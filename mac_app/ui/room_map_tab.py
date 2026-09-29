import cv2
import numpy as np
import time
import math
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox, QPushButton, 
    QProgressBar, QTableWidget, QTableWidgetItem, QSpinBox, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QPen, QColor, QFont

from spatial.keyframe_selector import KeyframeSelector, SensorData
from spatial.angular_dedup import AngularDeduplicator

class RoomMapTab(QWidget):
    def __init__(self, engine_ref):
        super().__init__()
        self.engine = engine_ref
        
        self.selector = KeyframeSelector(yaw_threshold=30.0, pitch_threshold=20.0)
        self.dedup = AngularDeduplicator(merge_threshold=15.0)
        
        self.fake_yaw = 0.0
        self.last_fake_update = time.time()
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left side: Preview/Map (60%)
        self.map_label = QLabel("Ready to scan...")
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setStyleSheet("background-color: #222;")
        layout.addWidget(self.map_label, stretch=6)
        
        # Right side: Controls (40%)
        control_panel = QVBoxLayout()
        
        # Scan Controls
        scan_group = QGroupBox("Scan Controls")
        scan_layout = QVBoxLayout()
        
        self.start_btn = QPushButton("Start Scan")
        self.start_btn.setStyleSheet("background-color: green; color: white;")
        self.start_btn.clicked.connect(self.start_scan)
        
        self.stop_btn = QPushButton("Stop Scan")
        self.stop_btn.setStyleSheet("background-color: red; color: white;")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scan)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        
        self.keyframe_label = QLabel("Keyframes: 0")
        
        scan_layout.addWidget(self.start_btn)
        scan_layout.addWidget(self.stop_btn)
        scan_layout.addWidget(self.progress_bar)
        scan_layout.addWidget(self.keyframe_label)
        scan_group.setLayout(scan_layout)
        control_panel.addWidget(scan_group)
        
        # Room Inventory
        inventory_group = QGroupBox("Room Inventory")
        inventory_layout = QVBoxLayout()
        self.inventory_table = QTableWidget(0, 3)
        self.inventory_table.setHorizontalHeaderLabels(["Class", "Count", "Avg Conf"])
        self.inventory_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        inventory_layout.addWidget(self.inventory_table)
        inventory_group.setLayout(inventory_layout)
        control_panel.addWidget(inventory_group)
        
        # Scan Settings
        settings_group = QGroupBox("Scan Settings")
        settings_layout = QVBoxLayout()
        
        yaw_layout = QHBoxLayout()
        yaw_layout.addWidget(QLabel("Yaw Threshold (°):"))
        self.yaw_spinbox = QSpinBox()
        self.yaw_spinbox.setRange(15, 60)
        self.yaw_spinbox.setValue(30)
        self.yaw_spinbox.valueChanged.connect(lambda v: setattr(self.selector, 'yaw_threshold', float(v)))
        yaw_layout.addWidget(self.yaw_spinbox)
        
        pitch_layout = QHBoxLayout()
        pitch_layout.addWidget(QLabel("Pitch Threshold (°):"))
        self.pitch_spinbox = QSpinBox()
        self.pitch_spinbox.setRange(10, 45)
        self.pitch_spinbox.setValue(20)
        self.pitch_spinbox.valueChanged.connect(lambda v: setattr(self.selector, 'pitch_threshold', float(v)))
        pitch_layout.addWidget(self.pitch_spinbox)
        
        settings_layout.addLayout(yaw_layout)
        settings_layout.addLayout(pitch_layout)
        settings_group.setLayout(settings_layout)
        control_panel.addWidget(settings_group)
        
        layout.addLayout(control_panel, stretch=4)
        
    def start_scan(self):
        self.selector.start_scan()
        self.dedup.reset()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.inventory_table.setRowCount(0)
        self.fake_yaw = 0.0
        
    def stop_scan(self):
        keyframes = self.selector.stop_scan()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.populate_inventory()
        self.render_map()
        
    def populate_inventory(self):
        inventory = self.dedup.get_inventory()
        objects = self.dedup.get_unique_objects()
        
        self.inventory_table.setRowCount(len(inventory))
        row = 0
        for cls_name, count in inventory.items():
            objs = [o for o in objects if o.class_name == cls_name]
            avg_conf = sum(o.confidence for o in objs) / len(objs) if objs else 0.0
            
            self.inventory_table.setItem(row, 0, QTableWidgetItem(cls_name))
            self.inventory_table.setItem(row, 1, QTableWidgetItem(str(count)))
            self.inventory_table.setItem(row, 2, QTableWidgetItem(f"{avg_conf:.2f}"))
            row += 1
            
    def update_display(self, frame: np.ndarray, sensor_data: SensorData):
        if not self.selector.is_scanning:
            # Just show live feed if not scanning and map not rendered yet
            if self.inventory_table.rowCount() == 0:
                self.show_frame(frame)
            return
            
        if self.selector.should_capture(sensor_data):
            kf = self.selector.capture(frame, sensor_data)
            
            # Run inference on keyframe
            result = self.engine.infer(frame)
            kf.detections = result.detections
            
            # Add to dedup
            for det in result.detections:
                world_angle = self.selector.estimate_object_world_angle(
                    kf, det.center[0], frame.shape[1]
                )
                self.dedup.add_detection(det.class_name, world_angle, det.confidence, kf.index)
                
            self.keyframe_label.setText(f"Keyframes: {self.selector.keyframe_count}")
            self.progress_bar.setValue(int(self.selector.get_coverage_percentage()))
            
        self.show_frame(frame)
        
    def show_frame(self, frame: np.ndarray):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled_pixmap = pixmap.scaled(self.map_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.map_label.setPixmap(scaled_pixmap)

    def generate_fake_sensor_data(self) -> SensorData:
        now = time.time()
        dt = now - self.last_fake_update
        self.last_fake_update = now
        
        # slowly rotate 15 degrees per second
        self.fake_yaw = (self.fake_yaw + 15.0 * dt) % 360
        return SensorData(yaw=self.fake_yaw, pitch=0.0, roll=0.0, timestamp=now)
        
    def render_map(self):
        w, h = self.map_label.width(), self.map_label.height()
        pixmap = QPixmap(w, h)
        pixmap.fill(QColor("#222"))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        cx, cy = w // 2, h // 2
        radius = min(w, h) // 2 - 40
        
        # Draw radar circle
        pen = QPen(QColor("#555"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawEllipse(cx - radius, cy - radius, radius * 2, radius * 2)
        
        # Draw center point (camera)
        painter.setBrush(QColor("blue"))
        painter.drawEllipse(cx - 5, cy - 5, 10, 10)
        
        # Draw objects
        objects = self.dedup.get_unique_objects()
        for obj in objects:
            angle_rad = math.radians(obj.world_angle - 90) # 0 is up
            ox = cx + int(math.cos(angle_rad) * radius)
            oy = cy + int(math.sin(angle_rad) * radius)
            
            painter.setBrush(QColor("red"))
            painter.drawEllipse(ox - 5, oy - 5, 10, 10)
            
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(ox + 10, oy + 5, f"{obj.class_name} ({obj.confidence:.2f})")
            
        painter.end()
        self.map_label.setPixmap(pixmap)
