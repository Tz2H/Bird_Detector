"""
Nuitka build script for Bird Detector.

Use the current interpreter to build the desktop app.
Recommended entrypoint:
    uv run python build_nuitka.py
"""

import os
import platform
import shutil
import subprocess
import sys
from importlib.util import find_spec
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_BUNDLE_NAME = "BirdDetector"
APP_EXECUTABLE_NAME = "BirdDetectorApp"
MAIN_SCRIPT = PROJECT_ROOT / "src" / "main.py"
DIST_PATH = PROJECT_ROOT / "dist"
BUILD_PATH = PROJECT_ROOT / "build"

def clean_builds() -> None:
    """Clean previous build artifacts."""
    for path in [DIST_PATH, BUILD_PATH]:
        if path.exists():
            shutil.rmtree(path)
            print(f"Deleted '{path.name}' directory.")
            
    # Clean root-level build caches and stale targets
    stale_extensions = ["*.dist", "*.build", "*.onefile-build", "*.app"]
    for ext in stale_extensions:
        for stale in PROJECT_ROOT.glob(ext):
            shutil.rmtree(stale)
            print(f"Deleted stale output '{stale.name}'.")

def get_build_command() -> list[str]:
    """Construct the Nuitka compilation command."""
    jobs = max(1, (os.cpu_count() or 4) - 1)
    
    command = [
        sys.executable, "-m", "nuitka",
        str(MAIN_SCRIPT.relative_to(PROJECT_ROOT)),
        "--standalone",
        "--remove-output",
        "--assume-yes-for-downloads",
        f"--jobs={jobs}",
        "--lto=no",
        "--enable-plugin=pyqt5",
        "--include-qt-plugins=sensible,styles",
        f"--output-dir={DIST_PATH}",
        f"--output-filename={APP_EXECUTABLE_NAME}",
        "--include-package=bird_detector_app",
        "--include-package=ui",
        "--include-package=utils",
        f"--include-data-dir={PROJECT_ROOT / 'src' / 'resources'}=resources",
        f"--include-data-file={PROJECT_ROOT / 'config.txt'}=config.txt",
    ]

    # Exclude bloated torch headers to save space and speed up build
    if os.environ.get("NUITKA_KEEP_TORCH_HEADERS", "0") != "1":
        for ext in ("h", "hpp", "hh", "hxx", "cuh"):
            command.append(f"--noinclude-data-files=*.{ext}")

    # Include ultralytics configs if the library is installed
    if (spec := find_spec("ultralytics")) and spec.origin:
        cfg_dir = Path(spec.origin).resolve().parent / "cfg"
        if cfg_dir.exists():
            command.append(f"--include-data-dir={cfg_dir}=ultralytics/cfg")

    system = platform.system()
    icons_dir = PROJECT_ROOT / "src" / "resources" / "icons"
    
    if system == "Darwin":
        command.extend([
            "--macos-create-app-bundle",
            f"--macos-app-name={APP_BUNDLE_NAME}",
            "--macos-app-protected-resource=NSCameraUsageDescription:Camera access is required for real-time bird detection.",
            "--macos-app-protected-resource=NSMicrophoneUsageDescription:Microphone access is required by OpenCV for video capture init."
        ])
        icns_path = icons_dir / "app_icon.icns"
        if icns_path.exists():
            command.append(f"--macos-app-icon={icns_path}")
            
    elif system == "Windows":
        command.append("--windows-disable-console")
        ico_path = icons_dir / "favicon.ico"
        if ico_path.exists():
            command.append(f"--windows-icon-from-ico={ico_path}")

    return command

def build_executable() -> None:
    """Run Nuitka packaging."""
    print(f"Starting Nuitka build for '{APP_BUNDLE_NAME}' in {PROJECT_ROOT}")
    print(f"Using Python interpreter: {sys.executable}")
    
    clean_builds()
    
    command = get_build_command()
    print("\nRunning Nuitka command:")
    print(f"  {' '.join(command)}\n")
    
    try:
        # standard subprocess call, delegates output directly to terminal
        subprocess.check_call(command, cwd=PROJECT_ROOT)
        
        # Rename main.app to BirdDetector.app if running on macOS
        if platform.system() == "Darwin":
            generated = DIST_PATH / f"{MAIN_SCRIPT.stem}.app"
            expected = DIST_PATH / f"{APP_BUNDLE_NAME}.app"
            if generated.exists() and generated != expected:
                if expected.exists():
                    shutil.rmtree(expected)
                generated.rename(expected)
                
        print("\nBuild successful!")
    except subprocess.CalledProcessError as error:
        print(f"\n--- Nuitka Build Failed with exit code {error.returncode} ---")
        sys.exit(error.returncode)

if __name__ == "__main__":
    build_executable()
