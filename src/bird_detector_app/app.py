"""
Main GUI application for Bird Detector.
Author: Tz2H
"""

import csv
import gc
import os
from datetime import datetime
from pathlib import Path

import cv2
import matplotlib
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import QDateTime, Qt, QTimer
from PyQt5.QtGui import (
    QIcon,
    QImage,
    QPixmap,
)
from PyQt5.QtWidgets import (
    QAction,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QStatusBar,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from ui.components import MacStyleButton, MacStyleFrame
from ui.dialogs import DensityDialog, SettingsDialog
from utils.config_manager import resolve_model_path, save_config

from bird_detector_app.detector import ObjectDetector


SRC_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_ROOT.parent
RESOURCES_DIR = SRC_ROOT / "resources"
ICONS_DIR = RESOURCES_DIR / "icons"
CONFIG_FILE = PROJECT_ROOT / "config.txt"
DEFAULT_MODEL_PATH = RESOURCES_DIR / "models" / "yolo11m.pt"


def configure_matplotlib_fonts():
    """Configure a robust CJK font fallback list for Matplotlib."""
    preferred_fonts = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    current_fonts = list(matplotlib.rcParams.get("font.sans-serif", []))
    merged_fonts = []
    for name in preferred_fonts + current_fonts:
        if name not in merged_fonts:
            merged_fonts.append(name)
    matplotlib.rcParams["font.sans-serif"] = merged_fonts
    matplotlib.rcParams["axes.unicode_minus"] = False


class YoloVisualizationApp(QMainWindow):
    """Main window for real-time YOLO visualization."""

    def __init__(self):
        """Initialize the main window and runtime state."""
        super().__init__()
        configure_matplotlib_fonts()
        self.setWindowTitle("鸟类检测系统")
        self.setGeometry(100, 100, 1440, 900)

        # Initialize runtime state.
        self.all_classes = []
        self.selected_classes = set()
        self.density_classes = set()
        self.model_path = None
        self.is_detecting = False
        self.frame_count = 0
        self.fps = 0
        self.last_fps_update = QDateTime.currentDateTime()
        self.available_cameras = self.detect_cameras()
        self.selected_camera = None
        self.last_frame_time = QDateTime.currentDateTime()
        self.last_chart_update = QDateTime.currentDateTime()
        self.chart_update_interval_ms = 250
        self.last_csv_save_second = None

        # Initialize detector backend.
        self.bird_detector = ObjectDetector(str(DEFAULT_MODEL_PATH))

        # Apply global stylesheet.
        self.set_application_style()

        # Create and attach the central widget.
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Build the menu bar.
        self.create_menu_bar()

        # Build the toolbar.
        self.create_tool_bar()

        # Build status bar.
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("系统就绪")

        # Main vertical layout.
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(18)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Top action row with settings and export buttons.
        self.create_top_buttons(main_layout)

        # Middle content row: left video panel, right chart panel.
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Left panel: video and counters.
        self.create_left_panel(content_layout)

        # Right panel: density chart and controls.
        self.create_right_panel(content_layout)

        # Attach content layout below the top row.
        main_layout.addLayout(content_layout, 1)

        # Initialize the embedded Matplotlib canvas.
        self.init_matplotlib_canvas()

        # Default density classes follow detection classes.
        self.density_classes = set(self.all_classes)
        self.bird_detector.density_classes = set(self.all_classes)

        # Initialize video capture and timer.
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(1)  # Run as fast as possible with a 1 ms interval.

        # Buffer detection samples for the density chart.
        self.recognition_data = []  # [(timestamp, total_count, {class_name: count}), ...]

        # Initialize system tray icon.
        self.create_tray_icon()

        # Load persisted user configuration.
        self.load_config()

    def set_application_style(self):
        """Apply stylesheet rules for the whole application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #15171B;
            }
            QWidget {
                background-color: transparent;
                color: #E6EAF0;
                font-family: "Microsoft YaHei UI", "Segoe UI", "PingFang SC";
                font-size: 12px;
            }
            QLabel {
                color: #E6EAF0;
                font-size: 12px;
                font-weight: 400;
            }
            QMenuBar {
                background-color: #1B1E23;
                color: #E6EAF0;
                border-bottom: 1px solid #2B2F36;
            }
            QMenuBar::item:selected {
                background-color: #232731;
                border-radius: 6px;
            }
            QMenu {
                background-color: #1B1E23;
                border: 1px solid #2B2F36;
                border-radius: 8px;
                padding: 6px;
            }
            QMenu::item:selected {
                background-color: #232731;
                border-radius: 6px;
            }
            QStatusBar {
                background-color: #1B1E23;
                color: #C9D1DB;
                border-top: 1px solid #2B2F36;
            }
            QComboBox {
                background-color: #1F2227;
                color: #E6EAF0;
                border: 1px solid #2B2F36;
                border-radius: 8px;
                padding: 6px 10px;
                min-height: 28px;
            }
            QComboBox:hover {
                background-color: #232731;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QProgressBar {
                background-color: #232731;
                border: none;
                border-radius: 6px;
                text-align: center;
                color: #E6EAF0;
            }
            QProgressBar::chunk {
                background-color: #4F6EF7;
                border-radius: 6px;
            }
            QToolBar {
                background-color: #1B1E23;
                border: none;
                spacing: 5px;
            }
            QToolBar::separator {
                width: 1px;
                background-color: #2B2F36;
                margin: 5px;
            }
            QPushButton {
                background-color: #232731;
                color: #E6EAF0;
                border: 1px solid #2B2F36;
                border-radius: 8px;
                padding: 6px 12px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #2A2F3A;
            }
            QPushButton:pressed {
                background-color: #1F232C;
            }
            QPushButton:disabled {
                background-color: #1C2026;
                color: #7E8796;
                border: 1px solid #262A31;
            }
            QDialog {
                background-color: #181B20;
            }
            QScrollArea {
                background-color: transparent;
                border: 1px solid #2B2F36;
                border-radius: 10px;
            }
            QScrollArea QWidget {
                background-color: transparent;
            }
            QCheckBox {
                spacing: 8px;
                color: #D5DBE5;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 4px;
                border: 1px solid #39404C;
                background: #1F2227;
            }
            QCheckBox::indicator:checked {
                background: #4F6EF7;
                border: 1px solid #4F6EF7;
            }
            QLabel#videoDisplay, QLabel#densityPanel {
                background-color: #1C1F25;
                border: 1px solid #2B2F36;
                border-radius: 12px;
                padding: 12px;
                color: #C9D1DB;
                font-size: 12px;
            }
            QLabel#statLabel {
                font-size: 13px;
                font-weight: 600;
                color: #E6EAF0;
            }
        """)

    def create_top_buttons(self, main_layout):
        """Create the top action row."""
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.setSpacing(12)

        # Settings button
        self.settings_btn = MacStyleButton("设置")
        self.settings_btn.setFixedWidth(100)
        self.settings_btn.clicked.connect(self.show_settings_dialog)
        top_buttons_layout.addWidget(self.settings_btn, alignment=Qt.AlignLeft)

        top_buttons_layout.addStretch()

        # CSV export button
        self.save_csv_button = MacStyleButton("保存数据为 CSV")
        self.save_csv_button.setIcon(
            self.style().standardIcon(self.style().SP_DialogSaveButton)
        )
        self.save_csv_button.clicked.connect(self.save_data_to_csv)
        top_buttons_layout.addWidget(self.save_csv_button, alignment=Qt.AlignRight)

        main_layout.addLayout(top_buttons_layout)

    def create_left_panel(self, content_layout):
        """Create the left panel with video and counters."""
        left_frame = MacStyleFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(16)

        # Video controls row
        video_control_frame = MacStyleFrame()
        video_control_layout = QHBoxLayout(video_control_frame)

        # Video source selector
        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头", "视频文件"])
        video_control_layout.addWidget(QLabel("视频源:"))
        video_control_layout.addWidget(self.source_combo)

        # Resolution selector
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "1280x720", "1920x1080"])
        video_control_layout.addWidget(QLabel("分辨率:"))
        video_control_layout.addWidget(self.resolution_combo)

        left_layout.addWidget(video_control_frame)

        # Video display area
        self.video_label = QLabel("等待视频流...")
        self.video_label.setMinimumSize(640, 640)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setObjectName("videoDisplay")
        left_layout.addWidget(self.video_label)

        # Recognition info area
        info_frame = MacStyleFrame()
        info_layout = QHBoxLayout(info_frame)

        # Detection count label
        self.count_label = QLabel("识别到的鸟类数量: 0")
        self.count_label.setObjectName("statLabel")
        info_layout.addWidget(self.count_label)

        # FPS label
        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setObjectName("statLabel")
        info_layout.addWidget(self.fps_label)

        left_layout.addWidget(info_frame)

        # Attach left panel to content layout.
        content_layout.addWidget(left_frame, 2)

    def create_right_panel(self, content_layout):
        """Create the right panel with chart and controls."""
        right_frame = MacStyleFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(16)

        # Density chart container
        self.density_chart_placeholder = QLabel("数量密度分布图")
        self.density_chart_placeholder.setMinimumSize(400, 300)
        self.density_chart_placeholder.setAlignment(Qt.AlignCenter)
        self.density_chart_placeholder.setObjectName("densityPanel")
        right_layout.addWidget(self.density_chart_placeholder)

        # Control button area
        control_frame = MacStyleFrame()
        control_layout = QVBoxLayout(control_frame)
        control_layout.setSpacing(12)

        # Start/stop detection button
        self.start_stop_button = MacStyleButton("开始检测")
        self.start_stop_button.setIcon(
            self.style().standardIcon(self.style().SP_MediaPlay)
        )
        self.start_stop_button.clicked.connect(self.toggle_detection)
        control_layout.addWidget(self.start_stop_button)

        # Reserved progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        right_layout.addWidget(control_frame)

        # Attach right panel to content layout.
        content_layout.addWidget(right_frame, 1)

    def init_matplotlib_canvas(self):
        """Create and attach the Matplotlib canvas widget."""
        self.fig, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.fig)
        # Remove any previous placeholder layout.
        old_layout = self.density_chart_placeholder.layout()
        if old_layout:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
            old_layout.deleteLater()
        new_layout = QVBoxLayout(self.density_chart_placeholder)
        new_layout.addWidget(self.canvas)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(0)

    def load_config(self):
        """Load persisted configuration from config.txt."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("model="):
                            model_path = resolve_model_path(
                                line.split("=", 1)[1].strip()
                            )
                            if os.path.exists(model_path):
                                self.load_model_and_classes(model_path)
                                self.statusBar.showMessage(
                                    f"已加载模型: {os.path.basename(model_path)}"
                                )
                            else:
                                self.statusBar.showMessage("配置中指定的模型文件不存在")
                        elif line.startswith("classes="):
                            classes_str = line.split("=", 1)[1].strip()
                            if classes_str:
                                self.selected_classes = {
                                    cls for cls in classes_str.split(",") if cls
                                }
                                self.bird_detector.selected_classes = (
                                    self.selected_classes
                                )
                                # Default density classes to selected classes.
                                if (
                                    not hasattr(self, "density_classes")
                                    or not self.density_classes
                                ):
                                    self.density_classes = set(self.selected_classes)
                                    self.bird_detector.density_classes = set(
                                        self.selected_classes
                                    )
                            else:
                                self.selected_classes = set()
                                self.bird_detector.selected_classes = set()
                                self.density_classes = set()
                                self.bird_detector.density_classes = set()
                        elif line.startswith("density="):
                            density_str = line.split("=", 1)[1].strip()
                            if density_str:
                                self.density_classes = {
                                    cls for cls in density_str.split(",") if cls
                                }
                            else:
                                self.density_classes = set()
                            self.bird_detector.density_classes = set(
                                self.density_classes
                            )
            except Exception as e:
                self.statusBar.showMessage(f"读取config.txt失败: {e}")
        else:
            self.statusBar.showMessage("未找到config.txt文件，请进行设置")

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("文件")

        open_action = QAction("打开视频", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_video)
        file_menu.addAction(open_action)

        save_action = QAction("保存数据", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_data_to_csv)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View menu
        view_menu = menubar.addMenu("视图")

        fullscreen_action = QAction("全屏", self)
        fullscreen_action.setShortcut("F11")
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)

        # Help menu
        help_menu = menubar.addMenu("帮助")

        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_tool_bar(self):
        """Create the toolbar container.

        The toolbar is intentionally minimal in the current UI.
        """
        pass

    def create_tray_icon(self):
        """Create the system tray icon and context menu."""
        self.tray_icon = QSystemTrayIcon(self)
        fallback_icon = ICONS_DIR / "favicon.ico"
        # Use a style icon first, then fallback to a bundled icon file.
        icon = (
            self.style().standardIcon(self.style().SP_ComputerIcon)
            if self.style()
            else QIcon(str(fallback_icon))
        )
        if icon.isNull() and fallback_icon.exists():
            icon = QIcon(str(fallback_icon))
        self.tray_icon.setIcon(icon)

        # Build tray context menu.
        tray_menu = QMenu()
        show_action = tray_menu.addAction("显示")
        show_action.triggered.connect(self.show)
        quit_action = tray_menu.addAction("退出")
        quit_action.triggered.connect(self.close)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

    def show_settings_dialog(self):
        """Open the settings launcher dialog."""
        dlg = QDialog(self)
        dlg.setWindowTitle("设置")
        dlg.resize(300, 150)
        layout = QVBoxLayout(dlg)

        model_btn = QPushButton("模型设置")
        density_btn = QPushButton("密度图设置")

        layout.addWidget(model_btn)
        layout.addWidget(density_btn)

        def on_model():
            # Handle model selection and detectable classes.
            sdlg = SettingsDialog(
                self, self.model_path, self.all_classes, self.selected_classes
            )
            if sdlg.exec_():
                model_path, selected_classes = sdlg.get_result()
                self.load_model_and_classes(model_path)
                self.selected_classes = selected_classes
                self.bird_detector.selected_classes = self.selected_classes
                # Keep density classes aligned with selected classes.
                if not hasattr(self, "density_classes") or not self.density_classes:
                    self.density_classes = set(selected_classes)
                else:
                    self.density_classes = {
                        cls for cls in self.density_classes if cls in selected_classes
                    } or set(selected_classes)
                self.bird_detector.density_classes = set(self.density_classes)
                # Persist settings.
                save_config(model_path, selected_classes, self.density_classes)

        def on_density():
            # Handle density-chart class selection.
            # DensityDialog consumes the currently selected detection classes.
            ddialog = DensityDialog(self, density_classes=list(self.selected_classes))
            if ddialog.exec_():
                self.density_classes = ddialog.get_result()
                self.bird_detector.density_classes = self.density_classes
                save_config(
                    self.model_path, self.selected_classes, self.density_classes
                )

        model_btn.clicked.connect(on_model)
        density_btn.clicked.connect(on_density)

        dlg.exec_()

    def toggle_detection(self):
        """Toggle detection state between running and paused."""
        self.is_detecting = not self.is_detecting
        if self.is_detecting:
            self.start_stop_button.setText("停止检测")
            self.start_stop_button.setIcon(
                self.style().standardIcon(self.style().SP_MediaStop)
            )
            self.statusBar.showMessage("检测中...")
        else:
            self.start_stop_button.setText("开始检测")
            self.start_stop_button.setIcon(
                self.style().standardIcon(self.style().SP_MediaPlay)
            )
            self.statusBar.showMessage("检测已停止")
            # Reset frame-level detection state.
            if hasattr(self.bird_detector, "current_detection_info"):
                self.bird_detector.current_detection_info = []
            self.bird_detector.total_objects = 0
            self.count_label.setText("识别到的鸟类数量: 0")

    def open_video(self):
        """Open and use a local video file as input."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开视频文件", "", "视频文件 (*.mp4 *.avi *.mkv)"
        )
        if file_path:
            # Release existing capture before opening a new source.
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                self.statusBar.showMessage(
                    f"无法打开视频文件: {os.path.basename(file_path)}"
                )
                self.cap = None
            else:
                self.statusBar.showMessage(f"已打开视频: {os.path.basename(file_path)}")
                self.is_detecting = False  # Pause detection after loading a new video.
                self.start_stop_button.setText("开始检测")
                self.start_stop_button.setIcon(
                    self.style().standardIcon(self.style().SP_MediaPlay)
                )

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self,
            "关于",
            "YOLO智能识别分析系统\n版本: 1.0.0\n© 2025 版权所有:睿翼智控",
        )

    def detect_cameras(self):
        """Return IDs of available camera devices."""
        available_cameras = []
        for i in range(10):  # Probe the first ten camera indices.
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
        return available_cameras

    def show_camera_selection_dialog(self):
        """Show a dialog for selecting the active camera."""
        if not self.available_cameras:
            QMessageBox.warning(self, "警告", "未检测到可用的摄像头！")
            return False

        dialog = QDialog(self)
        dialog.setWindowTitle("选择摄像头")
        layout = QVBoxLayout(dialog)

        # Add instruction label.
        layout.addWidget(QLabel("请选择要使用的摄像头："))

        # Build camera selector.
        camera_combo = QComboBox()
        for camera_id in self.available_cameras:
            camera_combo.addItem(f"摄像头 {camera_id}", camera_id)
        layout.addWidget(camera_combo)

        # Add action buttons.
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Connect button signals.
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # Show dialog and return selected camera ID.
        if dialog.exec_() == QDialog.Accepted:
            self.selected_camera = camera_combo.currentData()
            return True
        return False

    def update_frame(self):
        """Fetch the next frame, optionally run detection, and refresh UI."""
        # Estimate real-time FPS.
        current_time = QDateTime.currentDateTime()
        elapsed = self.last_frame_time.msecsTo(current_time)
        if elapsed > 0:  # Avoid division by zero.
            current_fps = 1000 / elapsed
            self.fps = (self.fps * 0.9) + (current_fps * 0.1)  # Smooth FPS updates.
        self.last_frame_time = current_time

        if not self.is_detecting:
            # Keep previewing frames when detection is paused.
            if self.cap is None:
                if self.selected_camera is None:
                    # Ask the user to choose a camera if none is selected.
                    if not self.show_camera_selection_dialog():
                        return
                self.cap = cv2.VideoCapture(self.selected_camera)
                # Set camera resolution to 640x640.
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
                # Reduce camera buffer latency.
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not self.cap.isOpened():
                    # Show placeholder frame when camera cannot be opened.
                    black_image = np.zeros((640, 640, 3), dtype=np.uint8)
                    no_camera_icon_path = ICONS_DIR / "no_camera.png"
                    if no_camera_icon_path.exists():
                        icon = cv2.imread(
                            str(no_camera_icon_path), cv2.IMREAD_UNCHANGED
                        )
                        if icon is not None:
                            # Resize and overlay the icon on a black background.
                            icon_height, icon_width = icon.shape[:2]
                            scale = min(400 / icon_width, 300 / icon_height)
                            resized_icon = cv2.resize(
                                icon,
                                (int(icon_width * scale), int(icon_height * scale)),
                            )
                            h, w = black_image.shape[:2]
                            ih, iw = resized_icon.shape[:2]
                            x = (w - iw) // 2
                            y = (h - ih) // 2
                            if resized_icon.shape[2] == 4:
                                alpha_s = resized_icon[:, :, 3] / 255.0
                                alpha_l = 1.0 - alpha_s
                                for c in range(0, 3):
                                    black_image[y : y + ih, x : x + iw, c] = (
                                        alpha_s * resized_icon[:, :, c]
                                        + alpha_l
                                        * black_image[y : y + ih, x : x + iw, c]
                                    )
                            else:
                                black_image[y : y + ih, x : x + iw] = resized_icon[
                                    :, :, :3
                                ]
                    processed_frame = black_image
                    self.count_label.setText("识别到的鸟类数量: 0")
                    self.fps_label.setText(f"FPS: {self.fps:.1f}")
                    h, w, ch = processed_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(
                        processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
                    ).rgbSwapped()
                    pixmap = QPixmap.fromImage(qt_image)
                    self.video_label.setPixmap(
                        pixmap.scaled(
                            self.video_label.width(),
                            self.video_label.height(),
                            Qt.KeepAspectRatio,
                        )
                    )
                    return

            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    self.statusBar.showMessage("视频播放完毕或无法读取帧")
                    return

            # Render preview frame without detection overlays.
            processed_frame = frame
            self.count_label.setText("识别到的鸟类数量: 0")
            self.fps_label.setText(f"FPS: {self.fps:.1f}")
            h, w, ch = processed_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(
                processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            ).rgbSwapped()
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(
                pixmap.scaled(
                    self.video_label.width(),
                    self.video_label.height(),
                    Qt.KeepAspectRatio,
                )
            )
            return

        if self.cap is None:
            if self.selected_camera is None:
                if not self.show_camera_selection_dialog():
                    self.is_detecting = False
                    self.start_stop_button.setText("开始检测")
                    self.start_stop_button.setIcon(
                        self.style().standardIcon(self.style().SP_MediaPlay)
                    )
                    return
            self.cap = cv2.VideoCapture(self.selected_camera)
            # Set camera resolution to 640x640.
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)
            # Reduce camera buffer latency.
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.cap.isOpened():
                self.statusBar.showMessage("摄像头无法打开或不可用")
                self.is_detecting = False
                self.start_stop_button.setText("开始检测")
                self.start_stop_button.setIcon(
                    self.style().standardIcon(self.style().SP_MediaPlay)
                )
                return

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                self.statusBar.showMessage("视频播放完毕或无法读取帧")
                self.is_detecting = False
                self.start_stop_button.setText("开始检测")
                self.start_stop_button.setIcon(
                    self.style().standardIcon(self.style().SP_MediaPlay)
                )
                return

        # Run frame inference.
        processed_frame = self.bird_detector.process_frame(frame)

        # Update detection counter label.
        self.count_label.setText(
            f"识别到的鸟类数量: {self.bird_detector.total_objects}"
        )

        # Collect data for the density chart.
        now_dt = datetime.now()
        current_frame_class_counts = {cls: 0 for cls in sorted(self.density_classes)}
        if hasattr(self.bird_detector, "current_detection_info"):
            for det_info in self.bird_detector.current_detection_info:
                class_name = det_info["class"]
                if class_name in self.density_classes:
                    current_frame_class_counts[class_name] += 1

        # Write trend data at most once per second to avoid excessive I/O.
        if hasattr(self.bird_detector, "current_detection_info"):
            current_second = now_dt.strftime("%Y-%m-%d %H:%M:%S")
            if (
                self.bird_detector.current_detection_info
                and current_second != self.last_csv_save_second
            ):
                self.bird_detector.save_to_csv(
                    self.bird_detector.current_detection_info
                )
                self.last_csv_save_second = current_second

        total_objects_for_density = sum(current_frame_class_counts.values())
        self.recognition_data.append((
            now_dt,
            total_objects_for_density,
            current_frame_class_counts,
        ))
        if len(self.recognition_data) > 300:
            self.recognition_data.pop(0)

        # Refresh video display.
        h, w, ch = processed_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
        ).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.width(), self.video_label.height(), Qt.KeepAspectRatio
            )
        )

        # Refresh chart on a throttled interval.
        if (
            self.last_chart_update.msecsTo(current_time)
            >= self.chart_update_interval_ms
        ):
            self.update_density_chart()
            self.last_chart_update = current_time

    def update_density_chart(self):
        """Redraw the density chart using buffered samples."""
        if not self.recognition_data or not getattr(self, "density_classes", None):
            self.ax.clear()
            self.ax.set_title("数量密度分布（暂无数据）")
            self.canvas.draw()
            return

        # Build per-class time series.
        from collections import defaultdict

        class_time_count = defaultdict(list)
        timestamps = [item[0] for item in self.recognition_data]
        plot_classes = sorted(self.density_classes)
        # Append values for each class at each timestamp.
        for _, _, frame_classes in self.recognition_data:
            for cls in plot_classes:
                class_time_count[cls].append(frame_classes.get(cls, 0))

        self.ax.clear()
        # Handle colormap retrieval for newer Matplotlib versions.
        if hasattr(matplotlib, "colormaps"):
            # Only allocate colors for classes with non-zero history.
            valid_classes = [cls for cls in plot_classes if any(class_time_count[cls])]
            if not valid_classes:
                self.ax.set_title("数量密度分布（暂无数据）")
                self.canvas.draw()
                return
            color_map = matplotlib.colormaps.get_cmap("tab10").resampled(
                max(1, len(valid_classes))
            )
            for i, cls in enumerate(valid_classes):
                y = class_time_count[cls]
                color = color_map(i)
                self.ax.plot(
                    timestamps,
                    y,
                    label=cls,
                    linewidth=2.5,
                    marker="o",
                    markersize=7,
                    color=color,
                )
        else:
            import matplotlib.cm as cm

            # Only allocate colors for classes with non-zero history.
            valid_classes = [cls for cls in plot_classes if any(class_time_count[cls])]
            if not valid_classes:
                self.ax.set_title("数量密度分布（暂无数据）")
                self.canvas.draw()
                return
            color_map = cm.get_cmap("tab10", max(1, len(valid_classes)))
            for i, cls in enumerate(valid_classes):
                y = class_time_count[cls]
                color = (
                    color_map(i)
                    if hasattr(color_map, "__call__")
                    else color_map.colors[i]
                )
                self.ax.plot(
                    timestamps,
                    y,
                    label=cls,
                    linewidth=2.5,
                    marker="o",
                    markersize=7,
                    color=color,
                )

        self.ax.set_xlabel("时间", fontsize=12)
        self.ax.set_ylabel("数量", fontsize=12)
        self.ax.set_title("数量密度分布", fontsize=14, fontweight="bold")
        self.ax.grid(True, linestyle="--", alpha=0.4)
        locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
        formatter = mdates.ConciseDateFormatter(locator)
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)
        self.fig.autofmt_xdate(rotation=30)
        self.ax.legend(
            fontsize=12, loc="upper left", frameon=True, fancybox=True, shadow=True
        )
        self.canvas.draw()

    def save_data_to_csv(self):
        """Save the current frame detections to a CSV file."""
        if (
            not self.bird_detector
            or not hasattr(self.bird_detector, "current_detection_info")
            or not self.bird_detector.current_detection_info
        ):
            self.statusBar.showMessage("没有检测数据可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据", "", "CSV 文件 (*.csv)"
        )
        if file_path:
            try:
                # Export all detections from the current frame.
                # Write header row.
                with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["时间戳", "类别", "总数量"])
                    # Write row data for each detected object.
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    total_objects = len(self.bird_detector.current_detection_info)
                    for info in self.bird_detector.current_detection_info:
                        writer.writerow([timestamp, info["class"], total_objects])
                self.statusBar.showMessage(f"数据已保存到 {file_path}")
            except Exception as e:
                self.statusBar.showMessage(f"保存文件失败: {e}")

    def closeEvent(self, event):
        """Handle graceful shutdown and optional trend plotting."""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Release camera resources.
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.timer.stop()
            cv2.destroyAllWindows()
            # Generate trend chart from saved CSV data when possible.
            try:
                # Use the detector helper to generate the trend chart.
                if hasattr(self, "bird_detector") and self.bird_detector:
                    self.bird_detector.plot_trends()
            except Exception as e:
                print(f"生成趋势图时出错: {e}")
            event.accept()
        else:
            event.ignore()

    def load_model_and_classes(self, model_path):
        """Load a model and synchronize class selections."""
        # Proactively release any previous model instance.
        if hasattr(self, "bird_detector") and self.bird_detector is not None:
            del self.bird_detector
            gc.collect()
        try:
            self.model_path = resolve_model_path(model_path)
            self.bird_detector = ObjectDetector(self.model_path)
            self.all_classes = list(self.bird_detector.model.names.values())
            # Keep selected and density classes valid for the new model.
            if not hasattr(self, "selected_classes") or not self.selected_classes:
                self.selected_classes = set(self.all_classes)
            else:
                self.selected_classes = {
                    cls for cls in self.selected_classes if cls in self.all_classes
                } or set(self.all_classes)
            if not hasattr(self, "density_classes") or not self.density_classes:
                self.density_classes = set(self.selected_classes)
            else:
                self.density_classes = {
                    cls for cls in self.density_classes if cls in self.all_classes
                } or set(self.selected_classes)

            self.bird_detector.selected_classes = self.selected_classes
            self.bird_detector.density_classes = self.density_classes

            self.statusBar.showMessage(
                f"成功加载模型: {os.path.basename(self.model_path)}"
            )

        except Exception as e:
            self.statusBar.showMessage(f"加载模型失败: {e}")
            # Reset state when model loading fails.
            self.model_path = None
            self.all_classes = []
            self.selected_classes = set()
            self.density_classes = set()
            self.bird_detector = None  # Clear detector object.
