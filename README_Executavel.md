### 1. Localização do Arquivo
O executável está localizado em:
```
d:/adolfocesar/ProjetoARAKIS/codigos/oraganizer/dist/SuperProcessadorImagens.exe
```

## 🎯 Funcionalidades da Aplicação

### Interface Gráfica
A aplicação abre uma janela com interface amigável contendo:

1. **Configurações Principais**
   - Seleção da pasta de entrada
   - Escolha da marca d'água (LoveHent, VioletJoi, VixMavis)

2. **Ajustes da Marca d'água**
   - Posição (9 opções: cantos, centro, etc.)
   - Escala (0.01 a 1.0)
   - Opacidade (0.0 a 1.0)
   - Margens X e Y (0 a 500 pixels)

3. **Ações Disponíveis**
   - **Apenas Extrair Metadados**: Lê imagens PNG e salva metadados em `metadata.json`
   - **Apenas Processar Imagens**: Aplica marca d'água, cria previews, gera ZIPs

### Funcionalidades de Processamento
- ✅ Extração de metadados de imagens PNG
- ✅ Aplicação de marca d'água personalizada
- ✅ Geração de previews em WEBP
- ✅ Criação de imagens JPEG com marca d'água
- ✅ Geração automática de arquivo `characters.txt`
- ✅ Criação de pacotes ZIP organizados
- ✅ Organização automática de arquivos originais

## 📂 Estrutura de Arquivos Necessários

### Marcas d'água (Requisito)
O executável espera encontrar as marcas d'água nos seguintes caminhos:
```
D:\adolfocesar\content\marcadaguas\lovehent_watermark.png
D:\adolfocesar\content\marcadaguas\violetjoi_watermark.png
D:\adolfocesar\content\marcadaguas\vixmavis_watermark.png
```

⚠️ **IMPORTANTE**: Certifique-se de que essas marcas d'água existam nos caminhos especificados, ou a aplicação retornará erro.

### Pasta de Entrada
- Pode ser uma pasta com imagens PNG diretamente
- Ou uma pasta contendo subpastas (modo multi-pack)
- Cada subpasta deve conter imagens PNG para processamento



Utiliza múltiplos threads para processamento eficiente



- Inclui automaticamente todas as dependências necessárias:
  - PIL (Pillow) para processamento de imagens
  - tkinter para interface gráfica
  - piexif para metadados EXIF
  - threading para processamento paralelo