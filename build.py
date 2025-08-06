#!/usr/bin/env python3
"""
Build script for Super Image Processor v4.0 - Enhanced Edition
Creates a standalone executable using PyInstaller
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
SPEC_FILE = PROJECT_ROOT / "SuperImageProcessor.spec"

def clean_build_dirs():
    """Clean previous build artifacts"""
    print("🧹 Cleaning previous build artifacts...")
    
    for dir_path in [DIST_DIR, BUILD_DIR]:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"   Removed {dir_path}")

def create_pyinstaller_spec():
    """Create PyInstaller spec file"""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

# Project paths
project_root = Path(SPECPATH)
external_dir = project_root / "external"
assets_dir = project_root / "assets"

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(external_dir), 'external'),
        (str(assets_dir), 'assets'),
    ],
    hiddenimports=[
        'PIL._tkinter_finder',
        'pkg_resources.py2_warn',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SuperImageProcessor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for debugging
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one
)
'''
    
    print("📄 Creating PyInstaller spec file...")
    with open(SPEC_FILE, 'w', encoding='utf-8') as f:
        f.write(spec_content)
    print(f"   Created {SPEC_FILE}")

def build_executable():
    """Build the executable using PyInstaller"""
    print("🔨 Building executable with PyInstaller...")
    
    try:
        # Run PyInstaller
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', str(SPEC_FILE)]
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Build completed successfully!")
            
            # Check if executable was created
            exe_path = DIST_DIR / "SuperImageProcessor.exe"
            if exe_path.exists():
                size_mb = exe_path.stat().st_size / (1024 * 1024)
                print(f"   📦 Executable created: {exe_path}")
                print(f"   📏 Size: {size_mb:.1f} MB")
                return True
            else:
                print("❌ Executable not found after build")
                return False
        else:
            print(f"❌ Build failed with code {result.returncode}")
            print(f"STDOUT: {result.stdout}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Build error: {e}")
        return False

def test_executable():
    """Test the built executable"""
    exe_path = DIST_DIR / "SuperImageProcessor.exe"
    if not exe_path.exists():
        print("❌ Executable not found for testing")
        return False
    
    print("🧪 Testing executable...")
    try:
        # Test with --version flag
        result = subprocess.run([str(exe_path), '--version'], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ Executable test passed!")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Executable test failed with code {result.returncode}")
            print(f"STDERR: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Executable test timed out")
        return False
    except Exception as e:
        print(f"❌ Test error: {e}")
        return False

def create_installer_info():
    """Create information for installer creation"""
    info_content = f"""
# Super Image Processor v4.0 - Enhanced Edition
# Build Information

## Executable Location
{DIST_DIR / 'SuperImageProcessor.exe'}

## Required Files (bundled in executable)
- Core processing modules
- PySide6 GUI framework  
- PIL/Pillow image libraries
- External workflow scripts
- Asset files

## External Dependencies
The following files should be present in the same directory as the executable:
- external/pixivMosaic2.py (for auto-mosaic functionality)
- external/PixivMosaicWorkflowAPI.json (ComfyUI workflow)

## Watermark Files
Default watermark files should be located at:
- D:/adolfocesar/content/marcadaguas/lovehent_watermark.png
- D:/adolfocesar/content/marcadaguas/violetjoi_watermark.png  
- D:/adolfocesar/content/marcadaguas/vixmavis_watermark.png

## Usage
Double-click SuperImageProcessor.exe to start the GUI application.

For command line usage:
SuperImageProcessor.exe --help

## System Requirements
- Windows 10/11
- At least 4GB RAM
- 500MB free disk space
- ComfyUI installation (for auto-mosaic features)
"""
    
    info_path = DIST_DIR / "README.txt"
    with open(info_path, 'w', encoding='utf-8') as f:
        f.write(info_content)
    
    print(f"📋 Created installer info: {info_path}")

def main():
    """Main build process"""
    print("🚀 Super Image Processor v4.0 - Build Process")
    print("=" * 50)
    
    # Check if PyInstaller is available
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} found")
    except ImportError:
        print("❌ PyInstaller not found. Install with: pip install pyinstaller")
        return 1
    
    # Build process
    steps = [
        ("Clean build directories", clean_build_dirs),
        ("Create PyInstaller spec", create_pyinstaller_spec),
        ("Build executable", build_executable),
        ("Test executable", test_executable),
        ("Create installer info", create_installer_info),
    ]
    
    for step_name, step_func in steps:
        print(f"\n📋 {step_name}...")
        try:
            success = step_func()
            if success is False:
                print(f"❌ {step_name} failed!")
                return 1
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            return 1
    
    print("\n" + "=" * 50)
    print("🎉 Build process completed successfully!")
    print(f"📦 Executable: {DIST_DIR / 'SuperImageProcessor.exe'}")
    print(f"📋 Info file: {DIST_DIR / 'README.txt'}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())