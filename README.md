# Super Image Processor v4.0 - Enhanced Edition

A complete rewrite of the original Tkinter-based image processing application, now featuring a modern PySide6 interface with improved architecture and enhanced functionality.

## 🌟 Features

### Core Functionality
- **📊 Metadata Extraction**: Extract and preserve PNG metadata with JSON export
- **🎨 Batch Image Processing**: Apply watermarks with customizable settings
- **🔒 Auto-Mosaic Generation**: ComfyUI integration for automated censoring
- **✏️ Manual Mosaic Editor**: Interactive brush-based editing tools
- **📦 Package Creation**: Automated ZIP generation with organized outputs
- **🚀 Multi-threaded Processing**: Responsive UI with background operations

### Technical Improvements
- **Clean Architecture**: Separated business logic from GUI
- **Modern Qt Interface**: Professional PySide6-based UI
- **Thread Safety**: Background processing with progress tracking
- **Error Handling**: Comprehensive error reporting and recovery
- **Extensible Design**: Plugin-ready architecture for future enhancements

## 🛠️ Installation

### Prerequisites
- Python 3.9+ (recommended: Python 3.11)
- Windows 10/11 (Linux/macOS support coming soon)

### Dependencies
Install all required packages:
```bash
pip install -r requirements.txt
```

### Manual Installation
```bash
pip install PySide6>=6.5.0
pip install Pillow>=10.0.0
pip install opencv-python>=4.9.0
pip install piexif>=1.1.0
pip install numpy>=1.24.0
```

## 🚀 Quick Start

### Run the Application
```bash
python run.py
```

### Command Line Options
```bash
python run.py --help     # Show help
python run.py --version  # Show version info
python run.py --gui      # Start GUI mode (default)
python run.py --cli      # CLI mode (future feature)
```

### Test Installation
```bash
python test_app.py
```

## 📁 Project Structure

```
Organizer3/
├── core/                    # Business logic (GUI-independent)
│   ├── processor.py         # Main image processing
│   ├── metadata.py          # Metadata handling
│   ├── watermark.py         # Watermark application
│   ├── auto_mosaic.py       # ComfyUI integration
│   └── utils.py            # Common utilities
│
├── gui/                     # PySide6 interface
│   ├── main_window.py       # Main application window
│   ├── worker_thread.py     # Background processing
│   └── manual_editor.py     # Interactive editor
│
├── external/                # External scripts
│   ├── pixivMosaic2.py      # ComfyUI interface script
│   └── PixivMosaicWorkflowAPI.json  # ComfyUI workflow
│
├── assets/                  # Application assets
│   └── watermarks/          # Watermark files
│
├── run.py                   # Main application entry
├── requirements.txt         # Python dependencies
├── build.py                # Build script for executable
└── test_app.py             # Test suite
```

## 🎯 Usage Guide

### 1. Basic Workflow
1. **Select Input Folder**: Choose directory containing PNG images
2. **Configure Watermark**: Select watermark and adjust settings
3. **Extract Metadata**: Read and save image metadata to JSON
4. **Process Images**: Apply watermarks and generate outputs
5. **Auto-Mosaic** (Optional): Generate censored versions using ComfyUI
6. **Manual Edit** (Optional): Fine-tune results with brush tools

### 2. Watermark Configuration
- **Position**: 9 placement options (corners, centers, etc.)
- **Scale**: 0.01 - 1.0 (relative to image size)
- **Opacity**: 0.0 - 1.0 (transparency level)
- **Margins**: X/Y pixel offsets from edges

### 3. Output Structure
```
input_folder/
├── original_images/         # Original PNG files (moved)
├── preview_Images/          # WEBP previews
├── free_post/              # Watermarked JPEG files
├── pixiv_safe/             # Auto-mosaic processed (optional)
├── metadata.json           # Extracted metadata
├── characters.txt          # Character list
└── [folder-name]-[date].zip # Packaged files
```

## 🔧 Advanced Configuration

### Watermark Files
Default watermark locations:
```
D:\adolfocesar\content\marcadaguas\
├── lovehent_watermark.png
├── violetjoi_watermark.png
└── vixmavis_watermark.png
```

### ComfyUI Integration
For auto-mosaic functionality:
1. Install ComfyUI
2. Place workflow file in `external/PixivMosaicWorkflowAPI.json`
3. Ensure `pixivMosaic2.py` script is configured

### Performance Tuning
- **Max Workers**: Adjust thread count in core settings
- **Timeout**: Configure external script timeouts
- **Memory**: Monitor usage with large batches

## 🏗️ Building Executable

Create standalone executable:
```bash
python build.py
```

This creates:
- `dist/SuperImageProcessor.exe` - Standalone executable
- `dist/README.txt` - Deployment instructions

## 🧪 Testing

Run the test suite:
```bash
python test_app.py
```

Test specific components:
```python
# Test core functionality only
from test_app import test_core_functionality
test_core_functionality()

# Test GUI imports
from test_app import test_gui_creation
test_gui_creation()
```

## 🔍 Troubleshooting

### Common Issues

**Import Errors**
```bash
# Check dependencies
python -c "import PySide6; print('PySide6:', PySide6.__version__)"
python -c "import PIL; print('Pillow:', PIL.__version__)"
```

**GUI Won't Start**
- Verify display environment (for WSL/remote systems)
- Check PySide6 installation
- Run with `python run.py --version` first

**Watermark Errors**
- Verify file paths in `core/watermark.py`
- Check file permissions
- Ensure PNG format with alpha channel

**ComfyUI Integration**
- Verify ComfyUI installation
- Check workflow JSON file validity
- Test external script independently

### Debug Mode
Run with detailed logging:
```bash
python run.py 2>&1 | tee debug.log
```

## 🚧 Future Enhancements

### Planned Features
- **CLI Mode**: Command-line batch processing
- **Plugin System**: Extensible filter and effect plugins
- **Cloud Integration**: Remote processing capabilities
- **AI Enhancement**: Machine learning-based improvements
- **Cross-Platform**: Native Linux and macOS support

### Contributing
1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request with detailed description

## 📄 License

MIT License - See LICENSE file for details.

## 🙏 Acknowledgments

- Original Tkinter version developers
- PySide6/Qt team for excellent GUI framework
- ComfyUI community for workflow integration
- PIL/Pillow team for image processing capabilities

## 📞 Support

For issues and feature requests:
1. Check existing issues in repository
2. Run test suite to diagnose problems
3. Provide detailed error logs and system info
4. Include sample data if applicable

---

**Super Image Processor v4.0 - Enhanced Edition**  
*Modern. Powerful. Extensible.*# organizer3
