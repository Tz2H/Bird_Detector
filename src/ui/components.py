"""
Reusable UI components for the Bird Detector interface.

Author: Tz2H
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QPushButton, QFrame, QGraphicsDropShadowEffect


class MacStyleButton(QPushButton):
    """Styled push button with a macOS-like appearance."""

    def __init__(self, text, parent=None):
        """Initialize the styled button."""
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #3B82F6;
                color: #FFFFFF;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-family: "Inter", "Microsoft YaHei UI";
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2563EB;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #1F222A;
                color: #4B5563;
            }
        """)

        # Optional subtle shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 40))
        self.setGraphicsEffect(shadow)


class MacStyleFrame(QFrame):
    """Styled frame container with a macOS-like appearance."""

    def __init__(self, parent=None):
        """Initialize the styled frame."""
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #171A21;
                border-radius: 12px;
                border: 1px solid #292D3E;
            }
        """)

        # Ambient shadow for floating card effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 60))
        self.setGraphicsEffect(shadow)
