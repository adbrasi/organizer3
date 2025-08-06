"""
Core image processing logic extracted from the original Tkinter application
All GUI dependencies removed - pure business logic with callbacks
"""
import os
import json
import shutil
import zipfile
import threading
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

try:
    from PIL import Image
    import piexif
except ImportError:
    raise ImportError("PIL (Pillow) and piexif are required")

from .utils import CoreConfig, LoggerMixin, LogLevel, get_base_dir
from .metadata import extract_png, embed, create_character_list, validate_metadata_size
from .watermark import apply_watermark


class ImageProcessorCore(LoggerMixin):
    """
    Core image processing functionality without GUI dependencies.
    Handles metadata extraction, image processing, and watermark application.
    """
    
    def __init__(self, config: CoreConfig, callbacks=None):
        super().__init__(callbacks)
        self.config = config
        
    def extract_metadata(self, root: Path) -> bool:
        """
        Extract metadata from PNG images in the specified root directory.
        
        Args:
            root: Root directory to process
            
        Returns:
            True if successful, False otherwise
        """
        self.update_status("Iniciando extração de metadados...")
        self.update_progress(0)
        
        try:
            target_folders = self._discover_packs(root)
            if not target_folders:
                self.log("Nenhuma pasta com imagens foi encontrada para processar.", LogLevel.WARN)
                return False

            total_folders = len(target_folders)
            for i, folder in enumerate(target_folders):
                self.update_status(f"Extraindo de '{folder.name}'...")
                
                # Find all image files
                image_files = []
                for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
                    image_files.extend(folder.glob(ext))
                
                if not image_files:
                    self.log(f"Nenhuma imagem encontrada em '{folder.name}'. Pulando.", LogLevel.WARN)
                    continue

                pack_metadata = {}
                with ThreadPoolExecutor(max_workers=min(self.config.max_workers, os.cpu_count() or 4)) as executor:
                    future_to_file = {executor.submit(extract_png, img_file): img_file for img_file in image_files}
                    for future in as_completed(future_to_file):
                        img_file = future_to_file[future]
                        try:
                            metadata = future.result()
                            if metadata is not None:
                                pack_metadata[img_file.name] = metadata
                        except Exception as exc:
                            self.log(f"Erro ao processar metadados de {img_file.name}: {exc}", LogLevel.ERROR)

                if pack_metadata:
                    metadata_file = folder / "metadata.json"
                    with open(metadata_file, 'w', encoding='utf-8') as f:
                        json.dump(pack_metadata, f, indent=2, ensure_ascii=False)
                    self.log(f"SUCESSO: Metadados de {len(pack_metadata)} imagens salvos em '{folder.name}/metadata.json'.", LogLevel.SUCCESS)
                
                self.update_progress((i + 1) / total_folders * 100)

            self.update_status("Extração de metadados concluída com sucesso!")
            return True
            
        except Exception as e:
            self.log(f"ERRO CRÍTICO na extração: {e}", LogLevel.FATAL)
            return False
        finally:
            self.update_progress(0)

    def process_images(self, root: Path) -> bool:
        """
        Process images with watermarks, create previews, and generate ZIP packages.
        
        Args:
            root: Root directory to process
            
        Returns:
            True if successful, False otherwise
        """
        self.update_status("Iniciando processamento de imagens...")
        self.update_progress(0)
        
        try:
            target_folders = self._discover_packs(root)
            if not target_folders:
                self.log("Nenhuma pasta com imagens foi encontrada para processar.", LogLevel.WARN)
                return False

            total_folders = len(target_folders)
            current_date = datetime.now().strftime("%d-%m-%Y")
            
            for i, folder in enumerate(target_folders):
                self.update_status(f"Processando pasta '{folder.name}'...")
                
                # Create output directories
                preview_folder = folder / "preview_Images"
                free_post_folder = folder / "free_post"
                temp_zip_folder = folder / "temp_for_zip"
                
                for output_dir in [preview_folder, free_post_folder, temp_zip_folder]:
                    output_dir.mkdir(exist_ok=True)

                # Load metadata
                metadata_file = folder / "metadata.json"
                if not metadata_file.exists():
                    self.log(f"Arquivo 'metadata.json' não encontrado para '{folder.name}'. Pulando.", LogLevel.WARN)
                    continue
                    
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    pack_metadata = json.load(f)

                # Generate characters.txt file
                character_list = create_character_list(pack_metadata)
                if character_list:
                    characters_txt_path = folder / "characters.txt"
                    with open(characters_txt_path, 'w', encoding='utf-8') as txt_file:
                        txt_file.write(character_list)
                    self.log(f"Arquivo 'characters.txt' criado em '{folder.name}'.")

                # Process images - find all image files that have metadata
                image_files_to_process = []
                for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
                    image_files_to_process.extend([p for p in folder.glob(ext) if p.name in pack_metadata])
                image_files_to_process = sorted(image_files_to_process)
                
                if not image_files_to_process:
                    self.log(f"Nenhuma imagem correspondente aos metadados em '{folder.name}'.", LogLevel.WARN)
                    shutil.rmtree(temp_zip_folder, ignore_errors=True)
                    continue

                # Process images in parallel
                with ThreadPoolExecutor(max_workers=min(self.config.max_workers, os.cpu_count() or 4)) as executor:
                    futures = []
                    for j, img_file in enumerate(image_files_to_process, 1):
                        future = executor.submit(
                            self._process_single_image,
                            img_file, j, pack_metadata,
                            preview_folder, free_post_folder, temp_zip_folder
                        )
                        futures.append(future)
                    
                    # Wait for all futures to complete
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            self.log(f"Erro no processamento de imagem: {e}", LogLevel.ERROR)

                # Create ZIP package
                zip_path = folder / f"{folder.name}-{current_date}.zip"
                try:
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=1) as zipf:
                        for item in temp_zip_folder.iterdir():
                            if item.is_file():
                                zipf.write(item, item.name)
                    
                    self.log(f"SUCESSO: Pasta '{folder.name}' processada. ZIP criado.", LogLevel.SUCCESS)
                except Exception as e:
                    self.log(f"Erro ao criar ZIP para '{folder.name}': {e}", LogLevel.ERROR)
                
                # Clean up temporary directory
                shutil.rmtree(temp_zip_folder, ignore_errors=True)

                # Move original images
                self._move_original_images(folder)

                self.update_progress((i + 1) / total_folders * 100)

            self.update_status("Processamento de imagens concluído com sucesso!")
            return True
            
        except Exception as e:
            self.log(f"ERRO CRÍTICO no processamento: {e}", LogLevel.FATAL)
            return False
        finally:
            self.update_progress(0)

    def run_auto_mosaic(self, pack_path: Path) -> bool:
        """
        Run automatic mosaic processing on a pack directory using external script.
        
        Args:
            pack_path: Path to the pack directory containing original_images
            
        Returns:
            True if successful, False otherwise
        """
        self.update_status(f"Iniciando processamento automático de mosaico para '{pack_path.name}'...")
        
        try:
            # Setup directories
            safe_dir = pack_path / "pixiv_safe"
            safe_dir.mkdir(exist_ok=True)
            
            original_images_dir = pack_path / "original_images"
            if not original_images_dir.exists():
                self.log(f"Diretório 'original_images' não encontrado em '{pack_path.name}'", LogLevel.ERROR)
                return False
            
            # Load metadata
            metadata_file = pack_path / "metadata.json"
            if not metadata_file.exists():
                self.log(f"Arquivo 'metadata.json' não encontrado em '{pack_path.name}'", LogLevel.ERROR)
                return False
                
            with open(metadata_file, 'r', encoding='utf-8') as f:
                meta_map = json.load(f)
            
            # Get external script paths
            base_dir = get_base_dir()
            workflow_path = base_dir / "external" / "PixivMosaicWorkflowAPI.json"
            script_path = base_dir / "external" / "pixivMosaic2.py"
            
            if not script_path.exists():
                self.log(f"Script pixivMosaic2.py não encontrado em {script_path}", LogLevel.ERROR)
                return False
                
            if not workflow_path.exists():
                self.log(f"Workflow JSON não encontrado em {workflow_path}", LogLevel.ERROR)
                return False
            
            # Process images - find all image files
            image_files = []
            for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
                image_files.extend(original_images_dir.glob(ext))
            
            if not image_files:
                self.log(f"Nenhuma imagem encontrada em '{original_images_dir}'", LogLevel.WARN)
                return False
            
            total_files = len(image_files)
            for i, src in enumerate(image_files, 1):
                dst = safe_dir / src.name
                
                # Run external mosaic script
                cmd = [
                    sys.executable,
                    str(script_path),
                    str(workflow_path),
                    str(src),
                    str(dst)
                ]
                
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=self.config.timeout_seconds
                    )
                    
                    if result.returncode != 0:
                        self.log(f"❌ {src.name}: {result.stderr}", LogLevel.ERROR)
                        continue
                    
                    # Re-embed metadata
                    if src.name in meta_map:
                        try:
                            embed(dst, meta_map[src.name])
                        except Exception as e:
                            self.log(f"Erro ao incorporar metadados em {dst.name}: {e}", LogLevel.WARN)
                    
                    self.log(f"✅ Processado: {src.name}")
                    
                except subprocess.TimeoutExpired:
                    self.log(f"Timeout ao processar {src.name}", LogLevel.ERROR)
                    continue
                except Exception as e:
                    self.log(f"Erro ao processar {src.name}: {e}", LogLevel.ERROR)
                    continue
                
                self.update_progress(int(i / total_files * 100))
            
            self.update_status(f"Processamento automático de mosaico concluído para '{pack_path.name}'!")
            return True
            
        except Exception as e:
            self.log(f"ERRO CRÍTICO no processamento de mosaico: {e}", LogLevel.FATAL)
            return False
        finally:
            self.update_progress(0)

    def _discover_packs(self, input_dir: Path) -> List[Path]:
        """
        Discover pack directories to process.
        
        Args:
            input_dir: Input directory to scan
            
        Returns:
            List of paths to process
        """
        # Check if input directory has image files directly
        image_extensions = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
        has_images = any(input_dir.glob(ext) for ext in image_extensions)
        if has_images:
            self.log("Modo de pasta única detectado. Processando a pasta de entrada diretamente.")
            return [input_dir]

        # Look for subdirectories with PNG files
        subfolders = [
            f for f in input_dir.iterdir()
            if f.is_dir() and not f.name.startswith(('.', 'original_images', 'free_post', 'preview_Images', 'pixiv_safe'))
        ]
        
        if subfolders:
            self.log(f"Modo multi-pack detectado. Encontradas {len(subfolders)} subpastas para processar.")
            return subfolders
        
        return []

    def _process_single_image(self, image_file: Path, index: int, pack_metadata: Dict[str, Any],
                            preview_folder: Path, free_post_folder: Path, temp_zip_folder: Path):
        """
        Process a single image file with watermarks and format conversion.
        
        Args:
            image_file: Path to image file to process
            index: Index for naming output files
            pack_metadata: Metadata dictionary for the pack
            preview_folder: Directory for preview images
            free_post_folder: Directory for watermarked images
            temp_zip_folder: Temporary directory for ZIP contents
        """
        try:
            image_name_base = f"image_{index}"
            
            with Image.open(image_file) as img:
                # Convert to RGB if necessary (for JPEG compatibility)
                if img.mode in ('RGBA', 'P'):
                    # Convert RGBA/palette images to RGB for JPEG output
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    rgb_img.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                    img = rgb_img
                
                # Get metadata for this image
                metadata_dict = pack_metadata.get(image_file.name, {})
                
                # Prepare EXIF data
                exif_bytes = b''
                if metadata_dict and validate_metadata_size(metadata_dict):
                    try:
                        json_string = json.dumps(metadata_dict, ensure_ascii=False, separators=(',', ':'))
                        exif_dict = {"0th": {piexif.ImageIFD.ImageDescription: json_string.encode('utf-8')}}
                        exif_bytes = piexif.dump(exif_dict)
                    except Exception as e:
                        self.log(f"Falha ao criar EXIF para {image_file.name}: {e}", LogLevel.WARN)

                # 1. Save preview image as WEBP
                preview_path = preview_folder / f"{image_name_base}.webp"
                img.convert("RGB").save(preview_path, "WEBP", quality=85, exif=exif_bytes)

                # 2. Save original image for ZIP - preserve original format for ZIP
                original_ext = image_file.suffix.lower()
                if original_ext in ['.jpg', '.jpeg']:
                    zip_path = temp_zip_folder / f"{image_name_base}.jpeg"
                    img.save(zip_path, "JPEG", quality=95, exif=exif_bytes)
                elif original_ext == '.webp':
                    zip_path = temp_zip_folder / f"{image_name_base}.webp"
                    img.save(zip_path, "WEBP", quality=95, exif=exif_bytes)
                else:  # PNG and others
                    zip_path = temp_zip_folder / f"{image_name_base}.png"
                    # For PNG, we need to use the original image with alpha channel
                    with Image.open(image_file) as orig_img:
                        orig_img.save(zip_path, "PNG")

                # 3. Apply watermark and save as JPEG for free post
                watermarked_img = apply_watermark(img.copy(), self.config.watermark)
                free_post_path = free_post_folder / f"{image_name_base}.jpeg"
                watermarked_img.save(free_post_path, "JPEG", quality=90, exif=exif_bytes)

            self.log(f"Processada: {image_file.name} -> {image_name_base}.*")
            
        except Exception as e:
            self.log(f"Erro ao processar {image_file.name}: {e}", LogLevel.ERROR)
            raise

    def _move_original_images(self, target_folder: Path):
        """
        Move original PNG files to organized directory.
        
        Args:
            target_folder: Target folder containing PNG files to move
        """
        self.log(f"Organizando arquivos originais de '{target_folder.name}'...")
        
        original_images_dir = target_folder / "original_images"
        original_images_dir.mkdir(exist_ok=True)
        
        # Find all original image files
        original_images = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            original_images.extend([f for f in target_folder.glob(ext) if f.is_file()])
        
        if not original_images:
            self.log("Nenhum arquivo de imagem original encontrado para mover.")
            return

        for img_file in original_images:
            try:
                destination = original_images_dir / img_file.name
                shutil.move(str(img_file), str(destination))
            except Exception as e:
                self.log(f"Falha ao mover {img_file.name}: {e}", LogLevel.ERROR)
        
        self.log(f"Arquivos originais movidos para '{original_images_dir.name}'.")

    def get_pack_info(self, pack_path: Path) -> Dict[str, Any]:
        """
        Get information about a pack directory.
        
        Args:
            pack_path: Path to pack directory
            
        Returns:
            Dictionary with pack information
        """
        info = {
            "name": pack_path.name,
            "has_metadata": (pack_path / "metadata.json").exists(),
            "has_original_images": (pack_path / "original_images").exists(),
            "has_pixiv_safe": (pack_path / "pixiv_safe").exists(),
            "png_count": len(list(pack_path.glob("*.png"))),
            "preview_count": len(list((pack_path / "preview_Images").glob("*"))) if (pack_path / "preview_Images").exists() else 0,
            "free_post_count": len(list((pack_path / "free_post").glob("*"))) if (pack_path / "free_post").exists() else 0
        }
        
        # Count original images if directory exists
        if info["has_original_images"]:
            info["original_count"] = len(list((pack_path / "original_images").glob("*.png")))
        else:
            info["original_count"] = 0
            
        # Count pixiv safe images if directory exists
        if info["has_pixiv_safe"]:
            info["pixiv_safe_count"] = len(list((pack_path / "pixiv_safe").glob("*.png")))
        else:
            info["pixiv_safe_count"] = 0
        
        return info