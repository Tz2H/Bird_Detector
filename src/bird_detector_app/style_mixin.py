"""Styling helpers for the Bird Detector main window."""

import matplotlib


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


class StyleMixin:
    """Mixin that applies the application stylesheet."""

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
