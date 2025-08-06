#!/usr/bin/env python3
"""
Super Image Processor v4.0 - Enhanced Edition
Main application entry point

This is a complete rewrite of the original Tkinter-based image processor,
now featuring a modern PySide6 interface with improved architecture:

- Separated core business logic from GUI
- Multi-threaded processing for responsive UI
- Enhanced error handling and logging
- Modern Qt-based interface
- Extensible plugin architecture

Author: Enhanced by Claude AI based on original Tkinter version
License: MIT
"""
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def check_dependencies():
    """Check if all required dependencies are installed"""
    missing_deps = []
    
    try:
        import PySide6
    except ImportError:
        missing_deps.append("PySide6>=6.5.0")
    
    try:
        import PIL
    except ImportError:
        missing_deps.append("Pillow>=10.0.0")
    
    try:
        import piexif
    except ImportError:
        missing_deps.append("piexif>=1.1.0")
    
    try:
        import numpy
    except ImportError:
        missing_deps.append("numpy>=1.24.0")
    
    if missing_deps:
        print("❌ Missing required dependencies:")
        for dep in missing_deps:
            print(f"  - {dep}")
        print("\n📦 Install missing dependencies with:")
        print("pip install -r requirements.txt")
        print("\nOr install individually:")
        for dep in missing_deps:
            print(f"pip install {dep}")
        return False
    
    print("✅ All dependencies are installed")
    return True

def check_external_scripts():
    """Check if external scripts are available"""
    external_dir = project_root / "external"
    required_files = [
        "pixivMosaic2.py",
        "PixivMosaicWorkflowAPI.json"
    ]
    
    missing_files = []
    for file in required_files:
        if not (external_dir / file).exists():
            missing_files.append(file)
    
    if missing_files:
        print("⚠️  Missing external files (auto-mosaic will be disabled):")
        for file in missing_files:
            print(f"  - external/{file}")
        print("\nNote: Basic image processing will still work without these files.")
        return False
    
    print("✅ All external scripts are available")
    return True

def setup_assets():
    """Ensure asset directories exist"""
    assets_dir = project_root / "assets"
    watermarks_dir = assets_dir / "watermarks"
    
    # Create directories if they don't exist
    watermarks_dir.mkdir(parents=True, exist_ok=True)
    
    return True

def main():
    """Main application entry point"""
    print("🚀 Starting Super Image Processor v4.0 - Enhanced Edition")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        return 1
    
    # Check external scripts (non-critical)
    check_external_scripts()
    
    # Setup asset directories
    setup_assets()
    
    # Import and start GUI
    try:
        from gui.main_window import MainWindow, create_application
        
        print("🎨 Initializing GUI...")
        app = create_application()
        
        print("🏠 Creating main window...")
        window = MainWindow()
        window.show()
        
        print("✅ Application started successfully!")
        print("💡 Close this console or the GUI window to exit.")
        print("=" * 60)
        
        # Run the application
        return app.exec()
        
    except ImportError as e:
        print(f"❌ Failed to import GUI components: {e}")
        print("Make sure all dependencies are installed correctly.")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1

def run_cli():
    """Run in CLI mode for batch processing (future feature)"""
    print("🖥️  CLI mode not yet implemented")
    print("Use 'python run.py' to start the GUI version")
    return 0

def show_version():
    """Show version information"""
    print("Super Image Processor v4.0 - Enhanced Edition")
    print("Built with PySide6 and modern Python architecture")
    print()
    
    # Show dependency versions
    try:
        import PySide6
        print(f"PySide6: {PySide6.__version__}")
    except ImportError:
        print("PySide6: Not installed")
    
    try:
        import PIL
        print(f"Pillow: {PIL.__version__}")
    except ImportError:
        print("Pillow: Not installed")
    
    try:
        import piexif
        print(f"piexif: {piexif.__version__}")
    except (ImportError, AttributeError):
        print("piexif: Installed (version unknown)")
    
    try:
        import numpy
        print(f"numpy: {numpy.__version__}")
    except ImportError:
        print("numpy: Not installed")

def show_help():
    """Show help information"""
    print("Super Image Processor v4.0 - Enhanced Edition")
    print("=" * 50)
    print()
    print("Usage:")
    print("  python run.py              Start GUI mode (default)")
    print("  python run.py --gui         Start GUI mode")
    print("  python run.py --cli         Start CLI mode (future feature)")
    print("  python run.py --version     Show version information")
    print("  python run.py --help        Show this help message")
    print()
    print("Features:")
    print("  📊 Metadata extraction from PNG images")
    print("  🎨 Batch image processing with watermarks")
    print("  🔒 Automatic mosaic generation (ComfyUI integration)")
    print("  ✏️ Manual mosaic editor (coming soon)")
    print("  📦 ZIP package generation")
    print("  🚀 Multi-threaded processing")
    print("  💻 Modern Qt-based interface")
    print()
    print("Dependencies:")
    print("  Run 'pip install -r requirements.txt' to install all dependencies")

if __name__ == "__main__":
    # Handle command line arguments
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ["--help", "-h"]:
            show_help()
            sys.exit(0)
        elif arg in ["--version", "-v"]:
            show_version()
            sys.exit(0)
        elif arg in ["--cli", "-c"]:
            sys.exit(run_cli())
        elif arg in ["--gui", "-g"]:
            pass  # Default behavior
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage information")
            sys.exit(1)
    
    # Run main GUI application
    sys.exit(main())