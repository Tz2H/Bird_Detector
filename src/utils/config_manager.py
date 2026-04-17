"""
Configuration helpers for model and class preferences.
Author: Tz2H
"""

import os
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
DEFAULT_MODEL_PATH = SRC_ROOT / "resources" / "models" / "yolo11m.pt"
CONFIG_FILE = PROJECT_ROOT / "config.txt"


def resolve_model_path(model_path):
    """Resolve a model path across src layout and legacy path styles."""
    if not model_path:
        return str(DEFAULT_MODEL_PATH)

    raw_path = Path(model_path).expanduser()
    if raw_path.is_absolute() and raw_path.exists():
        return str(raw_path)

    candidates = [
        PROJECT_ROOT / raw_path,
        SRC_ROOT / raw_path,
    ]

    model_path_text = str(raw_path).replace("\\", "/")
    if model_path_text.startswith("resources/"):
        candidates.append(PROJECT_ROOT / "src" / raw_path)

    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())

    return str(DEFAULT_MODEL_PATH)


def load_initial_config():
    """Load initial application configuration."""
    # Use project defaults when no user config exists.
    config = {
        "model_path": str(DEFAULT_MODEL_PATH),
        "selected_classes": set(),
        "heatmap_classes": set(),
    }

    # Read user overrides from config.txt.
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("model="):
                        config["model_path"] = line.split("=", 1)[1].strip()
                    elif line.startswith("classes="):
                        classes_str = line.split("=", 1)[1].strip()
                        if classes_str:
                            config["selected_classes"] = {
                                cls for cls in classes_str.split(",") if cls
                            }
                            # Default heatmap classes to selected classes.
                            config["heatmap_classes"] = set(config["selected_classes"])
                    elif line.startswith("heatmap="):
                        heatmap_str = line.split("=", 1)[1].strip()
                        if heatmap_str:
                            config["heatmap_classes"] = {
                                cls for cls in heatmap_str.split(",") if cls
                            }
        except Exception as e:
            print(f"Failed to read config.txt: {e}")

    if config["selected_classes"] and not config["heatmap_classes"]:
        config["heatmap_classes"] = set(config["selected_classes"])

    config["model_path"] = resolve_model_path(config["model_path"])

    return config


def save_config(model_path, selected_classes, heatmap_classes=None):
    """Persist model and class settings to config.txt."""
    try:
        model_path_value = resolve_model_path(model_path)
        try:
            model_path_value = os.path.relpath(model_path_value, PROJECT_ROOT)
        except ValueError:
            # Keep absolute paths when relative conversion is not possible.
            pass

        sorted_selected = sorted(selected_classes) if selected_classes else []
        sorted_heatmap = sorted(heatmap_classes) if heatmap_classes else []

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"model={model_path_value}\n")
            f.write("classes=" + ",".join(sorted_selected) + "\n")
            f.write("heatmap=" + ",".join(sorted_heatmap) + "\n")
        return True
    except Exception as e:
        print(f"Failed to save config.txt: {e}")
        return False
