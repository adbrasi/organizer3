"""
Auto-mosaic functionality using external ComfyUI workflow
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .utils import LoggerMixin, LogLevel, get_base_dir
from .metadata import embed


class AutoMosaicProcessor(LoggerMixin):
    """
    Handles automatic mosaic processing using external ComfyUI workflow.
    This class manages the execution of the pixivMosaic2.py script and handles
    metadata preservation during the mosaic process.
    """
    
    def __init__(self, callbacks=None, timeout_seconds: int = 180):
        super().__init__(callbacks)
        self.timeout_seconds = timeout_seconds
        self._setup_paths()
    
    def _setup_paths(self):
        """Setup paths to external scripts and workflows"""
        base_dir = get_base_dir()
        self.external_dir = base_dir / "external"
        self.workflow_path = self.external_dir / "PixivMosaicWorkflowAPI.json"
        self.script_path = self.external_dir / "pixivMosaic2.py"
    
    def validate_setup(self) -> bool:
        """
        Validate that all required external files are available.
        
        Returns:
            True if setup is valid, False otherwise
        """
        if not self.external_dir.exists():
            self.log(f"Diretório external não encontrado: {self.external_dir}", LogLevel.ERROR)
            return False
            
        if not self.script_path.exists():
            self.log(f"Script pixivMosaic2.py não encontrado: {self.script_path}", LogLevel.ERROR)
            return False
            
        if not self.workflow_path.exists():
            self.log(f"Workflow JSON não encontrado: {self.workflow_path}", LogLevel.ERROR)
            return False
        
        # Validate workflow file is valid JSON
        try:
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            self.log(f"Workflow JSON inválido: {e}", LogLevel.ERROR)
            return False
        except Exception as e:
            self.log(f"Erro ao ler workflow: {e}", LogLevel.ERROR)
            return False
        
        self.log("Configuração do auto-mosaic validada com sucesso.", LogLevel.SUCCESS)
        return True
    
    def process_image(self, input_path: Path, output_path: Path, 
                     preserve_metadata: bool = True, 
                     metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Process a single image through the mosaic workflow.
        
        Args:
            input_path: Path to input image
            output_path: Path for output image
            preserve_metadata: Whether to preserve/embed metadata
            metadata: Optional metadata to embed (if None, will try to read from input)
            
        Returns:
            True if successful, False otherwise
        """
        if not input_path.exists():
            self.log(f"Arquivo de entrada não encontrado: {input_path}", LogLevel.ERROR)
            return False
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run the mosaic script
        cmd = [
            sys.executable,
            str(self.script_path),
            str(self.workflow_path),
            str(input_path),
            str(output_path)
        ]
        
        try:
            self.log(f"Processando {input_path.name} através do workflow de mosaico...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            
            if result.returncode != 0:
                self.log(f"❌ Falha ao processar {input_path.name}: {result.stderr}", LogLevel.ERROR)
                return False
            
            # Check if output was created
            if not output_path.exists():
                self.log(f"❌ Arquivo de saída não foi criado: {output_path}", LogLevel.ERROR)
                return False
            
            # Preserve metadata if requested
            if preserve_metadata and metadata:
                try:
                    embed(output_path, metadata)
                    self.log(f"Metadados preservados para {output_path.name}")
                except Exception as e:
                    self.log(f"⚠️ Falha ao preservar metadados para {output_path.name}: {e}", LogLevel.WARN)
            
            self.log(f"✅ Processado com sucesso: {input_path.name} -> {output_path.name}")
            return True
            
        except subprocess.TimeoutExpired:
            self.log(f"❌ Timeout ao processar {input_path.name} (>{self.timeout_seconds}s)", LogLevel.ERROR)
            return False
        except Exception as e:
            self.log(f"❌ Erro inesperado ao processar {input_path.name}: {e}", LogLevel.ERROR)
            return False

    def process_image_with_retry(self, input_path: Path, output_path: Path, 
                                preserve_metadata: bool = True, 
                                metadata: Optional[Dict[str, Any]] = None,
                                max_retries: int = 2) -> bool:
        """
        Process a single image through the mosaic workflow with retry logic.
        If processing fails after retries, falls back to copying the original image.
        
        Args:
            input_path: Path to input image
            output_path: Path for output image
            preserve_metadata: Whether to preserve/embed metadata
            metadata: Optional metadata to embed
            max_retries: Maximum number of retry attempts
            
        Returns:
            True if successful (either processed or copied), False only on complete failure
        """
        if not input_path.exists():
            self.log(f"Arquivo de entrada não encontrado: {input_path}", LogLevel.ERROR)
            return False
        
        # Try processing with retries
        for attempt in range(max_retries):
            attempt_num = attempt + 1
            
            if attempt > 0:
                self.log(f"Tentativa {attempt_num}/{max_retries} para {input_path.name}...", LogLevel.WARN)
            
            success = self.process_image(input_path, output_path, preserve_metadata, metadata)
            
            if success:
                if attempt > 0:
                    self.log(f"✅ Sucesso na tentativa {attempt_num} para {input_path.name}", LogLevel.SUCCESS)
                return True
            else:
                self.log(f"❌ Falha na tentativa {attempt_num} para {input_path.name}", LogLevel.WARN)
        
        # All attempts failed - fallback to copying original image
        self.log(f"⚠️ Todas as tentativas falharam para {input_path.name}. Copiando imagem original como fallback...", LogLevel.WARN)
        
        try:
            import shutil
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Copy the original image
            shutil.copy2(input_path, output_path)
            
            # Preserve metadata if requested
            if preserve_metadata and metadata:
                try:
                    embed(output_path, metadata)
                    self.log(f"Metadados preservados na cópia para {output_path.name}")
                except Exception as e:
                    self.log(f"⚠️ Falha ao preservar metadados na cópia para {output_path.name}: {e}", LogLevel.WARN)
            
            self.log(f"📄 Imagem original copiada como fallback: {input_path.name} -> {output_path.name}", LogLevel.SUCCESS)
            return True
            
        except Exception as e:
            self.log(f"❌ Falha crítica ao copiar {input_path.name}: {e}", LogLevel.ERROR)
            return False
    
    def process_pack(self, pack_path: Path) -> bool:
        """
        Process all images in a pack directory through the mosaic workflow.
        
        Args:
            pack_path: Path to pack directory
            
        Returns:
            True if processing completed (even with some failures), False if setup invalid
        """
        if not self.validate_setup():
            return False
        
        # Setup directories
        original_images_dir = pack_path / "original_images"
        pixiv_safe_dir = pack_path / "pixiv_safe"
        metadata_file = pack_path / "metadata.json"
        
        if not original_images_dir.exists():
            self.log(f"Diretório 'original_images' não encontrado em '{pack_path.name}'", LogLevel.ERROR)
            return False
        
        # Create output directory
        pixiv_safe_dir.mkdir(exist_ok=True)
        
        # Load metadata if available
        metadata_map = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_map = json.load(f)
                self.log(f"Carregados metadados para {len(metadata_map)} imagens.")
            except Exception as e:
                self.log(f"⚠️ Erro ao carregar metadados: {e}", LogLevel.WARN)
        
        # Find PNG files to process
        png_files = list(original_images_dir.glob("*.png"))
        if not png_files:
            self.log(f"Nenhuma imagem PNG encontrada em '{original_images_dir}'", LogLevel.WARN)
            return True  # Not an error, just nothing to do
        
        total_files = len(png_files)
        processed_count = 0
        failed_count = 0
        
        self.update_status(f"Processando {total_files} imagens do pack '{pack_path.name}'...")
        
        for i, src_path in enumerate(png_files, 1):
            dst_path = pixiv_safe_dir / src_path.name
            
            # Get metadata for this image
            image_metadata = metadata_map.get(src_path.name, {})
            
            # Process the image
            success = self.process_image(
                src_path, 
                dst_path,
                preserve_metadata=True,
                metadata=image_metadata if image_metadata else None
            )
            
            if success:
                processed_count += 1
            else:
                failed_count += 1
            
            # Update progress
            progress = int(i / total_files * 100)
            self.update_progress(progress)
            self.update_status(f"Processando {i}/{total_files} - {processed_count} sucessos, {failed_count} falhas")
        
        # Final status update
        self.update_progress(0)
        if failed_count == 0:
            self.update_status(f"✅ Processamento completo: {processed_count} imagens processadas com sucesso!")
            self.log(f"SUCESSO: Pack '{pack_path.name}' processado - {processed_count} imagens.", LogLevel.SUCCESS)
        else:
            self.update_status(f"⚠️ Processamento completo: {processed_count} sucessos, {failed_count} falhas")
            self.log(f"AVISO: Pack '{pack_path.name}' processado com algumas falhas - {processed_count} sucessos, {failed_count} falhas.", LogLevel.WARN)
        
        return True
    
    def get_workflow_info(self) -> Optional[Dict[str, Any]]:
        """
        Get information about the loaded workflow.
        
        Returns:
            Workflow information dictionary or None if workflow not available
        """
        if not self.workflow_path.exists():
            return None
            
        try:
            with open(self.workflow_path, 'r', encoding='utf-8') as f:
                workflow_data = json.load(f)
            
            # Extract useful information
            info = {
                "path": str(self.workflow_path),
                "node_count": len(workflow_data) if isinstance(workflow_data, dict) else 0,
                "size_kb": self.workflow_path.stat().st_size / 1024,
                "valid": True
            }
            
            return info
            
        except Exception as e:
            return {
                "path": str(self.workflow_path),
                "error": str(e),
                "valid": False
            }
    
    def test_workflow(self, test_image_path: Optional[Path] = None) -> bool:
        """
        Test the mosaic workflow with a sample image.
        
        Args:
            test_image_path: Optional path to test image (if None, will look for any PNG)
            
        Returns:
            True if test successful, False otherwise
        """
        if not self.validate_setup():
            return False
        
        # Find a test image if not provided
        if test_image_path is None or not test_image_path.exists():
            # Look for any PNG in the project
            for possible_path in [
                get_base_dir() / "test_image.png",
                Path.cwd() / "test_image.png"
            ]:
                if possible_path.exists():
                    test_image_path = possible_path
                    break
            
            if test_image_path is None or not test_image_path.exists():
                self.log("Nenhuma imagem de teste disponível para testar o workflow.", LogLevel.WARN)
                return False
        
        # Create temporary output path
        temp_output = test_image_path.parent / f"test_mosaic_{test_image_path.stem}.png"
        
        try:
            self.log(f"Testando workflow com {test_image_path.name}...")
            result = self.process_image(test_image_path, temp_output, preserve_metadata=False)
            
            # Clean up test output
            if temp_output.exists():
                temp_output.unlink()
            
            if result:
                self.log("✅ Teste de workflow concluído com sucesso!", LogLevel.SUCCESS)
            else:
                self.log("❌ Teste de workflow falhou.", LogLevel.ERROR)
            
            return result
            
        except Exception as e:
            self.log(f"❌ Erro durante teste de workflow: {e}", LogLevel.ERROR)
            return False