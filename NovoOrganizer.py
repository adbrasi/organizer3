import os
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, PngImagePlugin
import piexif

# --- Classe para criar Tooltips (Dicas de Ferramenta) ---
class ToolTip:
    """Cria uma tooltip para um widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)

    def enter(self, event=None):
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 1
        
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.wm_geometry(f"+{x}+{y}")
        
        label = tk.Label(self.tooltip, text=self.text, justify='left',
                         background="#ffffe0", relief='solid', borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack(ipadx=1)

    def leave(self, event=None):
        if self.tooltip:
            self.tooltip.destroy()
            self.tooltip = None

# --- Classe Principal do Processador ---
class ImageProcessorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Super Processador de Imagens v3.1") # Versão atualizada
        self.root.geometry("900x750")
        self.root.minsize(800, 700)
        
        style = ttk.Style(self.root)
        style.theme_use('clam')

        self.WATERMARKS = {
            "LoveHent": r"D:\adolfocesar\content\marcadaguas\lovehent_watermark.png",
            "VioletJoi": r"D:\adolfocesar\content\marcadaguas\violetjoi_watermark.png",
            "VixMavis": r"D:\adolfocesar\content\marcadaguas\vixmavis_watermark.png"
        }

        self.input_folder = tk.StringVar()
        self.selected_watermark = tk.StringVar(value=list(self.WATERMARKS.keys())[0])
        
        self.wm_position = tk.StringVar(value="top_right")
        self.wm_opacity = tk.DoubleVar(value=0.95)
        self.wm_scale = tk.DoubleVar(value=0.35)
        self.wm_margin_x = tk.IntVar(value=20)
        self.wm_margin_y = tk.IntVar(value=20)

        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Pronto para iniciar.")
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1) # A linha do log deve expandir

        config_frame = ttk.LabelFrame(main_frame, text="1. Configurações Principais", padding="10")
        config_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Pasta de Entrada:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Entry(config_frame, textvariable=self.input_folder, width=60).grid(row=0, column=1, sticky="ew", pady=5, padx=5)
        ttk.Button(config_frame, text="Procurar...", command=self.select_input_folder).grid(row=0, column=2, pady=5)

        ttk.Label(config_frame, text="Marca d'água:").grid(row=1, column=0, sticky=tk.W, pady=5)
        wm_combo = ttk.Combobox(config_frame, textvariable=self.selected_watermark, values=list(self.WATERMARKS.keys()), state="readonly")
        wm_combo.grid(row=1, column=1, columnspan=2, sticky="ew", pady=5, padx=5)

        wm_params_frame = ttk.LabelFrame(main_frame, text="2. Ajustes da Marca d'água", padding="10")
        wm_params_frame.grid(row=1, column=0, sticky="ew", pady=10)
        wm_params_frame.columnconfigure(1, weight=1)
        wm_params_frame.columnconfigure(4, weight=1) # Ajuste de coluna

        # Coluna 1 de parâmetros
        ttk.Label(wm_params_frame, text="Posição:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        pos_combo = ttk.Combobox(wm_params_frame, textvariable=self.wm_position, state="readonly", values=["top_left", "top_center", "top_right", "center_left", "center", "center_right", "bottom_left", "bottom_center", "bottom_right"])
        pos_combo.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        
        ttk.Label(wm_params_frame, text="Escala:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        scale_frame = ttk.Frame(wm_params_frame)
        scale_frame.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        scale_slider = ttk.Scale(scale_frame, from_=0.01, to=1.0, variable=self.wm_scale, orient=tk.HORIZONTAL)
        scale_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        scale_label = ttk.Label(scale_frame, textvariable=self.wm_scale, width=5)
        scale_label.pack(side=tk.LEFT)
        scale_label.config(font=("Segoe UI", 8))

        # Coluna 2 de parâmetros
        ttk.Label(wm_params_frame, text="Opacidade:").grid(row=0, column=2, sticky=tk.W, padx=20, pady=2)
        opacity_frame = ttk.Frame(wm_params_frame)
        opacity_frame.grid(row=0, column=3, columnspan=2, sticky="ew", padx=5, pady=2)
        opacity_slider = ttk.Scale(opacity_frame, from_=0.0, to=1.0, variable=self.wm_opacity, orient=tk.HORIZONTAL)
        opacity_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        opacity_label = ttk.Label(opacity_frame, textvariable=self.wm_opacity, width=5)
        opacity_label.pack(side=tk.LEFT)
        opacity_label.config(font=("Segoe UI", 8))

        ttk.Label(wm_params_frame, text="Margem (X/Y):").grid(row=1, column=2, sticky=tk.W, padx=20, pady=2)
        margin_frame = ttk.Frame(wm_params_frame)
        margin_frame.grid(row=1, column=3, columnspan=2, sticky="ew", padx=(5,0))
        ttk.Spinbox(margin_frame, from_=0, to=500, textvariable=self.wm_margin_x, width=5).pack(side=tk.LEFT, padx=2)
        ttk.Spinbox(margin_frame, from_=0, to=500, textvariable=self.wm_margin_y, width=5).pack(side=tk.LEFT, padx=2)
        
        # --- ALTERAÇÃO 1: REMOÇÃO DO BOTÃO 'PROCESSO COMPLETO' E AJUSTE DO LAYOUT ---
        action_frame = ttk.LabelFrame(main_frame, text="3. Ações", padding="10")
        action_frame.grid(row=2, column=0, sticky="ew", pady=10)
        action_frame.columnconfigure((0, 1), weight=1) # Configura apenas 2 colunas para expandir

        btn1 = ttk.Button(action_frame, text="Apenas Extrair Metadados", command=lambda: self.start_task(self.run_metadata_extraction))
        btn1.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        ToolTip(btn1, "Lê todas as imagens PNG e salva os metadados em arquivos 'metadata.json'.")

        btn2 = ttk.Button(action_frame, text="Apenas Processar Imagens", command=lambda: self.start_task(self.run_image_processing))
        btn2.grid(row=0, column=1, sticky="ew", padx=5, pady=5)
        ToolTip(btn2, "Aplica marca d'água, recria metadados, gera previews, arquivo de personagens e pacotes .zip.\nRequer que os metadados já tenham sido extraídos.")
        
        # O botão 3 foi removido.

        log_frame = ttk.LabelFrame(main_frame, text="Progresso e Log de Atividades", padding="10")
        log_frame.grid(row=3, column=0, sticky="nsew", pady=(10, 0)) # Mudei para linha 3
        # O main_frame foi configurado para expandir a linha 4, que agora é a do log
        main_frame.rowconfigure(3, weight=1) 
        log_frame.rowconfigure(2, weight=1)
        log_frame.columnconfigure(0, weight=1)
        
        self.status_label = ttk.Label(log_frame, textvariable=self.status_var, font=("Segoe UI", 10, "italic"))
        self.status_label.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        self.progress_bar = ttk.Progressbar(log_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, width=100, state='disabled', font=("Consolas", 9), wrap=tk.WORD)
        self.log_text.grid(row=2, column=0, sticky="nsew", pady=(5,0))
    
    def log(self, message, level="INFO"):
        def _update_log():
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, f"[{timestamp}] [{level}] {message}\n")
            self.log_text.config(state='disabled')
            self.log_text.see(tk.END)
        self.root.after(0, _update_log)

    def update_status(self, message):
        self.root.after(0, self.status_var.set, message)
        self.log(message, "STATUS")

    def update_progress(self, value):
        self.root.after(0, self.progress_var.set, value)

    def select_input_folder(self):
        folder = filedialog.askdirectory(title="Selecione a pasta raiz ou uma pasta específica")
        if folder:
            self.input_folder.set(folder)
            self.log(f"Pasta de entrada selecionada: {folder}")

    def start_task(self, target_function):
        if not self.input_folder.get() or not os.path.isdir(self.input_folder.get()):
            messagebox.showerror("Erro de Configuração", "Por favor, selecione uma pasta de entrada válida.")
            return
        
        for child in self.root.winfo_children(): self.set_widget_state(child, 'disabled')
        threading.Thread(target=target_function, daemon=True).start()

    def task_finished(self):
        self.root.after(0, self._internal_task_finished)

    def _internal_task_finished(self):
        for child in self.root.winfo_children(): self.set_widget_state(child, 'normal')
        self.log_text.config(state='disabled')

    def set_widget_state(self, widget, state):
        try:
            if isinstance(widget, scrolledtext.ScrolledText): # Não desabilitar o log
                return
            widget.config(state=state)
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            self.set_widget_state(child, state)

    # --- LÓGICA DE PROCESSAMENTO (BACKEND) ---

    def _get_target_folders_to_process(self, input_dir):
        if any(input_dir.glob("*.png")):
            self.log("Modo de pasta única detectado. Processando a pasta de entrada diretamente.")
            return [input_dir]

        subfolders = [f for f in input_dir.iterdir() if f.is_dir() and not f.name.startswith(('.', 'original_images', 'free_post', 'preview_Images'))]
        if subfolders:
            self.log(f"Modo multi-pack detectado. Encontradas {len(subfolders)} subpastas para processar.")
            return subfolders
        
        return []

    def get_png_metadata(self, image_path):
        try:
            with Image.open(image_path) as img:
                metadata_text = dict(getattr(img, 'text', {}))
                
                # Prioriza ler o JSON completo do campo "Comment"
                comment_json = metadata_text.get("Comment")
                if comment_json:
                    try:
                        # Se encontrou o campo Comment, decodifica o JSON e o retorna
                        return json.loads(comment_json)
                    except json.JSONDecodeError:
                        self.log(f"Campo 'Comment' em {image_path.name} não é um JSON válido. Usando todos os campos.", "WARN")
                
                # Fallback: se não houver "Comment" ou falhar, retorna todos os campos de texto
                return metadata_text
        except Exception as e:
            self.log(f"Falha ao ler metadados de {image_path.name}: {e}", "ERROR")
            return None

    def run_metadata_extraction(self):
        self.update_status("Iniciando extração de metadados...")
        self.update_progress(0)
        
        try:
            input_dir = Path(self.input_folder.get())
            target_folders = self._get_target_folders_to_process(input_dir)
            if not target_folders:
                messagebox.showwarning("Aviso", "Nenhuma pasta com imagens .png foi encontrada para processar.")
                self.task_finished()
                return

            total_folders = len(target_folders)
            for i, folder in enumerate(target_folders):
                self.update_status(f"Extraindo de '{folder.name}'...")
                png_files = list(folder.glob("*.png"))
                if not png_files:
                    self.log(f"Nenhum .png encontrado em '{folder.name}'. Pulando.", "WARN")
                    continue

                pack_metadata = {}
                with ThreadPoolExecutor(max_workers=os.cpu_count() * 2) as executor:
                    future_to_file = {executor.submit(self.get_png_metadata, png): png for png in png_files}
                    for future in as_completed(future_to_file):
                        png_file = future_to_file[future]
                        try:
                            metadata = future.result()
                            if metadata is not None: pack_metadata[png_file.name] = metadata
                        except Exception as exc:
                            self.log(f"Erro ao processar metadados de {png_file.name}: {exc}", "ERROR")

                if pack_metadata:
                    metadata_file = folder / "metadata.json"
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(pack_metadata, f, indent=2, ensure_ascii=False)
                    self.log(f"SUCESSO: Metadados de {len(pack_metadata)} imagens salvos em '{folder.name}/metadata.json'.", "SUCCESS")
                
                self.update_progress((i + 1) / total_folders * 100)

            self.update_status("Extração de metadados concluída com sucesso!")
        except Exception as e:
            self.log(f"ERRO CRÍTICO na extração: {e}", "FATAL")
            messagebox.showerror("Erro Crítico", f"Ocorreu um erro inesperado: {e}")
        finally:
            self.update_progress(0)
            self.task_finished()

    def run_image_processing(self):
        self.update_status("Iniciando processamento de imagens...")
        self.update_progress(0)
        
        try:
            input_dir = Path(self.input_folder.get())
            watermark_key = self.selected_watermark.get()
            watermark_file = self.WATERMARKS.get(watermark_key)
            if not watermark_file or not os.path.exists(watermark_file):
                messagebox.showerror("Erro", f"Arquivo da marca d'água '{watermark_key}' não encontrado!")
                self.task_finished()
                return

            target_folders = self._get_target_folders_to_process(input_dir)
            if not target_folders:
                messagebox.showwarning("Aviso", "Nenhuma pasta com imagens .png foi encontrada para processar.")
                self.task_finished()
                return

            total_folders = len(target_folders)
            current_date = datetime.now().strftime("%d-%m-%Y")
            
            for i, folder in enumerate(target_folders):
                self.update_status(f"Processando pasta '{folder.name}'...")
                
                preview_folder = folder / "preview_Images"; free_post_folder = folder / "free_post"; temp_zip_folder = folder / "temp_for_zip"
                preview_folder.mkdir(exist_ok=True); free_post_folder.mkdir(exist_ok=True); temp_zip_folder.mkdir(exist_ok=True)

                metadata_file = folder / "metadata.json"
                if not metadata_file.exists():
                    self.log(f"Arquivo 'metadata.json' não encontrado para '{folder.name}'. Pulando.", "WARN")
                    continue
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    pack_metadata = json.load(f)

                # --- ALTERAÇÃO 2: GERAR ARQUIVO characters.txt ---
                character_list = []
                for image_meta in pack_metadata.values():
                    char_tag = image_meta.get("character")
                    if char_tag:
                        # Limpa a tag: substitui '_' por ' ' e remove espaços no início/fim
                        cleaned_char = char_tag.replace('_', ' ').strip()
                        if cleaned_char not in character_list: # Evita duplicatas
                             character_list.append(cleaned_char)
                
                if character_list:
                    characters_txt_path = folder / "characters.txt"
                    final_string = ", ".join(character_list)
                    with open(characters_txt_path, 'w', encoding='utf-8') as txt_file:
                        txt_file.write(final_string)
                    self.log(f"Arquivo 'characters.txt' criado em '{folder.name}'.")
                # --- FIM DA ALTERAÇÃO 2 ---

                png_files_to_process = sorted([p for p in folder.glob("*.png") if p.name in pack_metadata])
                if not png_files_to_process:
                    self.log(f"Nenhuma imagem correspondente aos metadados em '{folder.name}'.", "WARN")
                    shutil.rmtree(temp_zip_folder); continue

                with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
                    futures = [executor.submit(self._process_single_image, png, j, pack_metadata, watermark_file, preview_folder, free_post_folder, temp_zip_folder) for j, png in enumerate(png_files_to_process, 1)]
                    for future in as_completed(futures): future.result()

                zip_path = folder / f"{folder.name}-{current_date}.zip"
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                    for item in temp_zip_folder.iterdir(): zipf.write(item, item.name)
                
                shutil.rmtree(temp_zip_folder)
                self.log(f"SUCESSO: Pasta '{folder.name}' processada. ZIP criado.", "SUCCESS")

                self._move_original_images(folder)

                self.update_progress((i + 1) / total_folders * 100)

            self.update_status("Processamento de imagens concluído com sucesso!")
        except Exception as e:
            self.log(f"ERRO CRÍTICO no processamento: {e}", "FATAL")
            messagebox.showerror("Erro Crítico", f"Erro: {e}")
        finally:
            self.update_progress(0)
            self.task_finished()

    def _move_original_images(self, target_folder):
        self.log(f"Organizando arquivos originais de '{target_folder.name}'...")
        original_images_dir = target_folder / "original_images"
        original_images_dir.mkdir(exist_ok=True)
        
        original_pngs = [f for f in target_folder.glob("*.png") if f.is_file()]
        
        if not original_pngs:
            self.log("Nenhum arquivo .png original encontrado para mover.")
            return

        for png_file in original_pngs:
            try:
                destination = original_images_dir / png_file.name
                shutil.move(str(png_file), str(destination))
            except Exception as e:
                self.log(f"Falha ao mover {png_file.name}: {e}", "ERROR")
        
        self.log(f"Arquivos originais movidos para '{original_images_dir.name}'.")

    def _process_single_image(self, png_file, index, pack_metadata, watermark_file, preview_folder, free_post_folder, temp_zip_folder):
        try:
            image_name_base = f"image_{index}"
            with Image.open(png_file) as img:
                # --- Preparação dos Metadados EXIF ---
                metadata_dict = pack_metadata.get(png_file.name, {})
                exif_bytes = b''
                if metadata_dict:
                    try:
                        json_string = json.dumps(metadata_dict)
                        exif_dict = {"0th": {piexif.ImageIFD.ImageDescription: json_string.encode('utf-8')}}
                        exif_bytes = piexif.dump(exif_dict)
                    except Exception as e:
                        self.log(f"Falha ao criar EXIF para {png_file.name}: {e}", "WARN")

                # --- 1. Salvar Preview Image como WEBP ---
                img.convert("RGB").save(
                    preview_folder / f"{image_name_base}.webp",
                    "WEBP",
                    quality=85,
                    exif=exif_bytes
                )

                # --- 2. Salvar imagem original para o ZIP ---
                img.save(temp_zip_folder / f"{image_name_base}.png", "PNG")

                # --- 3. Aplicar marca d'água e salvar como JPEG para Free Post ---
                watermarked_img = self._apply_watermark(img.copy(), watermark_file)
                watermarked_img.save(
                    free_post_folder / f"{image_name_base}.jpeg",
                    "JPEG",
                    quality=90,
                    exif=exif_bytes
                )

            self.log(f"Processada: {png_file.name} -> {image_name_base}.*")
        except Exception as e:
            self.log(f"Erro ao processar {png_file.name}: {e}", "ERROR"); raise

    def _apply_watermark(self, base_image, watermark_path):
        base_image = base_image.convert('RGBA')
        watermark = Image.open(watermark_path).convert("RGBA")
        base_width, base_height = base_image.size
        min_dimension = min(base_width, base_height)
        watermark_size = int(min_dimension * self.wm_scale.get())
        watermark_ratio = watermark.width / watermark.height
        new_width = watermark_size if watermark_ratio >= 1 else int(watermark_size * watermark_ratio)
        new_height = int(watermark_size / watermark_ratio) if watermark_ratio >= 1 else watermark_size
        watermark = watermark.resize((new_width, new_height), Image.Resampling.LANCZOS)
        opacity = self.wm_opacity.get()
        if opacity < 1.0:
            alpha = watermark.split()[-1]
            alpha = alpha.point(lambda p: int(p * opacity))
            watermark.putalpha(alpha)
        pos_x, pos_y = self._calculate_position(base_width, base_height, watermark.width, watermark.height)
        temp_img = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
        temp_img.paste(watermark, (pos_x, pos_y), watermark)
        return Image.alpha_composite(base_image, temp_img).convert('RGB')

    def _calculate_position(self, base_width, base_height, wm_width, wm_height):
        margin_x, margin_y, position = self.wm_margin_x.get(), self.wm_margin_y.get(), self.wm_position.get()
        positions = {"top_left": (margin_x, margin_y), "top_center": ((base_width - wm_width) // 2, margin_y), "top_right": (base_width - wm_width - margin_x, margin_y), "center_left": (margin_x, (base_height - wm_height) // 2), "center": ((base_width - wm_width) // 2, (base_height - wm_height) // 2), "center_right": (base_width - wm_width - margin_x, (base_height - wm_height) // 2), "bottom_left": (margin_x, base_height - wm_height - margin_y), "bottom_center": ((base_width - wm_width) // 2, base_height - wm_height - margin_y), "bottom_right": (base_width - wm_width - margin_x, base_height - wm_height - margin_y)}
        return positions.get(position, positions["top_right"])
    
    # A função run_full_process foi removida.

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessorApp(root)
    root.mainloop()
