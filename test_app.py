#!/usr/bin/env python3
"""
Simple test script for Super Image Processor v4.0
Tests basic functionality without GUI
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test core imports
        from core.utils import CoreConfig, WatermarkConfig, CoreCallbacks
        from core.metadata import extract_png, embed
        from core.watermark import get_default_watermarks
        from core.processor import ImageProcessorCore
        from core.auto_mosaic import AutoMosaicProcessor
        print("✅ Core modules imported successfully")
        
        # Test GUI imports (optional)
        try:
            from gui.main_window import MainWindow, create_application
            from gui.worker_thread import WorkerThread
            from gui.manual_editor import ManualMosaicEditor
            print("✅ GUI modules imported successfully")
            gui_available = True
        except ImportError as e:
            print(f"⚠️ GUI modules not available: {e}")
            gui_available = False
        
        return True, gui_available
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False, False

def test_core_functionality():
    """Test core functionality without GUI"""
    print("\n🔧 Testing core functionality...")
    
    try:
        from core.utils import CoreConfig, WatermarkConfig, CoreCallbacks
        from core.watermark import get_default_watermarks, validate_watermark_file
        
        # Test watermark configuration
        watermarks = get_default_watermarks()
        print(f"   Found {len(watermarks)} default watermarks")
        
        # Test validation
        for name, path in watermarks.items():
            is_valid = validate_watermark_file(path)
            status = "✅" if is_valid else "❌"
            print(f"   {status} {name}: {path}")
        
        # Test config creation
        if watermarks:
            first_watermark = list(watermarks.items())[0]
            wm_config = WatermarkConfig(
                name=first_watermark[0],
                path=first_watermark[1]
            )
            
            config = CoreConfig(
                input_folder=Path("."),
                watermark=wm_config
            )
            print("✅ Configuration objects created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Core functionality test failed: {e}")
        return False

def test_external_files():
    """Test external files availability"""
    print("\n📁 Testing external files...")
    
    external_dir = project_root / "external"
    required_files = [
        "pixivMosaic2.py",
        "PixivMosaicWorkflowAPI.json"
    ]
    
    all_present = True
    for file in required_files:
        file_path = external_dir / file
        if file_path.exists():
            print(f"✅ {file} found")
        else:
            print(f"❌ {file} missing")
            all_present = False
    
    return all_present

def test_gui_creation():
    """Test GUI creation (if available)"""
    print("\n🖼️ Testing GUI creation...")
    
    try:
        from gui.main_window import create_application
        
        # Create application (but don't show)
        app = create_application()
        print("✅ QApplication created successfully")
        
        # Try to create main window (but don't show)
        from gui.main_window import MainWindow
        # Note: We can't actually create the window in headless environment
        print("✅ MainWindow class imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Super Image Processor v4.0 - Test Suite")
    print("=" * 50)
    
    # Test imports
    core_ok, gui_ok = test_imports()
    if not core_ok:
        print("❌ Critical: Core modules cannot be imported")
        return 1
    
    # Test core functionality
    if not test_core_functionality():
        print("❌ Critical: Core functionality test failed")
        return 1
    
    # Test external files
    external_ok = test_external_files()
    if not external_ok:
        print("⚠️ Warning: Some external files are missing")
    
    # Test GUI (if available)
    if gui_ok:
        gui_test_ok = test_gui_creation()
        if not gui_test_ok:
            print("⚠️ Warning: GUI test failed")
    
    print("\n" + "=" * 50)
    if core_ok:
        print("🎉 Core functionality tests passed!")
        if gui_ok:
            print("🖼️ GUI components are available")
        if external_ok:
            print("📁 All external files are present")
        
        print("\n✅ Application should be ready to run!")
        print("   Use: python run.py")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())