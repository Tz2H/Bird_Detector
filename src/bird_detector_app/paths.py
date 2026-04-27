"""Common project paths for the Bird Detector application."""

from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
RESOURCES_DIR = SRC_ROOT / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
CONFIG_FILE = PROJECT_ROOT / "config.txt"
DEFAULT_MODEL_PATH = RESOURCES_DIR / "models" / "yolo11m.pt"
