"""
Core object detection logic and plotting helpers.

Author: Tz2H
"""

import csv
import os
from datetime import datetime

import cv2
import matplotlib.pyplot as plt
from ultralytics import YOLO

from utils.config_manager import resolve_model_path


class ObjectDetector:
    """YOLO-based object detector."""

    def __init__(self, model_path=None):
        """Initialize the detector and runtime state."""
        plt.rcParams["font.sans-serif"] = [
            "PingFang SC",
            "Hiragino Sans GB",
            "Heiti SC",
            "Microsoft YaHei",
            "SimHei",
            "Noto Sans CJK SC",
            "Arial Unicode MS",
            "DejaVu Sans",
        ]
        plt.rcParams["axes.unicode_minus"] = False
        self.model = YOLO(resolve_model_path(model_path))
        # High-accuracy profile for per-frame video analysis.
        self.inference_conf = 0.35
        self.inference_iou = 0.45
        self.inference_imgsz = 1536
        self.inference_max_det = 300
        self.inference_augment = True
        self.inference_rescue_conf = 0.20
        self.inference_half = False
        # Fast profile for video playback output stream.
        self.fast_inference_conf = 0.40
        self.fast_inference_iou = 0.50
        self.fast_inference_imgsz = 960
        self.fast_inference_max_det = 120
        self.fast_inference_augment = False
        self.colors = {
            "box": (0, 255, 0),
            "text_bg": (44, 44, 44),
            "text": (255, 255, 255),
        }
        self.results_dir = "results"
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        self.csv_file = os.path.join(
            self.results_dir,
            f"object_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        self.init_csv()
        self.total_objects = 0
        self.class_counts = {}
        self.selected_classes = set()
        self.heatmap_classes = set()
        self.heatmap_points = []
        self.max_heatmap_points = 20000
        self.current_detection_info = []
        # Counting-related runtime attributes.
        self.threshold = 20  # Tune this threshold as needed.
        self.max_count = 0
        self.count_history = []

    def init_csv(self):
        """Create the output CSV with a header row."""
        with open(self.csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["时间戳", "类别", "总数量"])

    def save_to_csv(self, detection_info):
        """Append detection results to the CSV file."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_objects = len(detection_info)
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for info in detection_info:
                if info["class"] in self.selected_classes:
                    writer.writerow([timestamp, info["class"], total_objects])
        self.total_objects = total_objects
        self.class_counts = {}
        for info in detection_info:
            obj_class = info["class"]
            if obj_class not in self.class_counts:
                self.class_counts[obj_class] = 0
            self.class_counts[obj_class] += 1

    def plot_heatmap(self):
        """Plot and save a spatial heatmap of object detections."""
        if not self.heatmap_points:
            print("No heatmap data available.")
            return

        # Extract data for selected classes
        xs = []
        ys = []
        for point in self.heatmap_points:
            if point["class"] in self.heatmap_classes:
                xs.append(point["x"])
                ys.append(point["y"])

        if not xs:
            print("No valid points to plot for selected classes.")
            return

        plt.figure(figsize=(8, 8), facecolor="#171A21")
        ax = plt.gca()
        ax.set_facecolor("#171A21")

        # Set axes limit to typical frame dimension 640x640 context
        ax.set_xlim(0, 640)
        ax.set_ylim(640, 0)  # Invert Y-axis for correct spatial mapping

        hb = ax.hexbin(xs, ys, gridsize=40, cmap="magma", mincnt=1, edgecolors="none")

        # Style improvements
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_color("#292D3E")
        ax.spines["left"].set_color("#292D3E")
        ax.tick_params(colors="#64748B")

        plt.title(
            "空间热力分布", fontsize=16, fontweight="bold", color="#F8FAFC", pad=12
        )
        plt.xlabel("X 坐标", fontsize=12, color="#94A3B8")
        plt.ylabel("Y 坐标", fontsize=12, color="#94A3B8")

        cb = plt.colorbar(hb, ax=ax)
        cb.set_label("出现频次", color="#94A3B8", fontsize=12)
        cb.ax.yaxis.set_tick_params(color="#94A3B8")
        cb.outline.set_edgecolor("#292D3E")
        plt.setp(plt.getp(cb.ax.axes, "yticklabels"), color="#64748B")

        plt.tight_layout()
        output_file = os.path.join(
            self.results_dir,
            f"heatmap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        plt.savefig(output_file, dpi=300, bbox_inches="tight", facecolor="#171A21")
        print(f"Heatmap chart saved to: {output_file}")
        plt.close()

    def draw_counting_bar(self, frame, current_count):
        """Draw the current count progress bar."""
        bar_width = 200
        bar_height = 25
        padding = 20
        bar_x = padding
        bar_y = padding
        percentage = current_count / max(1, self.threshold)
        filled_width = min(int(percentage * bar_width), bar_width)
        status, color = self.get_crowd_status(current_count)
        cv2.rectangle(
            frame,
            (bar_x - 5, bar_y - 5),
            (bar_x + bar_width + 5, bar_y + bar_height + 5),
            (180, 180, 180),
            -1,
        )
        cv2.rectangle(
            frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (50, 50, 50),
            -1,
        )
        cv2.rectangle(
            frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height), color, -1
        )
        cv2.rectangle(
            frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (180, 180, 180),
            1,
        )
        label = f"COUNT: {current_count}"
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        text_x = bar_x + 10
        text_y = bar_y + bar_height // 2 + text_size[1] // 2
        cv2.putText(
            frame,
            label,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

    def draw_threshold_bar(self, frame, current_count):
        """Draw the threshold utilization bar."""
        bar_width = 250
        bar_height = 25
        padding = 20
        bar_x = frame.shape[1] - bar_width - padding
        bar_y = padding
        percentage = min((current_count / max(1, self.threshold)), 1.0)
        percentage_display = min(int(percentage * 100), 100)
        filled_width = min(int(percentage * bar_width), bar_width)
        status, color = self.get_crowd_status(current_count)
        cv2.rectangle(
            frame,
            (bar_x - 5, bar_y - 5),
            (bar_x + bar_width + 5, bar_y + bar_height + 5),
            (180, 180, 180),
            -1,
        )
        cv2.rectangle(
            frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (50, 50, 50),
            -1,
        )
        cv2.rectangle(
            frame, (bar_x, bar_y), (bar_x + filled_width, bar_y + bar_height), color, -1
        )
        cv2.rectangle(
            frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            (180, 180, 180),
            1,
        )
        label = f"THRESHOLD: {percentage_display}%"
        text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
        text_x = bar_x + bar_width - text_size[0] - 10
        text_y = bar_y + bar_height // 2 + text_size[1] // 2
        cv2.putText(
            frame,
            label,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

    def draw_statistics_panel(self, frame, current_count):
        """Draw the bottom-left statistics panel."""
        panel_width = 250
        panel_height = 120
        panel_x = 20
        panel_y = frame.shape[0] - panel_height - 40
        self.max_count = getattr(self, "max_count", 0)
        self.max_count = max(self.max_count, current_count)
        self.count_history = getattr(self, "count_history", [])
        self.count_history.append(current_count)
        if len(self.count_history) > 100:
            self.count_history.pop(0)
        avg_count = (
            sum(self.count_history) / len(self.count_history)
            if self.count_history
            else 0
        )
        cv2.rectangle(
            frame,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y + panel_height),
            (44, 44, 44),
            -1,
        )
        cv2.rectangle(
            frame,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y + panel_height),
            (180, 180, 180),
            1,
        )
        cv2.putText(
            frame,
            f"当前数量: {current_count}",
            (panel_x + 10, panel_y + 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"最大数量: {self.max_count}",
            (panel_x + 10, panel_y + 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )
        cv2.putText(
            frame,
            f"平均数量: {avg_count:.1f}",
            (panel_x + 10, panel_y + 95),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

    def get_crowd_status(self, current_count):
        """Return status label and color for current count density."""
        percentage = (current_count / max(1, self.threshold)) * 100
        if percentage < 60:
            return ("NORMAL", (0, 255, 0))
        elif percentage < 90:
            return ("WARNING", (0, 165, 255))
        else:
            return ("CRITICAL", (0, 0, 255))

    def draw_detection(self, frame, detections):
        """Draw detection boxes and labels for filtered detections."""
        detection_info = []
        class_counter = {}

        for detection in detections:
            x1, y1, x2, y2 = map(int, detection[:4])
            confidence = float(detection[4])
            class_id = int(detection[5])
            class_name = self.model.names[class_id]
            if class_name not in self.selected_classes:
                continue

            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            self.heatmap_points.append({"class": class_name, "x": cx, "y": cy})
            if len(self.heatmap_points) > self.max_heatmap_points:
                overflow = len(self.heatmap_points) - self.max_heatmap_points
                del self.heatmap_points[:overflow]

            class_counter[class_name] = class_counter.get(class_name, 0) + 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label_text = f"{class_name} {confidence:.2f}"
            # Render the class name on each bounding box.
            cv2.putText(
                frame,
                label_text,
                (x1, y1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 255, 0),
                2,
            )

        if class_counter:
            label = " ".join([f"{k}={v}" for k, v in class_counter.items()])
            cv2.putText(
                frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
            )

        for cname, count in class_counter.items():
            for _ in range(count):
                detection_info.append({"class": cname})

        self.current_detection_info = detection_info
        self.total_objects = sum(class_counter.values())

    def _resolve_selected_class_ids(self):
        """Map selected class names to model class IDs for inference filtering."""
        if not self.selected_classes:
            return None

        return [
            class_id
            for class_id, class_name in self.model.names.items()
            if class_name in self.selected_classes
        ]

    def _predict_with_profile(
        self,
        frame,
        selected_class_ids,
        conf,
        iou,
        imgsz,
        max_det,
        augment,
        rescue_conf=None,
    ):
        """Run YOLO predict using the provided profile and optional fallback pass."""
        results = self.model.predict(
            frame,
            conf=conf,
            iou=iou,
            imgsz=imgsz,
            max_det=max_det,
            augment=augment,
            half=self.inference_half,
            classes=selected_class_ids,
            verbose=False,
        )

        has_detection = (
            len(results) > 0
            and results[0].boxes is not None
            and len(results[0].boxes) > 0
        )

        if not has_detection and rescue_conf is not None and rescue_conf < conf:
            results = self.model.predict(
                frame,
                conf=rescue_conf,
                iou=iou,
                imgsz=imgsz,
                max_det=max_det,
                augment=augment,
                half=self.inference_half,
                classes=selected_class_ids,
                verbose=False,
            )
            has_detection = (
                len(results) > 0
                and results[0].boxes is not None
                and len(results[0].boxes) > 0
            )

        if has_detection:
            detections = results[0].boxes.data.cpu().numpy()
            self.draw_detection(frame, detections)
        else:
            self.current_detection_info = []
            self.total_objects = 0

        return frame

    def process_frame(self, frame):
        """Run model inference on a frame and draw detections."""
        selected_class_ids = self._resolve_selected_class_ids()

        if self.selected_classes and not selected_class_ids:
            self.current_detection_info = []
            self.total_objects = 0
            return frame

        return self._predict_with_profile(
            frame,
            selected_class_ids,
            conf=self.inference_conf,
            iou=self.inference_iou,
            imgsz=self.inference_imgsz,
            max_det=self.inference_max_det,
            augment=self.inference_augment,
            rescue_conf=self.inference_rescue_conf,
        )

    def process_frame_fast(self, frame):
        """Run low-latency inference profile for video playback stream."""
        selected_class_ids = self._resolve_selected_class_ids()

        if self.selected_classes and not selected_class_ids:
            self.current_detection_info = []
            self.total_objects = 0
            return frame

        return self._predict_with_profile(
            frame,
            selected_class_ids,
            conf=self.fast_inference_conf,
            iou=self.fast_inference_iou,
            imgsz=self.fast_inference_imgsz,
            max_det=self.fast_inference_max_det,
            augment=self.fast_inference_augment,
            rescue_conf=None,
        )
