"""
Core object detection logic and plotting helpers.

Author: Tz2H
"""

import csv
import os
from datetime import datetime

import cv2
from ultralytics import YOLO

from utils.config_manager import resolve_model_path


class ObjectDetector:
    """YOLO-based object detector."""

    def __init__(self, model_path=None):
        """Initialize the detector and runtime state."""
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
        self.results_dir = "results"
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        self.csv_file = os.path.join(
            self.results_dir,
            f"object_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )
        self.init_csv()
        self.total_objects = 0
        self.selected_classes = set()
        self.heatmap_classes = set()
        self.heatmap_points = []
        self.max_heatmap_points = 20000
        self.current_detection_info = []

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
