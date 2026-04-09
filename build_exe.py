"""
Bird Detector 打包脚本。

通过当前 Python 解释器调用 PyInstaller, 适合在 uv 环境中直接执行。
macOS 默认生成 .app, Windows 默认生成 .exe。
"""

from __future__ import annotations

import os
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
SPEC_FILE = PROJECT_ROOT / f"{APP_NAME}.spec"
MACOS_BUNDLE_ID = "com.tz2h.bird_detector"

HIDDEN_IMPORTS = [
    "utils.config_manager",
    "bird_detector_app.app",
    "bird_detector_app.detector",
    "ui.components",
    "ui.dialogs",
]


def get_icon_path() -> Path | None:
    """根据平台选择图标文件。"""
    if platform.system() == "Darwin":
        icon_path = PROJECT_ROOT / "resources" / "icons" / "app_icon.icns"
        return icon_path if icon_path.exists() else None

    if platform.system() == "Windows":
        icon_path = PROJECT_ROOT / "resources" / "icons" / "favicon.ico"
        return icon_path if icon_path.exists() else None

    return None


def build_data_entries() -> list[str]:
    """构建 PyInstaller 资源参数。"""
    entries = [
        f"resources{os.pathsep}resources",
        f"config.txt{os.pathsep}.",
    ]

    custom_hooks = PROJECT_ROOT / "custom_hooks.py"
    if custom_hooks.exists():
        entries.append(f"custom_hooks.py{os.pathsep}.")

    return entries


def expected_output_path() -> Path:
    """返回预期的打包产物路径。"""
    system = platform.system()
    if system == "Darwin":
        return DIST_PATH / f"{APP_NAME}.app"
    if system == "Windows":
        return DIST_PATH / f"{APP_NAME}.exe"
    return DIST_PATH / APP_NAME


def clean_previous_builds() -> None:
    """清理旧的构建产物。"""
    for path in (DIST_PATH, BUILD_PATH):
        if path.exists():
            shutil.rmtree(path)
            print(f"Deleted '{path.name}' directory.")

    if SPEC_FILE.exists():
        SPEC_FILE.unlink()
        print(f"Deleted '{SPEC_FILE.name}' file.")


def build_command() -> list[str]:
    """构建 PyInstaller 命令。"""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--name",
        APP_NAME,
        "--windowed",
    ]

    system = platform.system()
    if system == "Windows":
        command.append("--onefile")
    else:
        command.append("--onedir")
        if system == "Darwin":
            command.extend(["--osx-bundle-identifier", MACOS_BUNDLE_ID])

    icon_path = get_icon_path()
    if icon_path:
        command.extend(["--icon", str(icon_path.relative_to(PROJECT_ROOT))])
    elif system == "Darwin":
        print(
            "Warning: macOS icon not found at resources/icons/app_icon.icns, using the default app icon."
        )

    for hidden_import in HIDDEN_IMPORTS:
        command.extend(["--hidden-import", hidden_import])

    for data_entry in build_data_entries():
        command.extend(["--add-data", data_entry])

    command.append(MAIN_SCRIPT.name)
    return command


def build_executable() -> None:
    """执行打包流程。"""
    print(f"Starting build for '{APP_NAME}' in {PROJECT_ROOT}")
    print(f"Using Python interpreter: {sys.executable}")

    clean_previous_builds()

    command = build_command()
    print("\nRunning PyInstaller command:")
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
            print("--- PyInstaller Output ---")
            print(process.stdout)
        if process.stderr:
            print("--- PyInstaller Warnings/Errors ---")
            print(process.stderr)

        print(f"Build successful! Output is located at: {expected_output_path()}")
    except subprocess.CalledProcessError as error:
        print("\n--- PyInstaller Build Failed ---")
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
    except Exception as error:
        print(f"\nAn unexpected error occurred during the build process: {error}")


if __name__ == "__main__":
    build_executable()
