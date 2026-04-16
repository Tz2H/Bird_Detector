"""
Application entry point for the Bird Detector GUI.

Author: Tz2H
"""

import sys

from PyQt5.QtWidgets import QApplication

from bird_detector_app.app import YoloVisualizationApp
from utils.config_manager import load_initial_config


def main():
    """Run the desktop application."""
    # Load startup configuration from config.txt when available.
    initial_config = load_initial_config()

    app = QApplication(sys.argv)

    # Create the main window after QApplication is initialized.
    main_window = YoloVisualizationApp(initial_config=initial_config)

    main_window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
