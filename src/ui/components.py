"""
Reusable UI components for the Bird Detector interface.
Author: Tz2H
"""

from PyQt5.QtWidgets import QPushButton, QFrame


class MacStyleButton(QPushButton):
    """Styled push button with a macOS-like appearance."""

    def __init__(self, text, parent=None):
        """Initialize the styled button."""
        super().__init__(text, parent)
        self.setStyleSheet("""
            QPushButton {
                background-color: #4F6EF7;
                color: #F5F7FA;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5B7BFF;
            }
            QPushButton:pressed {
                background-color: #3F5FE0;
            }
            QPushButton:disabled {
                background-color: #2C313A;
                color: #8C96A6;
            }
        """)


class MacStyleFrame(QFrame):
    """Styled frame container with a macOS-like appearance."""

    def __init__(self, parent=None):
        """Initialize the styled frame."""
        super().__init__(parent)
        self.setStyleSheet("""
            QFrame {
                background-color: #1F2227;
                border-radius: 12px;
                border: 1px solid #2B2F36;
            }
        """)
