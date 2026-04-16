"""Configuration, menu, and tray behaviors for the main window."""

import os

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
)

from bird_detector_app.paths import ICONS_DIR
from ui.dialogs import DensityDialog, SettingsDialog
from utils.config_manager import load_initial_config, save_config


class ConfigMixin:
    """Mixin that handles settings, menus, and tray interactions."""

    def load_config(self, config_data=None):
        """Load persisted or injected startup configuration."""
        try:
            config = config_data or load_initial_config()
            self.load_model_and_classes(config.get("model_path"))

            detector = getattr(self, "bird_detector", None)
            if detector is None:
                self.statusBar.showMessage("模型加载失败，请在设置中重新选择模型")
                return

            configured_selected = set(config.get("selected_classes") or [])
            if configured_selected:
                selected_classes = {
                    cls for cls in configured_selected if cls in self.all_classes
                } or set(self.all_classes)
            else:
                selected_classes = set(self.all_classes)

            configured_density = set(config.get("density_classes") or [])
            if configured_density:
                density_classes = {
                    cls for cls in configured_density if cls in selected_classes
                } or set(selected_classes)
            else:
                density_classes = set(selected_classes)

            self.selected_classes = selected_classes
            self.density_classes = density_classes
            detector.selected_classes = set(self.selected_classes)
            detector.density_classes = set(self.density_classes)

            model_name = os.path.basename(self.model_path) if self.model_path else "默认模型"
            self.statusBar.showMessage(f"已加载配置: {model_name}")
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

    def show_settings_dialog(self):
        """Open the settings launcher dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.resize(300, 150)
        layout = QVBoxLayout(dialog)

        model_btn = QPushButton("模型设置")
        density_btn = QPushButton("密度图设置")

        layout.addWidget(model_btn)
        layout.addWidget(density_btn)

        def on_model():
            # Handle model selection and detectable classes.
            settings_dialog = SettingsDialog(
                self, self.model_path, self.all_classes, self.selected_classes
            )
            if settings_dialog.exec_():
                model_path, selected_classes = settings_dialog.get_result()
                self.load_model_and_classes(model_path)
                if not getattr(self, "bird_detector", None):
                    return

                self.selected_classes = {
                    cls for cls in selected_classes if cls in self.all_classes
                } or set(self.all_classes)
                self.bird_detector.selected_classes = set(self.selected_classes)

                # Keep density classes aligned with selected classes.
                if not hasattr(self, "density_classes") or not self.density_classes:
                    self.density_classes = set(self.selected_classes)
                else:
                    self.density_classes = {
                        cls
                        for cls in self.density_classes
                        if cls in self.selected_classes
                    } or set(self.selected_classes)
                self.bird_detector.density_classes = set(self.density_classes)

                # Persist settings.
                save_config(
                    self.model_path,
                    self.selected_classes,
                    self.density_classes,
                )

        def on_density():
            # Handle density-chart class selection.
            available_classes = sorted(self.selected_classes)
            initial_density_classes = {
                cls for cls in self.density_classes if cls in self.selected_classes
            }
            if not initial_density_classes:
                initial_density_classes = set(available_classes)

            density_dialog = DensityDialog(
                self,
                available_classes=available_classes,
                selected_classes=initial_density_classes,
            )
            if density_dialog.exec_():
                if not getattr(self, "bird_detector", None):
                    return
                self.density_classes = density_dialog.get_result()
                self.bird_detector.density_classes = set(self.density_classes)
                save_config(
                    self.model_path, self.selected_classes, self.density_classes
                )

        model_btn.clicked.connect(on_model)
        density_btn.clicked.connect(on_density)

        dialog.exec_()
