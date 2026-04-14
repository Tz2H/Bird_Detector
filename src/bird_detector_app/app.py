"""
Main GUI application for Bird Detector.

Author: Tz2H
"""

from PyQt5.QtCore import QDateTime, QTimer
from PyQt5.QtWidgets import QHBoxLayout, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from bird_detector_app.config_mixin import ConfigMixin
from bird_detector_app.detector import ObjectDetector
from bird_detector_app.layout_mixin import LayoutMixin
from bird_detector_app.paths import DEFAULT_MODEL_PATH
from bird_detector_app.runtime_mixin import RuntimeMixin
from bird_detector_app.style_mixin import StyleMixin, configure_matplotlib_fonts


class YoloVisualizationApp(
    StyleMixin,
    LayoutMixin,
    ConfigMixin,
    RuntimeMixin,
    QMainWindow,
):
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

        # Build the menu bar and toolbar.
        self.create_menu_bar()
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
        self.create_left_panel(content_layout)
        self.create_right_panel(content_layout)
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
