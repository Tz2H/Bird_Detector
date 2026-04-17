"""Configuration, menu, and tray behaviors for the main window."""

import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QMenu,
    QSystemTrayIcon,
)

from bird_detector_app.paths import ICONS_DIR
from utils.config_manager import load_initial_config


class ConfigMixin:
    """Mixin that handles settings, menus, and tray interactions."""

    def load_config(self, config_data=None):
        """Load persisted or injected startup configuration."""
        try:
            config = config_data or load_initial_config()
            self.load_model_and_classes(config.get("model_path"))

            detector = getattr(self, "bird_detector", None)
            if detector is None:
                self.statusBar.showMessage("模型加载失败，请检查模型文件配置")
                return

            bird_class = next(
                (cls for cls in self.all_classes if str(cls).lower() == "bird"),
                None,
            )
            selected_classes = {bird_class} if bird_class else set()
            heatmap_classes = set(selected_classes)

            self.selected_classes = selected_classes
            self.heatmap_classes = heatmap_classes
            detector.selected_classes = set(self.selected_classes)
            detector.heatmap_classes = set(self.heatmap_classes)

            model_name = (
                os.path.basename(self.model_path) if self.model_path else "默认模型"
            )
            if selected_classes:
                self.statusBar.showMessage(f"已加载配置: {model_name}（仅检测 bird）")
            else:
                self.statusBar.showMessage(
                    f"已加载配置: {model_name}（模型不含 bird 类）"
                )
        except Exception as error:
            self.statusBar.showMessage(f"读取配置失败: {error}")

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
