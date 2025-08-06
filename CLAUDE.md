# Claude Code MCP Usage Instructions

This guide instructs Claude Code on how and when to use each installed MCP server. These tools significantly expand your capabilities and should be used whenever possible to provide the best assistance.

## 🚀 Project Setup - Serena (GLOBAL INSTALLATION)

**⚠️ CRITICAL: First Action for Every New Coding Session**

Since Serena was installed globally, you must activate the project before using Serena's tools:

### Initial Project Activation
```
Activate the project /mnt/d/adolfocesar/ProjetoARAKIS/codigos/Organizer3
```

### Subsequent Project Activations (after first time)
```
Activate the project Organizer3
```

**Remember**: Always perform this activation at the start of every new project involving code work!

## 📁 Project Overview - Image Processing Suite

This is a Python-based image processing application with two main components:
- **NovoOrganizer.py**: GUI application for batch processing images with watermarks
- **pixivMosaic2.py**: CLI tool for ComfyUI image processing workflows

## 🛠️ Commands

### Running the Applications
```bash
# GUI Image Processor
python NovoOrganizer.py

# CLI ComfyUI Tool  
python pixivMosaic2.py <arguments>
```

### Building Executable (PyInstaller)
```bash
# Create standalone executable
pyinstaller --onefile --windowed NovoOrganizer.py
```

### Testing
```bash
# Run individual test (no formal test framework detected)
python NovoOrganizer.py  # Manual GUI testing
python pixivMosaic2.py --help  # CLI argument validation
```

## 📋 Code Style Guidelines

### Imports
- Standard library imports first (os, json, shutil, etc.)
- Third-party imports second (PIL, tkinter, requests, etc.) 
- Local imports last (if any)
- Use absolute imports, avoid wildcards

### Formatting
- 4-space indentation
- Line length: ~120 characters (flexible for GUI code)
- String quotes: Use double quotes for user-facing strings, single for internal
- Portuguese comments and strings for user interface

### Types
- No explicit type hints currently used
- Duck typing with exception handling
- Validate inputs before processing

### Naming Conventions
- Classes: PascalCase (ImageProcessorApp, ToolTip)
- Methods/Functions: snake_case (_process_single_image, get_png_metadata)
- Constants: UPPER_SNAKE_CASE (WATERMARKS)
- Variables: snake_case with descriptive names

### Error Handling
- Use try/except blocks for file operations and image processing
- Log errors with severity levels ("ERROR", "WARN", "FATAL")
- Show user-friendly error messages via messagebox
- Graceful degradation when possible

### Dependencies
- PIL (Pillow): Image processing and manipulation
- tkinter: GUI framework 
- piexif: EXIF metadata handling
- requests: HTTP requests (pixivMosaic2)
- websocket: WebSocket communication (pixivMosaic2)

### File Paths
- Use pathlib.Path for cross-platform compatibility
- Handle Windows-style absolute paths (D:\adolfocesar\...)
- Create directories with exist_ok=True