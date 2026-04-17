"""Layout-building class for the main window."""

import matplotlib
matplotlib.use("Qt5Agg", force=True)

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.components import MacStyleButton, MacStyleFrame

class MainWindowUI:
    """Class to construct and hold all UI widgets for the main window."""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.central_widget = QWidget()
        main_window.setCentralWidget(self.central_widget)
        
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setSpacing(18)
        self.main_layout.setContentsMargins(24, 24, 24, 24)
        
        self.setup_top_buttons()
        self.setup_content_panels()

    def setup_top_buttons(self):
        """Create the top action row."""
        top_buttons_layout = QHBoxLayout()
        top_buttons_layout.setSpacing(16)
        top_buttons_layout.setContentsMargins(0, 0, 0, 8)

        self.settings_btn = MacStyleButton("设置")
        self.settings_btn.setFixedWidth(100)
        top_buttons_layout.addWidget(self.settings_btn, alignment=Qt.AlignLeft)

        top_buttons_layout.addStretch()

        self.save_csv_button = MacStyleButton("保存数据为 CSV")
        top_buttons_layout.addWidget(self.save_csv_button, alignment=Qt.AlignRight)

        self.main_layout.addLayout(top_buttons_layout)

    def setup_content_panels(self):
        """Create left (video) and right (charts/control) panels."""
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # ================= LEFT PANEL =================
        left_frame = MacStyleFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setSpacing(20)
        left_layout.setContentsMargins(20, 20, 20, 20)

        video_control_frame = MacStyleFrame()
        video_control_layout = QHBoxLayout(video_control_frame)
        video_control_layout.setContentsMargins(16, 12, 16, 12)
        video_control_layout.setSpacing(16)

        self.source_combo = QComboBox()
        self.source_combo.addItems(["摄像头", "视频文件"])
        video_control_layout.addWidget(QLabel("视频源:"))
        video_control_layout.addWidget(self.source_combo)

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["640x480", "1280x720", "1920x1080"])
        video_control_layout.addWidget(QLabel("分辨率:"))
        video_control_layout.addWidget(self.resolution_combo)

        video_control_layout.addStretch()
        left_layout.addWidget(video_control_frame)

        self.video_label = QLabel("等待视频流...")
        self.video_label.setMinimumSize(480, 480)
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setObjectName("videoDisplay")
        left_layout.addWidget(self.video_label)

        info_frame = MacStyleFrame()
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(20)

        self.count_label = QLabel("识别到的鸟类数量: 0")
        self.count_label.setObjectName("statLabel")
        info_layout.addWidget(self.count_label)

        self.fps_label = QLabel("FPS: 0")
        self.fps_label.setObjectName("statLabel")
        info_layout.addWidget(self.fps_label)

        info_layout.addStretch()
        left_layout.addWidget(info_frame)

        content_layout.addWidget(left_frame, 2)

        # ================= RIGHT PANEL =================
        right_frame = MacStyleFrame()
        right_layout = QVBoxLayout(right_frame)
        right_layout.setSpacing(20)
        right_layout.setContentsMargins(20, 20, 20, 20)

        self.density_chart_placeholder = QLabel("数量密度分布图")
        self.density_chart_placeholder.setMinimumSize(400, 300)
        self.density_chart_placeholder.setMaximumHeight(380)
        self.density_chart_placeholder.setAlignment(Qt.AlignCenter)
        self.density_chart_placeholder.setObjectName("densityPanel")
        right_layout.addWidget(self.density_chart_placeholder)

        log_frame = MacStyleFrame()
        log_layout = QVBoxLayout(log_frame)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_layout.setSpacing(8)

        log_title = QLabel("实时状态跟踪")
        log_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #F8FAFC;")
        log_layout.addWidget(log_title)

        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        self.log_text_edit.setPlaceholderText("系统空闲，等待视频流输入...")
        self.log_text_edit.setObjectName("logTextEdit")
        log_layout.addWidget(self.log_text_edit)

        right_layout.addWidget(log_frame, 1)

        control_frame = MacStyleFrame()
        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(16, 16, 16, 16)
        control_layout.setSpacing(12)

        self.start_stop_button = MacStyleButton("开始检测")
        self.start_stop_button.setMinimumHeight(44)
        control_layout.addWidget(self.start_stop_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        control_layout.addWidget(self.progress_bar)

        right_layout.addWidget(control_frame)
        content_layout.addWidget(right_frame, 1)
        
        self.main_layout.addLayout(content_layout, 1)
        
        # Init specific embedded plots
        self.init_matplotlib_canvas()

    def init_matplotlib_canvas(self):
        """Create and attach Matplotlib canvas widget to the placeholder."""
        self.fig, self.ax = plt.subplots(tight_layout=True)
        self.canvas = FigureCanvas(self.fig)

        self.fig.patch.set_facecolor("#171A21")
        self.ax.set_facecolor("#171A21")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_color("#292D3E")
        self.ax.spines["bottom"].set_color("#292D3E")
        self.ax.tick_params(colors="#64748B")
        self.ax.set_title(
            "数量密度分布（暂无数据）",
            fontsize=15,
            fontweight="600",
            color="#F8FAFC",
            pad=12,
        )

        new_layout = QVBoxLayout(self.density_chart_placeholder)
        new_layout.addWidget(self.canvas)
        new_layout.setContentsMargins(0, 0, 0, 0)
        new_layout.setSpacing(0)
