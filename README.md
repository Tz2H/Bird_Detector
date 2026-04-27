# 鸟类检测系统

基于 Ultralytics YOLO + PyQt5 的桌面鸟类检测应用。

当前版本以稳定性和可维护性为主，代码已采用 mixin 结构拆分，支持摄像头与本地视频两种输入。

## 当前能力

- 摄像头实时检测
- 本地视频检测（后台快速推理输出流，减少 UI 卡顿）
- 仅保留 bird 类检测
- 实时空间热力图显示
- 检测数据导出（当前帧手动导出 + 运行时自动写入结果目录）

## 技术栈

- Python 3.9+
- PyQt5
- OpenCV
- Ultralytics YOLO
- Matplotlib
- uv（推荐）
- Nuitka（可选打包）

## 安装与启动

### 推荐：uv

1. 安装依赖

```bash
uv sync
```

2. 启动应用

```bash
uv run bird-detector
```

也可直接运行入口文件：

```bash
uv run python src/main.py
```

### 兼容：pip

```bash
pip install -r requirements.txt
python src/main.py
```

## 打包（Nuitka）

```bash
uv run python build_nuitka.py
```

默认输出：

- macOS: `dist/BirdDetector.app`
- Windows: `dist/BirdDetectorApp.dist/BirdDetectorApp.exe`

构建脚本会自动包含：

- `src/resources/`
- `config.txt`

## 运行行为说明

### 输入源

- 摄像头：按开始检测后进行推理
- 视频文件：打开视频后自动开始检测；播放完成后自动停止检测并暂停视频

### 检测模式

- 摄像头路径：异步推理，优先保证交互响应
- 视频路径：后台线程持续快速推理，UI 侧按视频 FPS 消费带框输出流

### 热力图

- 右侧面板实时显示空间热力分布
- 检测停止、视频播放完成、程序关闭时会保存热力图快照到 `results/`

### CSV 数据

- 顶部/菜单“保存数据”可导出当前帧检测结果为 CSV
- 运行中会按秒节流自动写入 `results/object_detection_*.csv`

## 配置文件

默认读取项目根目录的 `config.txt`，支持字段：

- `model=...`
- `classes=...`
- `heatmap=...`

当前主流程会强制仅使用 bird 类进行检测与热力图统计。

## 代码结构（当前实现）

```
src/
├── main.py
├── resources/
├── bird_detector_app/
│   ├── app.py            # 主窗口初始化与运行时状态
│   ├── config_mixin.py   # 菜单、托盘、配置加载
│   ├── layout_mixin.py   # 界面布局
│   ├── runtime_mixin.py  # 视频流、推理调度、热力图与导出
│   ├── style_mixin.py    # 全局样式
│   ├── detector.py       # YOLO 推理与框绘制
│   └── paths.py          # 项目路径常量
├── utils/
│   └── config_manager.py
└── ui/
    └── components.py
```

## 常见问题

### 启动报模型相关错误

- 检查 `src/resources/models/yolo11m.pt` 是否存在
- 检查 `config.txt` 的 `model=` 路径是否有效

### 视频检测卡顿

- 当前版本已启用视频快速推理输出流
- 若仍卡顿，优先使用更低分辨率视频源或更强硬件

### 无热力图数据

- 确认检测到 bird 目标后再观察热力图
- 停止检测或播放完成后，会在 `results/` 目录生成热力图快照

© 2026 Zhouhang Tang
