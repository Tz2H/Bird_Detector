"""
配置管理工具模块
Creater Tz2H
"""

import os
from pathlib import Path


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
DEFAULT_MODEL_PATH = SRC_ROOT / "resources" / "models" / "yolo11m.pt"
CONFIG_FILE = PROJECT_ROOT / "config.txt"


def resolve_model_path(model_path):
    """解析模型路径，兼容 src layout 和旧配置路径。"""
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
    """加载初始配置"""
    # 默认配置
    config = {
        "model_path": str(DEFAULT_MODEL_PATH),
        "selected_classes": set(),
        "density_classes": set(),
    }

    # 尝试从config.txt加载配置
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
                            # 如果config有识别类别，密度图默认与识别类别一致
                            config["density_classes"] = set(config["selected_classes"])
                    elif line.startswith("density="):
                        density_str = line.split("=", 1)[1].strip()
                        if density_str:
                            config["density_classes"] = {
                                cls for cls in density_str.split(",") if cls
                            }
        except Exception as e:
            print(f"读取config.txt失败: {e}")

    if config["selected_classes"] and not config["density_classes"]:
        config["density_classes"] = set(config["selected_classes"])

    config["model_path"] = resolve_model_path(config["model_path"])

    return config


def save_config(model_path, selected_classes, density_classes=None):
    """保存配置到文件"""
    try:
        model_path_value = resolve_model_path(model_path)
        try:
            model_path_value = os.path.relpath(model_path_value, PROJECT_ROOT)
        except ValueError:
            # 可能是不同盘符或系统路径，保留绝对路径
            pass

        sorted_selected = sorted(selected_classes) if selected_classes else []
        sorted_density = sorted(density_classes) if density_classes else []

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(f"model={model_path_value}\n")
            f.write("classes=" + ",".join(sorted_selected) + "\n")
            f.write("density=" + ",".join(sorted_density) + "\n")
        return True
    except Exception as e:
        print(f"保存config.txt失败: {e}")
        return False
