"""
Watermark application utilities
"""
import os
from pathlib import Path
from typing import Tuple

try:
    from PIL import Image
except ImportError:
    raise ImportError("PIL (Pillow) is required for watermark operations")

from .utils import WatermarkConfig


class WatermarkError(Exception):
    """Custom exception for watermark operations"""
    pass


def apply_watermark(base_image: Image.Image, config: WatermarkConfig) -> Image.Image:
    """
    Apply watermark to base image according to configuration
    
    Args:
        base_image: PIL Image to apply watermark to
        config: WatermarkConfig with application settings
        
    Returns:
        New PIL Image with watermark applied
    """
    if not os.path.exists(config.path):
        raise WatermarkError(f"Watermark file not found: {config.path}")
    
    try:
        # Ensure base image is in RGBA mode for compositing
        base_image = base_image.convert('RGBA')
        
        # Load and prepare watermark
        with Image.open(config.path) as wm:
            watermark = wm.convert("RGBA")
        
        # Calculate watermark size based on base image
        base_width, base_height = base_image.size
        min_dimension = min(base_width, base_height)
        watermark_size = int(min_dimension * config.scale)
        
        # Maintain aspect ratio while resizing
        watermark_ratio = watermark.width / watermark.height
        if watermark_ratio >= 1:
            new_width = watermark_size
            new_height = int(watermark_size / watermark_ratio)
        else:
            new_width = int(watermark_size * watermark_ratio)
            new_height = watermark_size
        
        watermark = watermark.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Apply opacity if less than full
        if config.opacity < 1.0:
            alpha = watermark.split()[-1]  # Get alpha channel
            alpha = alpha.point(lambda p: int(p * config.opacity))
            watermark.putalpha(alpha)
        
        # Calculate position
        pos_x, pos_y = _calculate_position(
            base_width, base_height,
            watermark.width, watermark.height,
            config.position, config.margin_x, config.margin_y
        )
        
        # Create temporary image for compositing
        temp_img = Image.new('RGBA', base_image.size, (0, 0, 0, 0))
        temp_img.paste(watermark, (pos_x, pos_y), watermark)
        
        # Composite watermark onto base image
        result = Image.alpha_composite(base_image, temp_img)
        
        # Convert back to RGB for final output
        return result.convert('RGB')
        
    except Exception as e:
        raise WatermarkError(f"Failed to apply watermark: {e}")


def _calculate_position(base_width: int, base_height: int, 
                      wm_width: int, wm_height: int,
                      position: str, margin_x: int, margin_y: int) -> Tuple[int, int]:
    """
    Calculate watermark position based on configuration
    
    Args:
        base_width, base_height: Base image dimensions
        wm_width, wm_height: Watermark dimensions
        position: Position string (e.g., "top_right", "center", etc.)
        margin_x, margin_y: Margin distances from edges
        
    Returns:
        Tuple of (x, y) coordinates for watermark placement
    """
    positions = {
        "top_left": (margin_x, margin_y),
        "top_center": ((base_width - wm_width) // 2, margin_y),
        "top_right": (base_width - wm_width - margin_x, margin_y),
        "center_left": (margin_x, (base_height - wm_height) // 2),
        "center": ((base_width - wm_width) // 2, (base_height - wm_height) // 2),
        "center_right": (base_width - wm_width - margin_x, (base_height - wm_height) // 2),
        "bottom_left": (margin_x, base_height - wm_height - margin_y),
        "bottom_center": ((base_width - wm_width) // 2, base_height - wm_height - margin_y),
        "bottom_right": (base_width - wm_width - margin_x, base_height - wm_height - margin_y)
    }
    
    return positions.get(position, positions["top_right"])


def validate_watermark_file(path: str) -> bool:
    """
    Validate that watermark file exists and is readable
    
    Args:
        path: Path to watermark file
        
    Returns:
        True if file is valid, False otherwise
    """
    if not os.path.exists(path):
        return False
    
    try:
        with Image.open(path) as img:
            # Try to load the image to verify it's readable
            img.verify()
        return True
    except Exception:
        return False


def get_default_watermarks() -> dict:
    """
    Get default watermark configurations
    
    Returns:
        Dictionary mapping watermark names to file paths
    """
    return {
        "LoveHent": r"D:\adolfocesar\content\marcadaguas\lovehent_watermark.png",
        "VioletJoi": r"D:\adolfocesar\content\marcadaguas\violetjoi_watermark.png",
        "VixMavis": r"D:\adolfocesar\content\marcadaguas\vixmavis_watermark.png"
    }