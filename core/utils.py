"""
Core utilities and configuration classes
"""
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, NamedTuple, Optional
from enum import Enum


class LogLevel(Enum):
    """Log levels for consistent logging"""
    INFO = "INFO"
    SUCCESS = "SUCCESS"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


class CoreCallbacks(NamedTuple):
    """Callback functions for core operations to communicate with GUI"""
    progress: Callable[[int], None]  # 0-100 progress percentage
    log: Callable[[str, str], None]  # message, level
    status: Callable[[str], None]    # status message


@dataclass
class WatermarkConfig:
    """Watermark application settings"""
    name: str
    path: str
    position: str = "top_right"
    opacity: float = 0.95
    scale: float = 0.35
    margin_x: int = 20
    margin_y: int = 20


@dataclass
class CoreConfig:
    """Core processor configuration"""
    input_folder: Path
    watermark: WatermarkConfig
    max_workers: int = 8
    timeout_seconds: int = 180
    

def get_base_dir() -> Path:
    """Get base directory, handling PyInstaller frozen executable"""
    if getattr(sys, 'frozen', False):
        # PyInstaller frozen executable
        return Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    else:
        # Normal Python execution
        return Path(__file__).parent.parent


def setup_logging():
    """Setup consistent logging configuration"""
    import logging
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)


class LoggerMixin:
    """Mixin class to provide logging capabilities to core classes"""
    
    def __init__(self, callbacks: Optional[CoreCallbacks] = None):
        self.callbacks = callbacks or CoreCallbacks(
            progress=lambda x: None,
            log=lambda msg, level: print(f"[{level}] {msg}"),
            status=lambda msg: print(f"Status: {msg}")
        )
    
    def log(self, message: str, level: LogLevel = LogLevel.INFO):
        """Log a message using callbacks"""
        self.callbacks.log(message, level.value)
    
    def update_progress(self, value: int):
        """Update progress using callbacks"""
        self.callbacks.progress(max(0, min(100, value)))
    
    def update_status(self, message: str):
        """Update status using callbacks"""
        self.callbacks.status(message)