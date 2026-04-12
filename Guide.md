# 鸟类检测系统 - 首次运行指南

本指南适用于当前 uv 工作区版本（macOS 优先）。

## 快速入门（源码运行）

1. 在项目根目录安装依赖：
   ```bash
   uv sync
   ```
2. 启动程序（推荐）：
   ```bash
   uv run bird-detector
   ```
   或使用入口文件：
   ```bash
   uv run python main.py
   ```

## 快速入门（打包后运行）

1. 在项目根目录执行打包：
   ```bash
   uv run python build_exe.py
   ```
2. macOS 默认产物：
   - `dist/BirdDetectorApp.app`
3. 首次在 macOS 打开 `.app` 可能提示来源未验证：
   - 可在系统设置中手动允许后重试
   - 或在终端移除隔离属性（仅对你信任的构建产物执行）：
     ```bash
     xattr -dr com.apple.quarantine dist/BirdDetectorApp.app
     ```

## 使用说明

### 基本操作

- **打开摄像头**：点击工具栏中的摄像头图标或选择"视频" -> "打开摄像头"
- **加载视频**：点击工具栏中的文件图标或选择"文件" -> "打开视频"
- **截图保存**：点击工具栏中的截图图标或按下 `S` 键
- **设置识别类别**：点击"设置" -> "选择识别类别"
- **设置密度图参数**：点击"设置" -> "密度图设置"

### 结果分析

- 检测结果将实时显示在主界面上
- 统计数据会在右侧面板中更新
- 检测记录保存在 `results/` 文件夹下

## 常见问题

### 启动失败

- 确认已在项目根目录执行 `uv sync`
- 确认使用的是当前项目环境启动：`uv run bird-detector`
- 若为打包版本，确认 `dist/BirdDetectorApp.app` 已生成

### 启动后无法检测

- 检查模型文件是否存在（应位于 `resources/models/`）
- 确保摄像头已正确连接并被系统识别
- 检查 `config.txt` 中模型路径是否可用

### 检测速度慢

- 在设置中降低处理分辨率
- 使用较小模型或减少识别类别数量
- 若设备支持，确保已正确安装并启用 CUDA（仅 NVIDIA 环境）

## 相关目录

- `resources/`：模型和静态资源
- `results/`：检测结果与导出数据
- `config.txt`：默认配置

## 技术支持

如有任何问题或建议，请联系开发者：

- 邮箱：support@example.com
