"""Runtime behaviors for detection, charting, and I/O."""

import csv
import gc
import os
from datetime import datetime

import cv2
import matplotlib
import matplotlib.dates as mdates
import numpy as np
from PyQt5.QtCore import QDateTime, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from bird_detector_app.detector import ObjectDetector
from bird_detector_app.paths import ICONS_DIR
from utils.config_manager import resolve_model_path


class RuntimeMixin:
    """Mixin that handles runtime user interactions and frame processing."""

    def toggle_detection(self):
        """Toggle detection state between running and paused."""
        self.is_detecting = not self.is_detecting
        if self.is_detecting:
            self.start_stop_button.setText("停止检测")
            self.start_stop_button.setIcon(
                self.style().standardIcon(self.style().SP_MediaStop)
            )
            self.statusBar.showMessage("检测中...")
        else:
            self.start_stop_button.setText("开始检测")
            self.start_stop_button.setIcon(
                self.style().standardIcon(self.style().SP_MediaPlay)
            )
            self.statusBar.showMessage("检测已停止")

            # Reset frame-level detection state.
            if hasattr(self.bird_detector, "current_detection_info"):
                self.bird_detector.current_detection_info = []
            self.bird_detector.total_objects = 0
            self.count_label.setText("识别到的鸟类数量: 0")

    def open_video(self):
        """Open and use a local video file as input."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开视频文件", "", "视频文件 (*.mp4 *.avi *.mkv)"
        )
        if file_path:
            # Release existing capture before opening a new source.
            if self.cap and self.cap.isOpened():
                self.cap.release()

            self.cap = cv2.VideoCapture(file_path)
            if not self.cap.isOpened():
                self.statusBar.showMessage(
                    f"无法打开视频文件: {os.path.basename(file_path)}"
                )
                self.cap = None
            else:
                self.statusBar.showMessage(f"已打开视频: {os.path.basename(file_path)}")
                self.is_detecting = False  # Pause detection after loading a new video.
                self.start_stop_button.setText("开始检测")
                self.start_stop_button.setIcon(
                    self.style().standardIcon(self.style().SP_MediaPlay)
                )

    def toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def show_about(self):
        """Show the About dialog."""
        QMessageBox.about(
            self,
            "关于",
            "YOLO智能识别分析系统\n版本: 1.0.0\n© 2025 版权所有:睿翼智控",
        )

    def detect_cameras(self):
        """Return IDs of available camera devices."""
        available_cameras = []
        for i in range(10):  # Probe the first ten camera indices.
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, _ = cap.read()
                if ret:
                    available_cameras.append(i)
                cap.release()
        return available_cameras

    def show_camera_selection_dialog(self):
        """Show a dialog for selecting the active camera."""
        if not self.available_cameras:
            QMessageBox.warning(self, "警告", "未检测到可用的摄像头！")
            return False

        dialog = QDialog(self)
        dialog.setWindowTitle("选择摄像头")
        layout = QVBoxLayout(dialog)

        # Add instruction label.
        layout.addWidget(QLabel("请选择要使用的摄像头："))

        # Build camera selector.
        camera_combo = QComboBox()
        for camera_id in self.available_cameras:
            camera_combo.addItem(f"摄像头 {camera_id}", camera_id)
        layout.addWidget(camera_combo)

        # Add action buttons.
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        # Connect button signals.
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # Show dialog and return selected camera ID.
        if dialog.exec_() == QDialog.Accepted:
            self.selected_camera = camera_combo.currentData()
            return True
        return False

    def update_frame(self):
        """Fetch the next frame, optionally run detection, and refresh UI."""
        # Estimate real-time FPS.
        current_time = QDateTime.currentDateTime()
        elapsed = self.last_frame_time.msecsTo(current_time)
        if elapsed > 0:  # Avoid division by zero.
            current_fps = 1000 / elapsed
            self.fps = (self.fps * 0.9) + (current_fps * 0.1)  # Smooth FPS updates.
        self.last_frame_time = current_time

        if not self.is_detecting:
            # Keep previewing frames when detection is paused.
            if self.cap is None:
                if self.selected_camera is None:
                    # Ask the user to choose a camera if none is selected.
                    if not self.show_camera_selection_dialog():
                        return
                self.cap = cv2.VideoCapture(self.selected_camera)

                # Set camera resolution to 640x640.
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

                # Reduce camera buffer latency.
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                if not self.cap.isOpened():
                    # Show placeholder frame when camera cannot be opened.
                    black_image = np.zeros((640, 640, 3), dtype=np.uint8)
                    no_camera_icon_path = ICONS_DIR / "no_camera.png"
                    if no_camera_icon_path.exists():
                        icon = cv2.imread(
                            str(no_camera_icon_path), cv2.IMREAD_UNCHANGED
                        )
                        if icon is not None:
                            # Resize and overlay the icon on a black background.
                            icon_height, icon_width = icon.shape[:2]
                            scale = min(400 / icon_width, 300 / icon_height)
                            resized_icon = cv2.resize(
                                icon,
                                (int(icon_width * scale), int(icon_height * scale)),
                            )
                            h, w = black_image.shape[:2]
                            ih, iw = resized_icon.shape[:2]
                            x = (w - iw) // 2
                            y = (h - ih) // 2
                            if resized_icon.shape[2] == 4:
                                alpha_s = resized_icon[:, :, 3] / 255.0
                                alpha_l = 1.0 - alpha_s
                                for c in range(0, 3):
                                    black_image[y : y + ih, x : x + iw, c] = (
                                        alpha_s * resized_icon[:, :, c]
                                        + alpha_l
                                        * black_image[y : y + ih, x : x + iw, c]
                                    )
                            else:
                                black_image[y : y + ih, x : x + iw] = resized_icon[
                                    :, :, :3
                                ]
                    processed_frame = black_image
                    self.count_label.setText("识别到的鸟类数量: 0")
                    self.fps_label.setText(f"FPS: {self.fps:.1f}")
                    h, w, ch = processed_frame.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(
                        processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
                    ).rgbSwapped()
                    pixmap = QPixmap.fromImage(qt_image)
                    self.video_label.setPixmap(
                        pixmap.scaled(
                            self.video_label.width(),
                            self.video_label.height(),
                            Qt.KeepAspectRatio,
                        )
                    )
                    return

            ret, frame = self.cap.read()
            if not ret:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    self.statusBar.showMessage("视频播放完毕或无法读取帧")
                    return

            # Render preview frame without detection overlays.
            processed_frame = frame
            self.count_label.setText("识别到的鸟类数量: 0")
            self.fps_label.setText(f"FPS: {self.fps:.1f}")
            h, w, ch = processed_frame.shape
            bytes_per_line = ch * w
            qt_image = QImage(
                processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
            ).rgbSwapped()
            pixmap = QPixmap.fromImage(qt_image)
            self.video_label.setPixmap(
                pixmap.scaled(
                    self.video_label.width(),
                    self.video_label.height(),
                    Qt.KeepAspectRatio,
                )
            )
            return

        if self.cap is None:
            if self.selected_camera is None:
                if not self.show_camera_selection_dialog():
                    self.is_detecting = False
                    self.start_stop_button.setText("开始检测")
                    self.start_stop_button.setIcon(
                        self.style().standardIcon(self.style().SP_MediaPlay)
                    )
                    return
            self.cap = cv2.VideoCapture(self.selected_camera)

            # Set camera resolution to 640x640.
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

            # Reduce camera buffer latency.
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.cap.isOpened():
                self.statusBar.showMessage("摄像头无法打开或不可用")
                self.is_detecting = False
                self.start_stop_button.setText("开始检测")
                self.start_stop_button.setIcon(
                    self.style().standardIcon(self.style().SP_MediaPlay)
                )
                return

        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                self.statusBar.showMessage("视频播放完毕或无法读取帧")
                self.is_detecting = False
                self.start_stop_button.setText("开始检测")
                self.start_stop_button.setIcon(
                    self.style().standardIcon(self.style().SP_MediaPlay)
                )
                return

        # Run frame inference.
        processed_frame = self.bird_detector.process_frame(frame)

        # Update detection counter label.
        self.count_label.setText(
            f"识别到的鸟类数量: {self.bird_detector.total_objects}"
        )

        # Collect data for the density chart.
        now_dt = datetime.now()
        current_frame_class_counts = {cls: 0 for cls in sorted(self.density_classes)}
        if hasattr(self.bird_detector, "current_detection_info"):
            for det_info in self.bird_detector.current_detection_info:
                class_name = det_info["class"]
                if class_name in self.density_classes:
                    current_frame_class_counts[class_name] += 1

        # Write trend data at most once per second to avoid excessive I/O.
        if hasattr(self.bird_detector, "current_detection_info"):
            current_second = now_dt.strftime("%Y-%m-%d %H:%M:%S")
            if (
                self.bird_detector.current_detection_info
                and current_second != self.last_csv_save_second
            ):
                self.bird_detector.save_to_csv(
                    self.bird_detector.current_detection_info
                )
                self.last_csv_save_second = current_second

        total_objects_for_density = sum(current_frame_class_counts.values())
        self.recognition_data.append((
            now_dt,
            total_objects_for_density,
            current_frame_class_counts,
        ))
        if len(self.recognition_data) > 300:
            self.recognition_data.pop(0)

        # Refresh video display.
        h, w, ch = processed_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            processed_frame.data, w, h, bytes_per_line, QImage.Format_RGB888
        ).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.width(),
                self.video_label.height(),
                Qt.KeepAspectRatio,
            )
        )

        # Refresh chart on a throttled interval.
        if (
            self.last_chart_update.msecsTo(current_time)
            >= self.chart_update_interval_ms
        ):
            self.update_density_chart()
            self.last_chart_update = current_time

    def update_density_chart(self):
        """Redraw the density chart using buffered samples."""
        if not self.recognition_data or not getattr(self, "density_classes", None):
            self.ax.clear()
            self.ax.set_title("数量密度分布（暂无数据）")
            self.canvas.draw()
            return

        # Build per-class time series.
        from collections import defaultdict

        class_time_count = defaultdict(list)
        timestamps = [item[0] for item in self.recognition_data]
        plot_classes = sorted(self.density_classes)

        # Append values for each class at each timestamp.
        for _, _, frame_classes in self.recognition_data:
            for cls in plot_classes:
                class_time_count[cls].append(frame_classes.get(cls, 0))

        self.ax.clear()

        # Handle colormap retrieval for newer Matplotlib versions.
        if hasattr(matplotlib, "colormaps"):
            # Only allocate colors for classes with non-zero history.
            valid_classes = [cls for cls in plot_classes if any(class_time_count[cls])]
            if not valid_classes:
                self.ax.set_title("数量密度分布（暂无数据）")
                self.canvas.draw()
                return
            color_map = matplotlib.colormaps.get_cmap("tab10").resampled(
                max(1, len(valid_classes))
            )
            for i, cls in enumerate(valid_classes):
                y = class_time_count[cls]
                color = color_map(i)
                self.ax.plot(
                    timestamps,
                    y,
                    label=cls,
                    linewidth=2.5,
                    marker="o",
                    markersize=7,
                    color=color,
                )
        else:
            import matplotlib.cm as cm

            # Only allocate colors for classes with non-zero history.
            valid_classes = [cls for cls in plot_classes if any(class_time_count[cls])]
            if not valid_classes:
                self.ax.set_title("数量密度分布（暂无数据）")
                self.canvas.draw()
                return
            color_map = cm.get_cmap("tab10", max(1, len(valid_classes)))
            for i, cls in enumerate(valid_classes):
                y = class_time_count[cls]
                color = (
                    color_map(i)
                    if hasattr(color_map, "__call__")
                    else color_map.colors[i]
                )
                self.ax.plot(
                    timestamps,
                    y,
                    label=cls,
                    linewidth=2.5,
                    marker="o",
                    markersize=7,
                    color=color,
                )

        self.ax.set_xlabel("时间", fontsize=12)
        self.ax.set_ylabel("数量", fontsize=12)
        self.ax.set_title("数量密度分布", fontsize=14, fontweight="bold")
        self.ax.grid(True, linestyle="--", alpha=0.4)

        locator = mdates.AutoDateLocator(minticks=3, maxticks=8)
        formatter = mdates.ConciseDateFormatter(locator)
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)
        self.fig.autofmt_xdate(rotation=30)

        self.ax.legend(
            fontsize=12, loc="upper left", frameon=True, fancybox=True, shadow=True
        )
        self.canvas.draw()

    def save_data_to_csv(self):
        """Save the current frame detections to a CSV file."""
        if (
            not self.bird_detector
            or not hasattr(self.bird_detector, "current_detection_info")
            or not self.bird_detector.current_detection_info
        ):
            self.statusBar.showMessage("没有检测数据可保存")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存数据", "", "CSV 文件 (*.csv)"
        )
        if file_path:
            try:
                # Export all detections from the current frame.
                # Write header row.
                with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(["时间戳", "类别", "总数量"])

                    # Write row data for each detected object.
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    total_objects = len(self.bird_detector.current_detection_info)
                    for info in self.bird_detector.current_detection_info:
                        writer.writerow([timestamp, info["class"], total_objects])
                self.statusBar.showMessage(f"数据已保存到 {file_path}")
            except Exception as error:
                self.statusBar.showMessage(f"保存文件失败: {error}")

    def closeEvent(self, event):
        """Handle graceful shutdown and optional trend plotting."""
        reply = QMessageBox.question(
            self,
            "确认退出",
            "确定要退出程序吗？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            # Release camera resources.
            if self.cap and self.cap.isOpened():
                self.cap.release()
            self.timer.stop()
            cv2.destroyAllWindows()

            # Generate trend chart from saved CSV data when possible.
            try:
                # Use the detector helper to generate the trend chart.
                if hasattr(self, "bird_detector") and self.bird_detector:
                    self.bird_detector.plot_trends()
            except Exception as error:
                print(f"生成趋势图时出错: {error}")
            event.accept()
        else:
            event.ignore()

    def load_model_and_classes(self, model_path):
        """Load a model and synchronize class selections."""
        # Proactively release any previous model instance.
        if hasattr(self, "bird_detector") and self.bird_detector is not None:
            del self.bird_detector
            gc.collect()

        try:
            self.model_path = resolve_model_path(model_path)
            self.bird_detector = ObjectDetector(self.model_path)
            self.all_classes = list(self.bird_detector.model.names.values())

            # Keep selected and density classes valid for the new model.
            if not hasattr(self, "selected_classes") or not self.selected_classes:
                self.selected_classes = set(self.all_classes)
            else:
                self.selected_classes = {
                    cls for cls in self.selected_classes if cls in self.all_classes
                } or set(self.all_classes)

            if not hasattr(self, "density_classes") or not self.density_classes:
                self.density_classes = set(self.selected_classes)
            else:
                self.density_classes = {
                    cls for cls in self.density_classes if cls in self.all_classes
                } or set(self.selected_classes)

            self.bird_detector.selected_classes = self.selected_classes
            self.bird_detector.density_classes = self.density_classes

            self.statusBar.showMessage(
                f"成功加载模型: {os.path.basename(self.model_path)}"
            )

        except Exception as error:
            self.statusBar.showMessage(f"加载模型失败: {error}")

            # Reset state when model loading fails.
            self.model_path = None
            self.all_classes = []
            self.selected_classes = set()
            self.density_classes = set()
            self.bird_detector = None  # Clear detector object.
