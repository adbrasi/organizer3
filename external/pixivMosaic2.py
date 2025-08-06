import websocket
import uuid
import json
import sys
import os
import requests
import time
import logging
import argparse

# 1. SETUP DE LOGGING
# Configura um logger para fornecer feedback claro e padronizado.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 2. FUNÇÕES DE REDE ROBUSTAS

def make_request_with_retry(method, url, **kwargs):
    """
    Função genérica para fazer requisições HTTP com timeouts e retentativas.
    """
    # Adiciona um timeout padrão se não for fornecido
    kwargs.setdefault('timeout', 30)
    
    for attempt in range(3): # Tenta até 3 vezes
        try:
            response = requests.request(method, url, **kwargs)
            response.raise_for_status() # Lança exceção para status 4xx/5xx
            return response
        except requests.exceptions.ConnectionError as e:
            logging.error(f"Erro de conexão ao tentar acessar {url}. Verifique se o ComfyUI está online. Tentativa {attempt + 1}/3.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de rede na tentativa {attempt + 1}/3: {e}")
        
        if attempt < 2:
            time.sleep(5) # Espera 5 segundos antes de tentar novamente
            
    logging.critical("Não foi possível conectar ao servidor ComfyUI após várias tentativas.")
    return None

def upload_image(server_address, image_path):
    """Faz o upload de uma imagem para o servidor ComfyUI de forma robusta."""
    url = f"http://{server_address}/upload/image"
    logging.info(f"Fazendo upload da imagem '{image_path}'...")
    try:
        with open(image_path, 'rb') as f:
            files = {'image': (os.path.basename(image_path), f)}
            data = {'overwrite': 'true', 'type': 'input'}
            response = make_request_with_retry('post', url, files=files, data=data)
            if response:
                logging.info("Upload da imagem bem-sucedido.")
                return response.json()
    except FileNotFoundError:
        logging.critical(f"Arquivo de imagem de entrada não encontrado em '{image_path}'.")
    except Exception as e:
        logging.critical(f"Erro inesperado durante o upload da imagem: {e}")
    return None

def queue_prompt(server_address, client_id, prompt):
    """Envia o workflow para a API do ComfyUI de forma robusta."""
    url = f"http://{server_address}/prompt"
    logging.info("Enviando workflow para a fila de execução...")
    
    payload = {"prompt": prompt, "client_id": client_id}
    response = make_request_with_retry('post', url, json=payload)
    
    if response:
        response_json = response.json()
        if 'error' in response_json:
            logging.error(f"Erro na validação do prompt pelo ComfyUI: {response_json['error']}")
            logging.error(f"Detalhes do nó: {response_json.get('node_errors')}")
            return None
        prompt_id = response_json.get('prompt_id')
        logging.info(f"Workflow enviado com sucesso! ID do Prompt: {prompt_id}")
        return prompt_id
    return None

def wait_for_prompt_execution(server_address, client_id, prompt_id):
    """Usa o WebSocket para saber QUANDO o prompt terminou de executar."""
    ws_url = f"ws://{server_address}/ws?clientId={client_id}"
    ws = websocket.WebSocket()
    try:
        ws.connect(ws_url, timeout=10)
        logging.info("Conectado ao WebSocket. Aguardando a execução do workflow...")
        while True:
            # Define um timeout para o recebimento de mensagens para não ficar preso para sempre
            out = ws.recv() 
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'progress':
                    value = message['data']['value']
                    max_val = message['data']['max']
                    logging.info(f"Progresso: {value}/{max_val}")
                elif message['type'] == 'executed' and message['data'].get('prompt_id') == prompt_id:
                    logging.info("Execução do prompt concluída no servidor.")
                    return True
    except websocket.WebSocketTimeoutException:
        logging.error("Timeout do WebSocket. Nenhuma mensagem recebida do servidor por um longo período.")
    except Exception as e:
        logging.error(f"Erro durante a comunicação WebSocket: {e}")
    finally:
        if ws.connected:
            ws.close()
    return False

def get_history(server_address, prompt_id):
    """Obtém o histórico completo e confiável de um prompt que já foi executado."""
    logging.info(f"Obtendo histórico para o prompt ID: {prompt_id}")
    url = f"http://{server_address}/history/{prompt_id}"
    response = make_request_with_retry('get', url)
    if response:
        return response.json()
    return None

def download_and_save_image(server_address, image_data, output_path):
    """Faz o download da imagem final de forma robusta."""
    filename = image_data['filename']
    subfolder = image_data['subfolder']
    file_type = image_data['type']
    
    url = f"http://{server_address}/view?filename={filename}&subfolder={subfolder}&type={file_type}"
    logging.info(f"Baixando imagem resultante de: {url}")
    
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        response = make_request_with_retry('get', url, stream=True)
        if response:
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            logging.info(f"Imagem final salva com sucesso em: {output_path}")
            return True
    except Exception as e:
        logging.critical(f"Falha crítica ao salvar a imagem final em '{output_path}': {e}")
    return False

# 3. FUNÇÃO PRINCIPAL ORQUESTRADORA

def run_censor_workflow(args):
    """Orquestra todo o processo de censura da imagem com tratamento de erros."""
    client_id = str(uuid.uuid4())
    
    # Etapa 1: Upload
    upload_info = upload_image(args.server, args.input_path)
    if not upload_info:
        return 1 # Código de erro para falha no upload

    uploaded_filename = upload_info.get('name')

    # Etapa 2: Preparar Workflow
    try:
        with open(args.workflow_path, 'r', encoding='utf-8') as f:
            prompt = json.load(f)
    except FileNotFoundError:
        logging.critical(f"Arquivo de workflow não encontrado em '{args.workflow_path}'.")
        return 1
    except json.JSONDecodeError:
        logging.critical(f"O arquivo de workflow '{args.workflow_path}' não é um JSON válido.")
        return 1
    
    prompt[args.load_node_id]["inputs"]["image"] = uploaded_filename

    # Etapa 3: Enfileirar
    prompt_id = queue_prompt(args.server, client_id, prompt)
    if not prompt_id:
        return 1

    # Etapa 4: Aguardar Execução
    if not wait_for_prompt_execution(args.server, client_id, prompt_id):
        logging.error("A execução do workflow falhou ou o WebSocket foi interrompido.")
        return 1

    # Etapa 5: Obter e Validar Histórico
    history = get_history(args.server, prompt_id)
    if not history or prompt_id not in history:
        logging.error("Não foi possível obter o histórico para o prompt finalizado.")
        return 1

    history_data = history[prompt_id]
    outputs = history_data.get('outputs', {})
    
    # Verificação crucial de falhas na execução do prompt
    for node_id, node_output in outputs.items():
        if 'exception' in node_output:
            logging.error(f"O nó {node_id} encontrou uma exceção durante a execução:")
            logging.error(f"  Tipo: {node_output['exception'].get('type')}")
            logging.error(f"  Mensagem: {node_output['exception'].get('message')}")
            return 1 # Falha na execução de um nó

    # Etapa 6: Localizar e Baixar Imagem
    if args.save_node_id not in outputs or 'images' not in outputs[args.save_node_id]:
        logging.error(f"O nó de saída '{args.save_node_id}' não produziu uma imagem no histórico.")
        logging.error(f"Outputs disponíveis: {list(outputs.keys())}")
        return 1

    final_image_data = outputs[args.save_node_id]['images'][0]
    
    if download_and_save_image(args.server, final_image_data, args.output_path):
        logging.info("Processo concluído com sucesso!")
        return 0 # Sucesso
    else:
        logging.error("Falha ao baixar a imagem final.")
        return 1

# 4. INTERFACE DE LINHA DE COMANDO

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa um workflow do ComfyUI de forma robusta para censurar imagens.")
    
    parser.add_argument("workflow_path", help="Caminho para o arquivo .json do workflow.")
    parser.add_argument("input_path", help="Caminho para a imagem de entrada.")
    parser.add_argument("output_path", help="Caminho completo para salvar a imagem de saída.")
    
    parser.add_argument("--server", default="127.0.0.1:8188", help="Endereço do servidor ComfyUI (ex: 127.0.0.1:8188).")
    parser.add_argument("--load-node-id", default="5", help="ID do nó 'LoadImage' no workflow.")
    parser.add_argument("--save-node-id", default="20", help="ID do nó 'SaveImage' no workflow.")

    args = parser.parse_args()
    
    # Inicia o processo e encerra com o código de status apropriado
    exit_code = run_censor_workflow(args)
    sys.exit(exit_code)