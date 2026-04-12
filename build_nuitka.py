"""
Nuitka build script for Bird Detector.

Use the current interpreter to build the desktop app.
Recommended entrypoint:
    uv run python build_nuitka.py
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_NAME = "BirdDetectorApp"
MAIN_SCRIPT = PROJECT_ROOT / "main.py"
DIST_PATH = PROJECT_ROOT / "dist"
BUILD_PATH = PROJECT_ROOT / "build"


def expected_output_path() -> Path:
    """Return the expected build output path."""
    system = platform.system()
    if system == "Darwin":
        return DIST_PATH / f"{APP_NAME}.app"
    return DIST_PATH / f"{APP_NAME}.dist"


def icon_arguments() -> list[str]:
    """Build platform-specific icon arguments."""
    icons_dir = PROJECT_ROOT / "resources" / "icons"
    system = platform.system()

    if system == "Darwin":
        icns_path = icons_dir / "app_icon.icns"
        if icns_path.exists():
            return [f"--macos-app-icon={icns_path}"]

        print(
            "Warning: macOS icon not found at resources/icons/app_icon.icns, using default app icon."
        )
        return []

    if system == "Windows":
        ico_path = icons_dir / "favicon.ico"
        if ico_path.exists():
            return [f"--windows-icon-from-ico={ico_path}"]

    return []


def clean_previous_builds() -> None:
    """Remove old artifacts to keep the output deterministic."""
    for path in (DIST_PATH, BUILD_PATH):
        if path.exists():
            shutil.rmtree(path)
            print(f"Deleted '{path.name}' directory.")

    stale_outputs = [
        PROJECT_ROOT / f"{APP_NAME}.build",
        PROJECT_ROOT / f"{APP_NAME}.dist",
        PROJECT_ROOT / f"{APP_NAME}.onefile-build",
        PROJECT_ROOT / f"{MAIN_SCRIPT.stem}.build",
        PROJECT_ROOT / f"{MAIN_SCRIPT.stem}.dist",
        PROJECT_ROOT / f"{MAIN_SCRIPT.stem}.onefile-build",
    ]
    for path in stale_outputs:
        if path.exists():
            shutil.rmtree(path)
            print(f"Deleted stale output '{path.name}'.")


def build_command() -> list[str]:
    """Construct a Nuitka command suitable for this project."""
    command = [
        sys.executable,
        "-m",
        "nuitka",
        MAIN_SCRIPT.name,
        "--standalone",
        "--remove-output",
        "--assume-yes-for-downloads",
        "--enable-plugin=pyqt5",
        "--include-qt-plugins=sensible,styles",
        f"--output-dir={DIST_PATH}",
        f"--output-filename={APP_NAME}",
        "--include-package=bird_detector_app",
        "--include-package=ui",
        "--include-package=utils",
        f"--include-data-dir={PROJECT_ROOT / 'resources'}=resources",
        f"--include-data-file={PROJECT_ROOT / 'config.txt'}=config.txt",
    ]

    system = platform.system()
    if system == "Darwin":
        command.extend(
            [
                "--macos-create-app-bundle",
                f"--macos-app-name={APP_NAME}",
            ]
        )
    elif system == "Windows":
        command.append("--windows-disable-console")

    command.extend(icon_arguments())
    return command


def build_executable() -> None:
    """Run Nuitka packaging."""
    print(f"Starting Nuitka build for '{APP_NAME}' in {PROJECT_ROOT}")
    print(f"Using Python interpreter: {sys.executable}")

    clean_previous_builds()

    command = build_command()
    print("\nRunning Nuitka command:")
    print(f"  {' '.join(command)}\n")

    try:
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=PROJECT_ROOT,
        )

        if process.stdout:
            print("--- Nuitka Output ---")
            print(process.stdout)
        if process.stderr:
            print("--- Nuitka Warnings ---")
            print(process.stderr)

        print(f"Build successful! Output is located at: {expected_output_path()}")
    except subprocess.CalledProcessError as error:
        print("\n--- Nuitka Build Failed ---")
        stderr_output = (
            error.stderr.decode("utf-8", errors="replace")
            if isinstance(error.stderr, bytes)
            else error.stderr
        )
        stdout_output = (
            error.stdout.decode("utf-8", errors="replace")
            if isinstance(error.stdout, bytes)
            else error.stdout
        )

        if stderr_output:
            print(stderr_output)
        if stdout_output:
            print("\nStandard Output (if any):")
            print(stdout_output)

        print("\nCheck the missing dependency or resource path reported above.")
    except Exception as error:  # pragma: no cover
        print(f"\nAn unexpected error occurred during the build process: {error}")


if __name__ == "__main__":
    build_executable()
