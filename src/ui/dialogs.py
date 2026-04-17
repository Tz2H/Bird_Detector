"""
Dialog components for density configuration.

Author: Tz2H
"""

from PyQt5.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class DensityDialog(QDialog):
    """Dialog for configuring classes shown in density charts."""

    def __init__(self, parent=None, available_classes=None, selected_classes=None):
        """Initialize the density configuration dialog."""
        super().__init__(parent)
        self.setWindowTitle("密度图设置")
        self.resize(400, 600)
        self.available_classes = list(available_classes or [])
        self.selected_classes = set(selected_classes or self.available_classes)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Scrollable class checkbox list
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.class_widget = QWidget()
        self.class_layout = QVBoxLayout(self.class_widget)
        self.density_checkboxes = []
        self.refresh_class_checkboxes()
        self.scroll.setWidget(self.class_widget)
        layout.addWidget(QLabel("请选择需要显示的类别："))
        layout.addWidget(self.scroll)

        # Confirmation buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        ok_btn = QPushButton("确认")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def refresh_class_checkboxes(self):
        """Rebuild density class checkboxes."""
        # Clear existing checkbox widgets.
        for cb in self.density_checkboxes:
            self.class_layout.removeWidget(cb)
            cb.deleteLater()
        self.density_checkboxes = []
        # Build new checkbox widgets.
        for cls in self.available_classes:
            cb = QCheckBox(cls)
            cb.setChecked(cls in self.selected_classes)
            cb.stateChanged.connect(self.update_density_classes)
            self.class_layout.addWidget(cb)
            self.density_checkboxes.append(cb)

    def update_density_classes(self):
        """Update density classes from checkbox state."""
        self.selected_classes = set()
        for cb in self.density_checkboxes:
            if cb.isChecked():
                self.selected_classes.add(cb.text())

    def get_result(self):
        """Return selected density classes."""
        return self.selected_classes
