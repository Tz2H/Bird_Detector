"""Runtime behaviors for detection, charting, and I/O."""

import csv
import gc
import os
import threading
from collections import deque
from datetime import datetime

import cv2
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

    def _set_detection_state(self, running, message=None):
        """Set detection state and keep button UI in sync."""
        self.is_detecting = running
        if running:
            self.start_stop_button.setText("停止检测")
            self.start_stop_button.setIcon(
                self.style().standardIcon(self.style().SP_MediaStop)
            )
        else:
            self.start_stop_button.setText("开始检测")
            self.start_stop_button.setIcon(
                self.style().standardIcon(self.style().SP_MediaPlay)
            )

        if message:
            self.statusBar.showMessage(message)

    def _clear_pending_inference(self, wait=False):
        """Cancel and clear pending inference future when possible."""
        pending = getattr(self, "pending_inference", None)
        if pending is None:
            self.pending_inference = None
            return True

        if not pending.done():
            if wait:
                try:
                    pending.result(timeout=5)
                except Exception:
                    if not pending.cancel():
                        return False
            else:
                pending.cancel()

        self.pending_inference = None
        return True

    def _ensure_file_pipeline_state(self):
        """Initialize lazy runtime state for file-video inference pipeline."""
        if not hasattr(self, "file_result_queue"):
            self.file_result_queue = deque(maxlen=18)
        if not hasattr(self, "file_pipeline_thread"):
            self.file_pipeline_thread = None
        if not hasattr(self, "file_pipeline_stop_requested"):
            self.file_pipeline_stop_requested = False
        if not hasattr(self, "file_pipeline_finished"):
            self.file_pipeline_finished = False
        if not hasattr(self, "file_pipeline_error"):
            self.file_pipeline_error = None
        if not hasattr(self, "file_last_output_frame"):
            self.file_last_output_frame = None
        if not hasattr(self, "file_playback_interval_ms"):
            self.file_playback_interval_ms = 33
        if not hasattr(self, "last_file_playback_time"):
            self.last_file_playback_time = QDateTime.currentDateTime()

    def _file_pipeline_worker(self):
        """Decode and infer video-file frames in a background thread."""
        detector = getattr(self, "bird_detector", None)
        capture = getattr(self, "cap", None)

        if detector is None or capture is None:
            self.file_pipeline_finished = True
            return

        while not self.file_pipeline_stop_requested:
            ret, frame = capture.read()
            if not ret:
                break

            try:
                processed_frame = detector.process_frame_fast(frame.copy())
            except Exception as error:
                self.file_pipeline_error = str(error)
                break

            detection_info = [
                dict(item) for item in getattr(detector, "current_detection_info", [])
            ]
            total_objects = int(getattr(detector, "total_objects", 0))
            self.file_result_queue.append((
                processed_frame,
                total_objects,
                detection_info,
                datetime.now(),
            ))

        self.file_pipeline_finished = True

    def _start_file_pipeline(self):
        """Start background file-video pipeline if it is not already running."""
        self._ensure_file_pipeline_state()

        # Natural EOF should not trigger implicit pipeline restart.
        if self.file_pipeline_finished:
            return True

        if (
            self.file_pipeline_thread is not None
            and self.file_pipeline_thread.is_alive()
        ):
            return True

        detector = getattr(self, "bird_detector", None)
        capture = getattr(self, "cap", None)
        if detector is None or capture is None or not capture.isOpened():
            return False

        self.file_result_queue.clear()
        self.file_pipeline_stop_requested = False
        self.file_pipeline_finished = False
        self.file_pipeline_error = None
        self.file_last_output_frame = None
        self.last_file_playback_time = QDateTime.currentDateTime()
        self.file_pipeline_thread = threading.Thread(
            target=self._file_pipeline_worker,
            daemon=True,
        )
        self.file_pipeline_thread.start()
        return True

    def _stop_file_pipeline(self, wait=False, clear_queue=True):
        """Stop file-video pipeline thread and optionally wait for shutdown."""
        self._ensure_file_pipeline_state()
        self.file_pipeline_stop_requested = True

        pipeline_thread = self.file_pipeline_thread
        if wait and pipeline_thread is not None and pipeline_thread.is_alive():
            pipeline_thread.join(timeout=2.0)

        if pipeline_thread is not None and not pipeline_thread.is_alive():
            self.file_pipeline_thread = None

        if clear_queue:
            self.file_result_queue.clear()
            self.file_last_output_frame = None
        self.file_pipeline_error = None
        self.file_pipeline_finished = False

    def _build_current_frame_class_counts(self, detection_info):
        """Aggregate per-class counts for charting and logs."""
        current_frame_class_counts = {cls: 0 for cls in sorted(self.heatmap_classes)}
        for det_info in detection_info:
            class_name = det_info.get("class")
            if class_name in current_frame_class_counts:
                current_frame_class_counts[class_name] += 1
        return current_frame_class_counts

    def _apply_detection_updates(self, detector, detection_info, now_dt):
        """Apply shared post-inference updates to UI and runtime buffers."""
        self.count_label.setText(f"识别到的鸟类数量: {detector.total_objects}")
        current_frame_class_counts = self._build_current_frame_class_counts(
            detection_info
        )

        # Write trend data at most once per second to avoid excessive I/O.
        current_second = now_dt.strftime("%Y-%m-%d %H:%M:%S")
        if detection_info and current_second != getattr(
            self, "last_csv_save_second", None
        ):
            detector.save_to_csv(detection_info)
            self.last_csv_save_second = current_second

        # Feed the real-time textual tracking log if applicable.
        if hasattr(self, "log_text_edit"):
            total_logged = sum(current_frame_class_counts.values())
            if total_logged > 0:
                log_lines = [
                    f"🟢 监控激活 - 定位到目标 ({now_dt.strftime('%H:%M:%S')})",
                    "=" * 32,
                ]
                for class_name, count in current_frame_class_counts.items():
                    if count > 0:
                        log_lines.append(f"  ▶ {class_name}: {count} 实体")
                log_lines.append("=" * 32)
                log_lines.append(f"⚡ 推理速度: {self.fps:.1f} FPS")
                self.log_text_edit.setText("\n".join(log_lines))
            else:
                self.log_text_edit.setText(
                    f"⚪ 静态观测中 ({now_dt.strftime('%H:%M:%S')})...\n\n目前未检测到活动目标"
                )

        total_objects_for_heatmap = sum(current_frame_class_counts.values())
        self.recognition_data.append((
            now_dt,
            total_objects_for_heatmap,
            current_frame_class_counts,
        ))
        if len(self.recognition_data) > 300:
            self.recognition_data.pop(0)

    def _save_heatmap_chart_to_results(self, notify=False):
        """Save current heatmap chart snapshot into the results directory."""
        if not hasattr(self, "fig"):
            return None

        detector = getattr(self, "bird_detector", None)
        if not detector or not getattr(detector, "heatmap_points", None):
            return None

        results_dir = getattr(detector, "results_dir", "results")

        try:
            os.makedirs(results_dir, exist_ok=True)
            file_name = (
                f"spatial_heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            )
            output_path = os.path.join(results_dir, file_name)
            self.fig.savefig(
                output_path, dpi=300, bbox_inches="tight", facecolor="#171A21"
            )
            if notify:
                self.statusBar.showMessage(f"空间热力图已保存: {file_name}")
            return output_path
        except Exception as error:
            if notify:
                self.statusBar.showMessage(f"保存热力图失败: {error}")
            return None

    def toggle_detection(self):
        """Toggle detection state between running and paused."""
        is_file_source = getattr(self, "video_source_kind", "camera") == "file"

        if not self.is_detecting:
            if getattr(self, "bird_detector", None) is None:
                self.statusBar.showMessage("模型未加载，无法开始检测")
                return

            if is_file_source:
                self._stop_file_pipeline(wait=True, clear_queue=True)
                self.is_video_paused = False
                self._set_detection_state(True, "检测中，视频继续播放...")
            else:
                self._set_detection_state(True, "检测中...")
            return

        stop_message = "检测已停止"
        if is_file_source:
            self.is_video_paused = True
            stop_message = "检测已停止，视频已暂停"

        self._set_detection_state(False, stop_message)
        if is_file_source:
            self._stop_file_pipeline(wait=False, clear_queue=True)
        self._clear_pending_inference()

        detector = getattr(self, "bird_detector", None)
        if detector is not None:
            # Reset frame-level detection state.
            if hasattr(detector, "current_detection_info"):
                detector.current_detection_info = []
            detector.total_objects = 0
        self.count_label.setText("识别到的鸟类数量: 0")
        self._save_heatmap_chart_to_results(notify=True)

    def _set_source_combo_value(self, source_text):
        """Update source selector without retriggering selection logic."""
        source_combo = getattr(self, "source_combo", None)
        if source_combo is None:
            return

        previous_state = source_combo.blockSignals(True)
        source_combo.setCurrentText(source_text)
        source_combo.blockSignals(previous_state)

    def on_source_changed(self, source_text):
        """Handle source selector changes between camera and file."""
        if source_text == "视频文件":
            if not self.open_video(sync_source_combo=False):
                self._set_source_combo_value("摄像头")
            return

        self._stop_file_pipeline(wait=True, clear_queue=True)

        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.cap = None
        self.video_source_kind = "camera"
        self.is_video_paused = False

        self._set_detection_state(False, "已切换到摄像头输入")
        self._clear_pending_inference()

    def open_video(self, *_args, sync_source_combo=True):
        """Open and use a local video file as input."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开视频文件", "", "视频文件 (*.mp4 *.avi *.mkv)"
        )
        if not file_path:
            return False

        self._stop_file_pipeline(wait=True, clear_queue=True)

        # Release existing capture before opening a new source.
        if self.cap and self.cap.isOpened():
            self.cap.release()

        self.cap = cv2.VideoCapture(file_path)
        if not self.cap.isOpened():
            self.statusBar.showMessage(
                f"无法打开视频文件: {os.path.basename(file_path)}"
            )
            self.cap = None
            return False

        self.selected_camera = None
        self.video_source_kind = "file"
        self.is_video_paused = False

        self._ensure_file_pipeline_state()
        source_fps = self.cap.get(cv2.CAP_PROP_FPS)
        if source_fps and source_fps > 1:
            self.file_playback_interval_ms = max(10, int(1000 / source_fps))
        else:
            self.file_playback_interval_ms = 33
        self.last_file_playback_time = QDateTime.currentDateTime()
        self.file_last_output_frame = None

        self._clear_pending_inference()

        detector = getattr(self, "bird_detector", None)
        if detector is None:
            self._set_detection_state(
                False,
                f"已打开视频: {os.path.basename(file_path)}（模型未加载，未自动开始检测）",
            )
        else:
            self._set_detection_state(
                True, f"已打开视频并开始检测: {os.path.basename(file_path)}"
            )

        if sync_source_combo:
            self._set_source_combo_value("视频文件")
        return True

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
            "YOLO智能识别分析系统\n版本: 1.0.0",
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

    def _render_frame_to_video_label(self, frame):
        """Render an OpenCV frame onto the preview label."""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(
            frame.data, w, h, bytes_per_line, QImage.Format_RGB888
        ).rgbSwapped()
        pixmap = QPixmap.fromImage(qt_image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.width(),
                self.video_label.height(),
                Qt.KeepAspectRatio,
            )
        )

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
            if (
                getattr(self, "video_source_kind", "camera") == "file"
                and self.cap is not None
                and getattr(self, "is_video_paused", False)
            ):
                self.fps_label.setText("FPS: 0.0")
                return

            # Keep previewing frames when detection is paused.
            if self.cap is None:
                if getattr(self, "video_source_kind", "camera") == "file":
                    return
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
                    self._render_frame_to_video_label(processed_frame)
                    return

            ret, frame = self.cap.read()
            if not ret:
                if getattr(self, "video_source_kind", "camera") == "file":
                    self.is_video_paused = True
                    self.statusBar.showMessage("视频播放完毕，视频已暂停")
                    return
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
                if not ret:
                    self.statusBar.showMessage("视频播放完毕或无法读取帧")
                    return

            # Render preview frame without detection overlays.
            processed_frame = frame
            self.count_label.setText("识别到的鸟类数量: 0")
            self.fps_label.setText(f"FPS: {self.fps:.1f}")
            self._render_frame_to_video_label(processed_frame)
            return

        if self.cap is None:
            if getattr(self, "video_source_kind", "camera") == "file":
                self._set_detection_state(False, "未加载视频文件，无法执行检测")
                self._clear_pending_inference()
                return
            if self.selected_camera is None:
                if not self.show_camera_selection_dialog():
                    self._set_detection_state(False, "检测已停止")
                    self._clear_pending_inference()
                    return
            self.cap = cv2.VideoCapture(self.selected_camera)

            # Set camera resolution to 640x640.
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 640)

            # Reduce camera buffer latency.
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            if not self.cap.isOpened():
                self._set_detection_state(False, "摄像头无法打开或不可用")
                self._clear_pending_inference()
                return

        detector = getattr(self, "bird_detector", None)
        if detector is None:
            self._set_detection_state(False, "模型未加载，无法执行检测")
            self._clear_pending_inference()
            return

        is_file_source = getattr(self, "video_source_kind", "camera") == "file"
        if is_file_source:
            if not self._start_file_pipeline():
                self._set_detection_state(False, "视频处理线程启动失败")
                self._clear_pending_inference()
                return

            can_present_next_frame = (
                self.last_file_playback_time.msecsTo(current_time)
                >= self.file_playback_interval_ms
            ) or len(self.file_result_queue) >= 3

            if can_present_next_frame and self.file_result_queue:
                (
                    processed_frame,
                    total_objects,
                    detection_info,
                    inferred_dt,
                ) = self.file_result_queue.popleft()
                self.file_last_output_frame = processed_frame
                self.last_file_playback_time = current_time
                detector.total_objects = total_objects
                detector.current_detection_info = detection_info
                self._apply_detection_updates(detector, detection_info, inferred_dt)

                self.fps_label.setText(f"FPS: {self.fps:.1f}")
                self._render_frame_to_video_label(processed_frame)

                if (
                    self.last_chart_update.msecsTo(current_time)
                    >= self.chart_update_interval_ms
                ):
                    self.update_heatmap_chart()
                    self.last_chart_update = current_time
                return

            if self.file_pipeline_error:
                self._set_detection_state(
                    False, f"检测失败: {self.file_pipeline_error}"
                )
                self._stop_file_pipeline(wait=True, clear_queue=True)
                self._clear_pending_inference()
                return

            pipeline_thread = self.file_pipeline_thread
            if self.file_pipeline_finished and (
                pipeline_thread is None or not pipeline_thread.is_alive()
            ):
                self.is_video_paused = True
                self._set_detection_state(False, "视频播放完毕，已暂停检测和视频")
                self._stop_file_pipeline(wait=False, clear_queue=True)
                self._clear_pending_inference()
                self._save_heatmap_chart_to_results()
                return

            self.count_label.setText(f"识别到的鸟类数量: {detector.total_objects}")
            self.fps_label.setText(f"FPS: {self.fps:.1f}")
            if self.file_last_output_frame is not None:
                self._render_frame_to_video_label(self.file_last_output_frame)
            return

        ret, frame = self.cap.read()
        if not ret:
            if getattr(self, "video_source_kind", "camera") == "file":
                self.is_video_paused = True
                self._set_detection_state(False, "视频播放完毕，已暂停检测和视频")
                self._clear_pending_inference()
                self._save_heatmap_chart_to_results()
                return
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
            if not ret:
                self._set_detection_state(False, "视频播放完毕或无法读取帧")
                self._clear_pending_inference()
                return
        processed_frame = frame
        pending_inference = getattr(self, "pending_inference", None)
        if pending_inference is None:
            self.pending_inference = self.inference_executor.submit(
                detector.process_frame, frame.copy()
            )
            pending_inference = self.pending_inference

        inference_ready = pending_inference is not None and pending_inference.done()

        if inference_ready:
            try:
                processed_frame = pending_inference.result()
            except Exception as error:
                self._set_detection_state(False, f"检测失败: {error}")
                self._clear_pending_inference()
                return
            self.pending_inference = None

        if inference_ready:
            detection_info = [
                dict(item) for item in getattr(detector, "current_detection_info", [])
            ]
            self._apply_detection_updates(detector, detection_info, datetime.now())
        else:
            if hasattr(detector, "draw_cached_tracks"):
                processed_frame = detector.draw_cached_tracks(frame.copy())
            self.count_label.setText(f"识别到的鸟类数量: {detector.total_objects}")

        self.fps_label.setText(f"FPS: {self.fps:.1f}")

        # Refresh video display.
        self._render_frame_to_video_label(processed_frame)

        # Refresh chart on a throttled interval.
        if inference_ready and (
            self.last_chart_update.msecsTo(current_time)
            >= self.chart_update_interval_ms
        ):
            self.update_heatmap_chart()
            self.last_chart_update = current_time

    def update_heatmap_chart(self):
        """Redraw the spatial heatmap using detected object points."""
        self.ax.clear()

        # Set dark theme styling
        self.ax.set_facecolor("#171A21")
        self.fig.patch.set_facecolor("#171A21")
        self.ax.spines["top"].set_visible(False)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["left"].set_color("#292D3E")
        self.ax.spines["bottom"].set_color("#292D3E")
        self.ax.tick_params(colors="#64748B")

        self.ax.set_xlim(0, 640)
        self.ax.set_ylim(640, 0)  # Real world image coordinates

        detector = getattr(self, "bird_detector", None)
        heatmap_points = getattr(detector, "heatmap_points", []) if detector else []

        if not heatmap_points or not getattr(self, "heatmap_classes", None):
            self.ax.set_title(
                "空间热力分布（暂无数据）",
                fontsize=15,
                fontweight="600",
                color="#F8FAFC",
                pad=12,
            )
            self.canvas.draw()
            return

        xs = []
        ys = []
        for point in heatmap_points:
            if point["class"] in self.heatmap_classes:
                xs.append(point["x"])
                ys.append(point["y"])

        if not xs:
            self.ax.set_title(
                "空间热力分布（暂无数据）",
                fontsize=15,
                fontweight="600",
                color="#F8FAFC",
                pad=12,
            )
            self.canvas.draw()
            return

        self.ax.hexbin(
            xs,
            ys,
            gridsize=30,
            cmap="magma",
            mincnt=1,
            edgecolors="none",
        )

        self.ax.set_xlabel("X 坐标", fontsize=12, color="#94A3B8")
        self.ax.set_ylabel("Y 坐标", fontsize=12, color="#94A3B8")
        self.ax.set_title(
            "空间热力分布", fontsize=15, fontweight="600", color="#F8FAFC", pad=12
        )
        self.ax.grid(True, linestyle=":", alpha=0.15, color="#F8FAFC")

        self.fig.tight_layout()
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
        self._stop_file_pipeline(wait=True, clear_queue=True)
        self._clear_pending_inference(wait=True)
        self._save_heatmap_chart_to_results()

        # Release camera resources.
        if self.cap and self.cap.isOpened():
            self.cap.release()
        self.timer.stop()
        if hasattr(self, "inference_executor") and self.inference_executor:
            self.inference_executor.shutdown(wait=False, cancel_futures=True)
        cv2.destroyAllWindows()

    def load_model_and_classes(self, model_path):
        """Load a model and synchronize class selections."""
        self._stop_file_pipeline(wait=True, clear_queue=True)
        if not self._clear_pending_inference(wait=True):
            self.statusBar.showMessage("检测任务仍在运行，请稍后再切换模型")
            return
        old_detector = getattr(self, "bird_detector", None)

        try:
            resolved_model_path = resolve_model_path(model_path)
            new_detector = ObjectDetector(resolved_model_path)
            new_all_classes = list(new_detector.model.names.values())

            # Keep only bird for detection and heatmap chart.
            bird_class = next(
                (cls for cls in new_all_classes if str(cls).lower() == "bird"),
                None,
            )
            next_selected_classes = {bird_class} if bird_class else set()
            next_heatmap_classes = set(next_selected_classes)

            new_detector.selected_classes = next_selected_classes
            new_detector.heatmap_classes = next_heatmap_classes

            self.model_path = resolved_model_path
            self.bird_detector = new_detector
            self.all_classes = new_all_classes
            self.selected_classes = next_selected_classes
            self.heatmap_classes = next_heatmap_classes

            if old_detector is not None and old_detector is not new_detector:
                del old_detector
                gc.collect()

            model_name = os.path.basename(self.model_path)
            if next_selected_classes:
                self.statusBar.showMessage(f"成功加载模型: {model_name}（仅检测 bird）")
            else:
                self.statusBar.showMessage(
                    f"成功加载模型: {model_name}（模型不含 bird 类）"
                )

        except Exception as error:
            self.statusBar.showMessage(f"加载模型失败: {error}")
