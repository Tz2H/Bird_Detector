"""Styling helpers for the Bird Detector main window."""

import matplotlib

def configure_matplotlib_fonts():
    """Configure a robust CJK font fallback list for Matplotlib."""
    preferred_fonts = [
        "PingFang SC",
        "Hiragino Sans GB",
        "Heiti SC",
        "Microsoft YaHei UI",
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

def apply_application_style(window):
    """Apply stylesheet rules for the whole application."""
    window.setStyleSheet("""
        QMainWindow {
            background-color: #0B0D11;
        }
        QWidget {
            background-color: transparent;
            color: #F1F5F9;
            font-family: "Inter", "SF Pro Display", "Segoe UI", "Microsoft YaHei UI";
            font-size: 13px;
        }
        QLabel {
            color: #E2E8F0;
            font-size: 13px;
            font-weight: 500;
        }
        QMenuBar {
            background-color: #0F1218;
            color: #CBD5E1;
            border-bottom: 1px solid #1E2330;
            padding: 4px;
        }
        QMenuBar::item {
            padding: 6px 10px;
            border-radius: 6px;
            background: transparent;
        }
        QMenuBar::item:selected {
            background-color: #1E2330;
            color: #FFFFFF;
        }
        QMenu {
            background-color: #171A21;
            border: 1px solid #292D3E;
            border-radius: 8px;
            padding: 6px;
            margin: 4px;
        }
        QMenu::item {
            padding: 6px 24px 6px 12px;
            border-radius: 6px;
        }
        QMenu::item:selected {
            background-color: #2D3344;
            color: #FFFFFF;
        }
        QStatusBar {
            background-color: #0F1218;
            color: #94A3B8;
            border-top: 1px solid #1E2330;
        }
        QComboBox {
            background-color: #1E2330;
            color: #F1F5F9;
            border: 1px solid #292D3E;
            border-radius: 6px;
            padding: 6px 12px;
            min-height: 28px;
        }
        QComboBox:hover {
            background-color: #2D3344;
            border: 1px solid #3B82F6;
        }
        QComboBox::drop-down {
            border: none;
            width: 24px;
        }
        QComboBox QAbstractItemView {
            background-color: #171A21;
            border: 1px solid #292D3E;
            border-radius: 6px;
            selection-background-color: #2D3344;
        }
        QProgressBar {
            background-color: #1E2330;
            border: none;
            border-radius: 4px;
            text-align: center;
            color: #F1F5F9;
            height: 8px;
        }
        QProgressBar::chunk {
            background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #3B82F6, stop:1 #60A5FA);
            border-radius: 4px;
        }
        QToolBar {
            background-color: #0B0D11;
            border: none;
            spacing: 8px;
            padding: 4px;
        }
        QToolBar::separator {
            width: 1px;
            background-color: #1E2330;
            margin: 6px;
        }
        QDialog {
            background-color: #0F1218;
        }
        QScrollArea {
            background-color: transparent;
            border: 1px solid #292D3E;
            border-radius: 8px;
        }
        QScrollArea QWidget {
            background-color: transparent;
        }
        QScrollBar:vertical {
            border: none;
            background-color: transparent;
            width: 10px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #2D3344;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #475569;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QCheckBox {
            spacing: 12px;
            color: #CBD5E1;
            font-size: 13px;
        }
        QCheckBox::indicator {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid #334155;
            background: #1E293B;
        }
        QCheckBox::indicator:hover {
            border: 1px solid #3B82F6;
        }
        QCheckBox::indicator:checked {
            background: #3B82F6;
            border: 1px solid #3B82F6;
        }
        QTextEdit {
            background-color: #1E2330;
            color: #CBD5E1;
            border: 1px solid #292D3E;
            border-radius: 8px;
            padding: 10px;
            font-family: "Inter", "SF Pro Display", "Microsoft YaHei UI";
            font-size: 13px;
            line-height: 1.5;
        }
        QLabel#videoDisplay, QLabel#heatmapPanel {
            background-color: #101217;
            border: 1px solid #1E2330;
            border-radius: 12px;
            padding: 12px;
            color: #64748B;
            font-size: 14px;
            font-weight: 500;
        }
        QLabel#statLabel {
            font-size: 15px;
            font-weight: 700;
            color: #F8FAFC;
            padding: 4px 8px;
            background-color: #1E2330;
            border-radius: 6px;
        }
    """)
