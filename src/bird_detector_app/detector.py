"""
Core object detection logic and plotting helpers.

Author: Tz2H
"""

import csv
import glob
import os
from datetime import datetime

import cv2
import matplotlib.pyplot as plt
import pandas as pd
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
        self.density_classes = set()
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

    def plot_trends(self):
        """Plot and save a trend chart from the latest CSV file."""
        csv_files = glob.glob(os.path.join(self.results_dir, "object_detection_*.csv"))
        if not csv_files:
            print("No detection result files were found.")
            return
        latest_csv = max(csv_files, key=os.path.getctime)
        print(f"Processing file: {latest_csv}")
        df = pd.read_csv(latest_csv)
        df["时间戳"] = pd.to_datetime(df["时间戳"])
        plt.figure(figsize=(15, 8))
        # Plot per-class totals over time.
        for obj_class, group in df.groupby("类别"):
            if obj_class in self.selected_classes:
                plt.plot(
                    group["时间戳"],
                    group["总数量"],
                    marker="o",
                    linestyle="-",
                    label=obj_class,
                )
        plt.title("目标检测数量趋势图", fontsize=16, fontweight="bold")
        plt.xlabel("时间", fontsize=12)
        plt.ylabel("目标数量", fontsize=12)
        plt.grid(True, linestyle="--", alpha=0.7)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.legend(fontsize=12)
        output_file = os.path.join(
            self.results_dir,
            f"object_trend_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
        )
        plt.savefig(output_file, dpi=300, bbox_inches="tight")
        print(f"Trend chart saved to: {output_file}")
        plt.show()

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
        """Draw bounding boxes and labels for valid detections."""
        detection_info = []
        class_counter = {}
        for detection in detections:
            x1, y1, x2, y2 = map(int, detection[:4])
            cls = int(detection[5])
            class_name = self.model.names[cls]
            if class_name not in self.selected_classes:
                continue
            class_counter[class_name] = class_counter.get(class_name, 0) + 1
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            # Render the class name on each bounding box.
            cv2.putText(
                frame,
                class_name,
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

    def process_frame(self, frame):
        """Run model inference on a frame and draw detections."""
        results = self.model.predict(frame)
        if len(results) > 0:
            detections = results[0].boxes.data.cpu().numpy()
            self.draw_detection(frame, detections)
        return frame
