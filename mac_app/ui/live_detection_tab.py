import cv2
import numpy as np
import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox, QTableWidget,
    QTableWidgetItem, QCheckBox, QPushButton, QScrollArea, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QImage, QPixmap
from core.collision_zone import CollisionZone
from core.inference_engine import InferenceResult

class LiveDetectionTab(QWidget):
    def __init__(self, engine_ref):
        super().__init__()
        self.engine = engine_ref
        
        # Dataset capture state
        self.capture_count = 0
        self.dataset_dir = "rc_car_dataset"
        os.makedirs(self.dataset_dir, exist_ok=True)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left side: Video Feed (75%)
        self.video_label = QLabel("Waiting for video feed...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_label, stretch=3)
        
        # Right side: Control Panel (25%)
        control_panel = QVBoxLayout()
        
        # Object Counts
        counts_group = QGroupBox("Object Counts")
        counts_layout = QVBoxLayout()
        self.counts_table = QTableWidget(0, 2)
        self.counts_table.setHorizontalHeaderLabels(["Class", "Count"])
        self.counts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        counts_layout.addWidget(self.counts_table)
        counts_group.setLayout(counts_layout)
        control_panel.addWidget(counts_group)
        
        # Collision Zone
        zone_group = QGroupBox("Collision Zone")
        zone_layout = QVBoxLayout()
        self.zone_checkbox = QCheckBox("Enable Collision Zone Warning")
        zone_layout.addWidget(self.zone_checkbox)
        zone_group.setLayout(zone_layout)
        control_panel.addWidget(zone_group)
        
        # Dataset Capture
        dataset_group = QGroupBox("Dataset Capture")
        dataset_layout = QVBoxLayout()
        self.capture_btn = QPushButton("Capture Frame")
        self.capture_btn.clicked.connect(self.capture_frame)
        self.capture_label = QLabel("Total Captured: 0")
        dataset_layout.addWidget(self.capture_btn)
        dataset_layout.addWidget(self.capture_label)
        dataset_group.setLayout(dataset_layout)
        control_panel.addWidget(dataset_group)
        
        # Class Filter
        filter_group = QGroupBox("Class Filter")
        filter_layout = QVBoxLayout()
        self.filter_checkboxes = {}
        
        # COCO IDs for these classes:
        # person:0, car:2, bicycle:1, dog:16, cat:15, chair:56, laptop:63, bottle:39, phone:67
        common_classes = {
            "Person": 0, "Car": 2, "Bicycle": 1, "Dog": 16, "Cat": 15,
            "Chair": 56, "Laptop": 63, "Bottle": 39, "Phone": 67
        }
        
        for name, cls_id in common_classes.items():
            cb = QCheckBox(name)
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_filters)
            self.filter_checkboxes[cls_id] = cb
            filter_layout.addWidget(cb)
            
        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(filter_layout)
        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        
        filter_box_layout = QVBoxLayout()
        filter_box_layout.addWidget(scroll_area)
        filter_group.setLayout(filter_box_layout)
        control_panel.addWidget(filter_group)
        
        layout.addLayout(control_panel, stretch=1)
        
        # State to store latest frame for dataset capture
        self._latest_frame = None
        self._latest_result = None

    def update_filters(self):
        active_ids = [cls_id for cls_id, cb in self.filter_checkboxes.items() if cb.isChecked()]
        if len(active_ids) == len(self.filter_checkboxes):
            self.engine.set_class_filter(None)
        else:
            self.engine.set_class_filter(active_ids)
            
    def capture_frame(self):
        if self._latest_frame is not None:
            filename = os.path.join(self.dataset_dir, f"capture_{self.capture_count:04d}.jpg")
            cv2.imwrite(filename, self._latest_frame)
            # Would also save labels here...
            self.capture_count += 1
            self.capture_label.setText(f"Total Captured: {self.capture_count}")

    def update_display(self, frame: np.ndarray, result: InferenceResult, collision_zone: CollisionZone):
        self._latest_frame = frame.copy()
        self._latest_result = result
        
        disp_frame = frame.copy()
        
        if self.zone_checkbox.isChecked():
            alerts = collision_zone.check_hazards(result.detections, disp_frame.shape)
            disp_frame = collision_zone.draw_zone(disp_frame, alerts)
            
        # Draw bounding boxes
        for det in result.detections:
            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(disp_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{det.class_name} {det.confidence:.2f}"
            cv2.putText(disp_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
        # Convert BGR to RGB
        disp_frame_rgb = cv2.cvtColor(disp_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = disp_frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(disp_frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        
        # Scale pixmap to fit label
        scaled_pixmap = pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.video_label.setPixmap(scaled_pixmap)
        
        # Update Object Counts
        counts = result.count_by_class
        self.counts_table.setRowCount(len(counts))
        for row, (cls_name, count) in enumerate(counts.items()):
            self.counts_table.setItem(row, 0, QTableWidgetItem(cls_name))
            self.counts_table.setItem(row, 1, QTableWidgetItem(str(count)))
