"""
Qt Worker thread implementation for background processing
Handles all long-running operations without blocking the GUI
"""
import json
from pathlib import Path
from typing import Optional

try:
    from PySide6.QtCore import QThread, Signal, QObject
except ImportError:
    raise ImportError("PySide6 is required. Install with: pip install PySide6")

from core.processor import ImageProcessorCore
from core.auto_mosaic import AutoMosaicProcessor
from core.utils import CoreConfig, CoreCallbacks


class WorkerSignals(QObject):
    """Signals for communicating with the main thread"""
    progress = Signal(int)  # Progress percentage (0-100)
    log = Signal(str, str)  # Message, level
    status = Signal(str)    # Status message
    finished = Signal()     # Task finished
    success = Signal()      # Task completed successfully
    error = Signal(str)     # Error occurred with error message


class WorkerThread(QThread):
    """
    Background worker thread for processing operations.
    Runs core processing logic without blocking the GUI.
    """
    
    # Signals for communication with main thread
    finished = Signal()
    success = Signal()
    error = Signal(str)
    
    def __init__(self, operation: str, config: CoreConfig, callbacks: CoreCallbacks):
        super().__init__()
        self.operation = operation
        self.config = config
        self.callbacks = callbacks
        
        # Connect callbacks to thread-safe signals
        self._setup_signals()
    
    def _setup_signals(self):
        """Setup thread-safe signal connections"""
        # Create worker signals
        self.signals = WorkerSignals()
        
        # Connect worker signals to main thread callbacks
        self.signals.progress.connect(self.callbacks.progress)
        self.signals.log.connect(self.callbacks.log)
        self.signals.status.connect(self.callbacks.status)
        
        # Create thread-safe callbacks that emit signals
        self.thread_safe_callbacks = CoreCallbacks(
            progress=self.signals.progress.emit,
            log=self.signals.log.emit,
            status=self.signals.status.emit
        )
    
    def run(self):
        """Main thread execution method"""
        try:
            if self.operation == "extract_metadata":
                self._extract_metadata()
            elif self.operation == "process_images":
                self._process_images()
            elif self.operation == "auto_mosaic":
                self._auto_mosaic()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
            
            self.success.emit()
            
        except Exception as e:
            error_message = f"Erro na operação '{self.operation}': {str(e)}"
            self.thread_safe_callbacks.log(error_message, "FATAL")
            self.error.emit(error_message)
            
        finally:
            self.finished.emit()
    
    def _extract_metadata(self):
        """Execute metadata extraction in background thread"""
        processor = ImageProcessorCore(self.config, self.thread_safe_callbacks)
        
        success = processor.extract_metadata(self.config.input_folder)
        if not success:
            raise RuntimeError("Falha na extração de metadados")
    
    def _process_images(self):
        """Execute image processing in background thread"""
        processor = ImageProcessorCore(self.config, self.thread_safe_callbacks)
        
        success = processor.process_images(self.config.input_folder)
        if not success:
            raise RuntimeError("Falha no processamento de imagens")
    
    def _auto_mosaic(self):
        """Execute auto-mosaic processing in background thread"""
        # Auto-mosaic should process the original_images folder directly
        original_images_dir = self.config.input_folder / "original_images"
        
        if not original_images_dir.exists():
            raise RuntimeError(f"Pasta 'original_images' não encontrada em: {self.config.input_folder}")
        
        # Find all image files in original_images
        image_files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            image_files.extend(original_images_dir.glob(ext))
        
        if not image_files:
            raise RuntimeError(f"Nenhuma imagem encontrada em: {original_images_dir}")
        
        # Initialize auto-mosaic processor
        mosaic_processor = AutoMosaicProcessor(
            self.thread_safe_callbacks, 
            self.config.timeout_seconds
        )
        
        if not mosaic_processor.validate_setup():
            raise RuntimeError("Configuração do auto-mosaico inválida")
        
        # Create pixiv_safe output directory
        pixiv_safe_dir = self.config.input_folder / "pixiv_safe" 
        pixiv_safe_dir.mkdir(exist_ok=True)
        
        # Load metadata if available
        metadata_file = self.config.input_folder / "metadata.json"
        metadata_map = {}
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_map = json.load(f)
                self.thread_safe_callbacks.log(f"Carregados metadados para {len(metadata_map)} imagens.", "INFO")
            except Exception as e:
                self.thread_safe_callbacks.log(f"Erro ao carregar metadados: {e}", "WARN")
        
        # Process each image file
        total_files = len(image_files)
        processed_count = 0
        failed_count = 0
        
        self.thread_safe_callbacks.status(f"Processando {total_files} imagens para auto-mosaico...")
        
        for i, src_path in enumerate(image_files, 1):
            dst_path = pixiv_safe_dir / src_path.name
            
            # Get metadata for this image
            image_metadata = metadata_map.get(src_path.name, {})
            
            # Process the image through mosaic workflow with retry and fallback
            success = mosaic_processor.process_image_with_retry(
                src_path,
                dst_path,
                preserve_metadata=True,
                metadata=image_metadata if image_metadata else None,
                max_retries=2
            )
            
            if success:
                processed_count += 1
            else:
                failed_count += 1
            
            # Update progress
            progress = int(i / total_files * 100)
            self.thread_safe_callbacks.progress(progress)
            self.thread_safe_callbacks.status(
                f"Processando {i}/{total_files} - {processed_count} sucessos, {failed_count} falhas"
            )
        
        # Final results
        if failed_count == 0:
            self.thread_safe_callbacks.status(f"Auto-mosaico completo: {processed_count} imagens processadas!")
            self.thread_safe_callbacks.log(f"SUCESSO: {processed_count} imagens processadas com sucesso.", "SUCCESS")
        else:
            self.thread_safe_callbacks.log(f"AVISO: {processed_count} sucessos, {failed_count} falhas.", "WARN")
        
        if processed_count == 0:
            raise RuntimeError("Nenhuma imagem foi processada com sucesso")


class ProgressWorkerThread(QThread):
    """
    Specialized worker thread for operations that need fine-grained progress reporting.
    Useful for operations with multiple steps or file processing.
    """
    
    progress = Signal(int, str)  # Progress percentage and current item
    finished = Signal()
    success = Signal()
    error = Signal(str)
    
    def __init__(self, operation_func, *args, **kwargs):
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        
    def run(self):
        """Execute the operation function with progress reporting"""
        try:
            # Create progress callback
            def progress_callback(percent, item=""):
                self.progress.emit(percent, item)
            
            # Add progress callback to kwargs
            self.kwargs['progress_callback'] = progress_callback
            
            # Execute operation
            result = self.operation_func(*self.args, **self.kwargs)
            
            if result:
                self.success.emit()
            else:
                self.error.emit("Operação falhou")
                
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class BatchWorkerThread(QThread):
    """
    Worker thread for batch operations on multiple items.
    Provides detailed progress tracking for each item in the batch.
    """
    
    item_started = Signal(str)      # Item name started
    item_finished = Signal(str, bool)  # Item name, success
    progress = Signal(int)          # Overall progress
    finished = Signal()
    success = Signal(int, int)      # Success count, total count
    error = Signal(str)
    
    def __init__(self, items, operation_func):
        super().__init__()
        self.items = items
        self.operation_func = operation_func
        
    def run(self):
        """Process items in batch with progress reporting"""
        try:
            total_items = len(self.items)
            success_count = 0
            
            for i, item in enumerate(self.items):
                if self.isInterruptionRequested():
                    break
                
                self.item_started.emit(str(item))
                
                try:
                    success = self.operation_func(item)
                    if success:
                        success_count += 1
                    self.item_finished.emit(str(item), success)
                except Exception as e:
                    self.item_finished.emit(str(item), False)
                    self.error.emit(f"Erro em {item}: {str(e)}")
                
                # Update progress
                progress = int((i + 1) / total_items * 100)
                self.progress.emit(progress)
            
            self.success.emit(success_count, total_items)
            
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


class ValidationWorkerThread(QThread):
    """
    Worker thread for validation operations.
    Checks file integrity, metadata validity, etc.
    """
    
    validation_result = Signal(dict)  # Validation results
    finished = Signal()
    error = Signal(str)
    
    def __init__(self, validation_func, target_path: Path):
        super().__init__()
        self.validation_func = validation_func
        self.target_path = target_path
        
    def run(self):
        """Run validation checks"""
        try:
            results = self.validation_func(self.target_path)
            self.validation_result.emit(results)
        except Exception as e:
            self.error.emit(str(e))
        finally:
            self.finished.emit()


def create_worker_thread(operation: str, config: CoreConfig, callbacks: CoreCallbacks) -> WorkerThread:
    """
    Factory function to create appropriate worker thread for operation.
    
    Args:
        operation: Operation name
        config: Core configuration
        callbacks: Callback functions
        
    Returns:
        Configured WorkerThread instance
    """
    return WorkerThread(operation, config, callbacks)