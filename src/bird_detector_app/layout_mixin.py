"""Layout-building methods for the main window."""

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
)

from ui.components import MacStyleButton, MacStyleFrame


class LayoutMixin:
    """Mixin that creates window layout sections."""

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
