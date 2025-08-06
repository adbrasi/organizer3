"""
Metadata extraction and embedding utilities
Handles PNG Comment chunks and EXIF for JPEG/WEBP
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from PIL import Image, PngImagePlugin
    import piexif
except ImportError as e:
    raise ImportError(f"Required imaging libraries not found: {e}")


class MetadataError(Exception):
    """Custom exception for metadata operations"""
    pass


def extract_png(path: Path) -> Dict[str, Any]:
    """
    Extract metadata from image files (PNG, JPEG, WEBP)
    Checks PNG Comment chunks and EXIF ImageDescription field
    
    Args:
        path: Path to image file
        
    Returns:
        Dictionary containing metadata, or empty dict if none found
    """
    try:
        with Image.open(path) as img:
            file_format = img.format.upper()
            
            # Initialize variables
            png_comment = ""
            exif_description = ""
            
            # For PNG files: try to get Comment chunk
            if file_format == 'PNG':
                png_comment = img.text.get("Comment", "")
            
            # For all formats: try to extract EXIF ImageDescription
            # Method 1: Direct piexif approach (works best for JPEG/WEBP)
            try:
                if hasattr(img, 'info') and 'exif' in img.info:
                    exif_dict = piexif.load(img.info['exif'])
                    if '0th' in exif_dict and piexif.ImageIFD.ImageDescription in exif_dict['0th']:
                        raw_desc = exif_dict['0th'][piexif.ImageIFD.ImageDescription]
                        # Handle both bytes and string
                        if isinstance(raw_desc, bytes):
                            exif_description = raw_desc.decode('utf-8')
                        else:
                            exif_description = str(raw_desc)
            except Exception as e:
                # If piexif fails, try alternative method
                pass
            
            # Method 2: PIL's getexif() method (alternative for JPEG)
            if not exif_description and file_format in ['JPEG', 'JPG']:
                try:
                    exif_data = img.getexif()
                    if exif_data and 270 in exif_data:  # 270 is ImageDescription tag
                        exif_description = exif_data[270]
                except Exception:
                    pass
            
            # Method 3: PIL's _getexif() method (legacy fallback)
            if not exif_description and hasattr(img, '_getexif'):
                try:
                    exif = img._getexif()
                    if exif and 270 in exif:  # 270 is ImageDescription tag
                        exif_description = exif[270]
                except Exception:
                    pass
            
            # Prioritize EXIF ImageDescription (newer metadata location), then PNG comment
            metadata_source = exif_description or png_comment or "{}"
            
        try:
            # Try to parse as JSON
            parsed_metadata = json.loads(metadata_source)
            return parsed_metadata
        except (json.JSONDecodeError, ValueError) as e:
            # If JSON parsing fails, preserve the raw data
            return {
                "raw_comment": png_comment if png_comment else None,
                "raw_exif_description": exif_description if exif_description else None,
                "_parse_error": str(e),
                "_metadata_source": metadata_source if metadata_source != "{}" else None
            }
            
    except Exception as e:
        raise MetadataError(f"Failed to extract metadata from {path.name}: {e}")


def extract_all_png_metadata(path: Path) -> Dict[str, Any]:
    """
    Extract all available text metadata from PNG file
    
    Args:
        path: Path to PNG file
        
    Returns:
        Dictionary with all text chunks
    """
    try:
        with Image.open(path) as img:
            # Get all text metadata
            metadata = dict(getattr(img, 'text', {}))
            
            # Prioritize Comment field if it contains JSON
            comment_json = metadata.get("Comment")
            if comment_json:
                try:
                    return json.loads(comment_json)
                except json.JSONDecodeError:
                    # Keep all fields if Comment isn't valid JSON
                    pass
                    
            return metadata
            
    except Exception as e:
        raise MetadataError(f"Failed to extract all metadata from {path.name}: {e}")


def embed(path: Path, metadata: Dict[str, Any]) -> None:
    """
    Embed metadata into image file (PNG, JPEG, or WEBP)
    
    Args:
        path: Path to image file
        metadata: Dictionary containing metadata to embed
    """
    if not metadata:
        return
        
    # Convert metadata to JSON string
    json_str = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
    
    # Check size limits (PNG tEXt chunk limitation)
    if len(json_str.encode('utf-8')) > 60_000:  # 64KB limit with safety margin
        raise MetadataError(f"Metadata too large for {path.name} (>60KB)")
    
    try:
        suffix = path.suffix.lower()
        
        if suffix == '.png':
            _embed_png(path, json_str)
        elif suffix in ['.jpg', '.jpeg', '.webp']:
            _embed_exif(path, json_str)
        else:
            raise MetadataError(f"Unsupported file format: {suffix}")
            
    except Exception as e:
        raise MetadataError(f"Failed to embed metadata in {path.name}: {e}")


def _embed_png(path: Path, json_str: str) -> None:
    """Embed metadata in PNG Comment chunk"""
    with Image.open(path) as img:
        # Create PNG info with Comment chunk
        png_info = PngImagePlugin.PngInfo()
        png_info.add_text("Comment", json_str)
        
        # Save with metadata
        img.save(path, pnginfo=png_info)


def _embed_exif(path: Path, json_str: str) -> None:
    """Embed metadata in EXIF ImageDescription field"""
    with Image.open(path) as img:
        # Create EXIF data
        exif_dict = {
            "0th": {
                piexif.ImageIFD.ImageDescription: json_str.encode('utf-8')
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        
        # Save with EXIF data
        if path.suffix.lower() == '.webp':
            # WebP with EXIF support (requires Pillow >= 10.0)
            img.save(path, exif=exif_bytes)
        else:
            # JPEG
            img.save(path, exif=exif_bytes)


def validate_metadata_size(metadata: Dict[str, Any]) -> bool:
    """
    Check if metadata will fit within size constraints
    
    Args:
        metadata: Dictionary containing metadata
        
    Returns:
        True if metadata size is acceptable
    """
    if not metadata:
        return True
        
    json_str = json.dumps(metadata, ensure_ascii=False, separators=(',', ':'))
    return len(json_str.encode('utf-8')) <= 60_000


def create_character_list(pack_metadata: Dict[str, Dict[str, Any]]) -> str:
    """
    Extract unique character names from pack metadata
    
    Args:
        pack_metadata: Dictionary mapping filenames to metadata
        
    Returns:
        Comma-separated string of unique character names
    """
    characters = []
    
    for image_meta in pack_metadata.values():
        char_tag = image_meta.get("character", "")
        if char_tag:
            # Clean the tag: replace underscores with spaces and strip
            cleaned_char = char_tag.replace('_', ' ').strip()
            if cleaned_char and cleaned_char not in characters:
                characters.append(cleaned_char)
    
    return ", ".join(characters)