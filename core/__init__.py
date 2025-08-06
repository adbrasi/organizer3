"""
Core package for Super Image Processor v4.0  
Contains all business logic without GUI dependencies
"""

from .processor import ImageProcessorCore
from .auto_mosaic import AutoMosaicProcessor
from .metadata import extract_png, embed, create_character_list, validate_metadata_size
from .watermark import apply_watermark, validate_watermark_file, get_default_watermarks
from .utils import CoreConfig, WatermarkConfig, CoreCallbacks, LogLevel, LoggerMixin

__all__ = [
    "ImageProcessorCore",
    "AutoMosaicProcessor", 
    "extract_png",
    "embed",
    "create_character_list",
    "validate_metadata_size",
    "apply_watermark",
    "validate_watermark_file", 
    "get_default_watermarks",
    "CoreConfig",
    "WatermarkConfig",
    "CoreCallbacks",
    "LogLevel",
    "LoggerMixin"
]