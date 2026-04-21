# 鸟类检测系统 - 使用指南（当前版本）

本指南基于当前代码实现编写，适用于 uv 工作流（macOS/Windows 均可参考）。

## 1. 启动方式

### 1.1 源码运行（推荐）

```bash
uv sync
uv run bird-detector
```

或：

```bash
uv run python src/main.py
```

### 1.2 打包运行（可选）

```bash
uv run python build_nuitka.py
```

默认产物：

- macOS: `dist/BirdDetector.app`
- Windows: `dist/BirdDetectorApp.dist/BirdDetectorApp.exe`

如果 macOS 首次打开被阻止：

```bash
xattr -dr com.apple.quarantine dist/BirdDetector.app
```

## 2. 界面说明

### 2.1 菜单栏

- 文件
  - 打开视频（Ctrl+O）
  - 保存数据（Ctrl+S）
  - 退出（Ctrl+Q）
- 视图
  - 全屏（F11）
- 帮助
  - 关于

### 2.2 顶部按钮

- 保存数据为 CSV

### 2.3 左侧区域

- 视频源下拉：摄像头 / 视频文件
- 分辨率下拉：当前为预留项，暂未接入实时切换逻辑
- 视频画面：显示实时带框结果
- 状态栏：显示识别数量与 FPS

### 2.4 右侧区域

- 空间热力分布图（实时更新）
- 实时状态跟踪日志
- 开始检测 / 停止检测 按钮

### 2.5 状态栏与托盘

- 底部状态栏显示实时提示
- 系统托盘支持“显示/退出”

## 3. 当前检测逻辑

### 3.1 类别策略

当前版本仅保留 bird 类检测与热力图统计。

### 3.2 输入源行为

- 摄像头模式
  - 使用异步推理路径
  - 优先交互响应
  - 首次使用时会弹出摄像头选择对话框
- 视频文件模式
  - 打开视频后自动开始检测
  - 菜单“打开视频”或视频源下拉切到“视频文件”都会触发文件选择
  - 后台线程快速推理生成带框输出流
  - UI 按源 FPS 节奏消费结果帧
  - 播放完成后自动停止检测并暂停视频

### 3.3 热力图与结果输出

- 右侧热力图实时绘制
- 以下时机会保存热力图快照到 `results/`
  - 手动停止检测
  - 视频播放结束
  - 程序关闭
- 检测 CSV
  - 自动按秒节流写入 `results/object_detection_*.csv`
  - 手动导出功能保存当前帧检测数据

## 4. 配置文件

根目录 `config.txt` 支持字段：

- `model=...`
- `classes=...`
- `heatmap=...`

说明：

- 启动时会读取配置
- 运行时主流程会将检测类别限制为 bird

## 5. 常见问题

### 5.1 程序无法启动

- 先执行 `uv sync`
- 再执行 `uv run bird-detector`
- 检查模型文件是否存在：`src/resources/models/yolo11m.pt`

### 5.2 打开视频后没有检测结果

- 确认视频中确实存在 bird 目标
- 查看状态栏是否有模型加载失败提示

### 5.3 热力图没有变化

- 热力图仅统计检测到的 bird 目标
- 无有效目标时会显示“暂无数据”

### 5.4 导出 CSV 看起来数据较少

- 手动导出是当前帧数据快照
- 运行中自动结果在 `results/object_detection_*.csv`

## 6. 关键目录

- `src/bird_detector_app/`: 主应用逻辑（mixin 架构）
- `src/resources/`: 模型与图标
- `src/utils/config_manager.py`: 配置读取与路径解析
- `results/`: 运行结果输出目录
