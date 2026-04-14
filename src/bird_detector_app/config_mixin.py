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

from bird_detector_app.paths import CONFIG_FILE, ICONS_DIR
from ui.dialogs import DensityDialog, SettingsDialog
from utils.config_manager import resolve_model_path, save_config


class ConfigMixin:
    """Mixin that handles settings, menus, and tray interactions."""

    def load_config(self):
        """Load persisted configuration from config.txt."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                    for line in file:
                        line = line.strip()
                        if line.startswith("model="):
                            model_path = resolve_model_path(
                                line.split("=", 1)[1].strip()
                            )
                            if os.path.exists(model_path):
                                self.load_model_and_classes(model_path)
                                self.statusBar.showMessage(
                                    f"已加载模型: {os.path.basename(model_path)}"
                                )
                            else:
                                self.statusBar.showMessage("配置中指定的模型文件不存在")
                        elif line.startswith("classes="):
                            classes_str = line.split("=", 1)[1].strip()
                            if classes_str:
                                self.selected_classes = {
                                    cls for cls in classes_str.split(",") if cls
                                }
                                self.bird_detector.selected_classes = (
                                    self.selected_classes
                                )
                                # Default density classes to selected classes.
                                if (
                                    not hasattr(self, "density_classes")
                                    or not self.density_classes
                                ):
                                    self.density_classes = set(self.selected_classes)
                                    self.bird_detector.density_classes = set(
                                        self.selected_classes
                                    )
                            else:
                                self.selected_classes = set()
                                self.bird_detector.selected_classes = set()
                                self.density_classes = set()
                                self.bird_detector.density_classes = set()
                        elif line.startswith("density="):
                            density_str = line.split("=", 1)[1].strip()
                            if density_str:
                                self.density_classes = {
                                    cls for cls in density_str.split(",") if cls
                                }
                            else:
                                self.density_classes = set()
                            self.bird_detector.density_classes = set(
                                self.density_classes
                            )
            except Exception as error:
                self.statusBar.showMessage(f"读取config.txt失败: {error}")
        else:
            self.statusBar.showMessage("未找到config.txt文件，请进行设置")

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
                self.selected_classes = selected_classes
                self.bird_detector.selected_classes = self.selected_classes

                # Keep density classes aligned with selected classes.
                if not hasattr(self, "density_classes") or not self.density_classes:
                    self.density_classes = set(selected_classes)
                else:
                    self.density_classes = {
                        cls for cls in self.density_classes if cls in selected_classes
                    } or set(selected_classes)
                self.bird_detector.density_classes = set(self.density_classes)

                # Persist settings.
                save_config(model_path, selected_classes, self.density_classes)

        def on_density():
            # Handle density-chart class selection.
            # DensityDialog consumes the currently selected detection classes.
            density_dialog = DensityDialog(
                self, density_classes=list(self.selected_classes)
            )
            if density_dialog.exec_():
                self.density_classes = density_dialog.get_result()
                self.bird_detector.density_classes = self.density_classes
                save_config(
                    self.model_path, self.selected_classes, self.density_classes
                )

        model_btn.clicked.connect(on_model)
        density_btn.clicked.connect(on_density)

        dialog.exec_()
