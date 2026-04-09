# 鸟类检测系统

基于 YOLO 的智能鸟类检测系统，使用 PyQt5 构建用户界面。

## 功能特点

- 实时摄像头检测
- 视频文件检测
- 多类别检测与过滤
- 检测数据统计与可视化
- 数据保存与导出

## 系统要求

- Python 3.9+
- OpenCV
- PyQt5
- Ultralytics YOLO
- PyInstaller（用于打包）

## 安装与启动

1. 安装依赖：
   ```bash
   uv sync
   ```
2. 启动程序：
   ```bash
   uv run bird-detector
   ```
   也可以直接运行入口文件：
   ```bash
   uv run python main.py
   ```

如果你需要兼容旧的 pip 流程，也可以继续使用：

```bash
pip install -r requirements.txt
python main.py
```

## 打包应用程序

项目包含 `build_exe.py`，会通过当前 uv 环境调用 PyInstaller。

```bash
uv run python build_exe.py
```

打包结果会根据平台自动区分：

- macOS：生成 `dist/BirdDetectorApp.app`
- Windows：生成 `dist/BirdDetectorApp.exe`

脚本会自动包含 `resources/` 和 `config.txt`。

如果你要给 macOS 版本设置自定义图标，可以补充 `resources/icons/app_icon.icns`。

## 项目结构

```
Bird_Detector/
├── bird_detector_app/     # 主程序包
├── resources/             # 资源文件
├── ui/                    # UI组件
├── utils/                 # 实用工具
├── main.py                # 程序入口
├── build_exe.py           # PyInstaller 打包脚本
├── config.txt             # 默认配置
├── requirements.txt       # 传统依赖列表
└── README.md              # 项目说明文件
```

## 使用方法

1. 启动程序。
2. 使用设置菜单选择模型和需要检测的类别。
3. 选择视频源（摄像头或视频文件）。
4. 点击“开始检测”按钮进行检测。
5. 检测结果将显示在界面上，同时可保存为 CSV 文件。

## 运行时输出

- 检测结果 CSV 和趋势图会写入 `results/`。
- 首次启动会读取 `config.txt` 中的模型和类别配置。

## 许可证

© 2025 版权所有 Tz2H
