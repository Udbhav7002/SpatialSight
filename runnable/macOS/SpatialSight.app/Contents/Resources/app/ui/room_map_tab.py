"""
Room Map Tab - Sensor-guided spatial room mapping with angular deduplication.

Provides live camera feed, 2D polar radar, three input modes
(auto sweep / phone USB / manual slider), keyframe capture,
spatially-deduplicated inventory, and one-click report export.
"""

import time
import os
from datetime import datetime
import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox, QPushButton,
    QProgressBar, QTableWidget, QTableWidgetItem, QSpinBox, QHeaderView,
    QRadioButton, QButtonGroup, QSlider, QMessageBox, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap

from spatial.keyframe_selector import KeyframeSelector, SensorData
from spatial.angular_dedup import AngularDeduplicator
from spatial.room_map_renderer import RoomMapRenderer
from core import adb_bridge
from ui.theme import (
    SURFACE_2, HAIRLINE, TEXT, TEXT_2, TEXT_3, ACCENT,
    GREEN, YELLOW, RED, TEAL,
)


class RoomMapTab(QWidget):
    """PyQt6 Tab for Mode 1: Spatial Room Mapping and Deduplication."""

    def __init__(self, engine_ref):
        super().__init__()
        self.engine = engine_ref

        self.selector = KeyframeSelector(yaw_threshold=30.0, pitch_threshold=20.0)
        self.dedup = AngularDeduplicator(merge_threshold=35.0)
        self.renderer = RoomMapRenderer(size=560, radius=210)

        # Angle / simulation state
        self.current_yaw: float = 0.0
        self.current_pitch: float = 0.0
        self.sim_speed_deg_per_sec: float = 24.0
        self.last_sim_tick: float = time.time()
        self.sweep_accumulated_deg: float = 0.0

        # Background ADB sensor reader
        self.sensor_worker = adb_bridge.SensorStreamWorker()
        self.sensor_worker.start()

        self._last_raw_frame = None

        self.setup_ui()

    # ------------------------------------------------------------------ UI --
    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # -- LEFT PANE -------------------------------------------------
        left = QVBoxLayout()
        left.setSpacing(8)

        lbl = QLabel("Camera Feed")
        lbl.setObjectName("SectionTitle")
        left.addWidget(lbl)

        self.camera_label = QLabel("Initializing Camera...")
        self.camera_label.setObjectName("VideoPanel")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setStyleSheet(
            "background-color:#000000;border:1px solid " + HAIRLINE + ";"
            "border-radius:12px;color:" + TEXT_3 + ";font-size:13px;"
        )
        self.camera_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        self.camera_label.setMinimumSize(240, 180)
        left.addWidget(self.camera_label, stretch=4)

        # Telemetry HUD
        hud = QFrame()
        hud.setStyleSheet(f"background:{SURFACE_2};border-radius:8px;")
        hud_lay = QHBoxLayout(hud)
        hud_lay.setContentsMargins(10, 6, 10, 6)

        self.telemetry_label = QLabel("Yaw: 0.0 deg | Pitch: 0.0 deg | Mode: Auto Sweep")
        self.telemetry_label.setStyleSheet(
            f"color:{TEAL};font-family:'Menlo','SF Mono','Consolas',monospace;"
            f"font-size:10px;font-weight:600;"
        )
        hud_lay.addWidget(self.telemetry_label)
        hud_lay.addStretch()

        self.kf_badge = QLabel("Keyframes: 0")
        self.kf_badge.setStyleSheet(f"color:{GREEN};font-weight:600;font-size:10px;")
        hud_lay.addWidget(self.kf_badge)
        left.addWidget(hud)

        # Coverage bar
        cov = QHBoxLayout()
        cov.setSpacing(8)
        cov_lbl = QLabel("Coverage")
        cov_lbl.setStyleSheet(f"font-size:11px;color:{TEXT_2};")
        cov.addWidget(cov_lbl)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet(
            f"QProgressBar::chunk{{background:{GREEN};}}"
        )
        cov.addWidget(self.progress_bar)
        self.cov_pct_label = QLabel("0%")
        self.cov_pct_label.setStyleSheet(f"font-size:11px;color:{TEXT};min-width:32px;")
        self.cov_pct_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        cov.addWidget(self.cov_pct_label)
        left.addLayout(cov)

        # Inventory table
        inv_group = QGroupBox("Inventory")
        inv_lay = QVBoxLayout(inv_group)
        inv_lay.setContentsMargins(8, 12, 8, 8)
        self.inventory_table = QTableWidget(0, 3)
        self.inventory_table.setHorizontalHeaderLabels(
            ["Object", "Count", "Direction"]
        )
        self.inventory_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.inventory_table.verticalHeader().setVisible(False)
        self.inventory_table.verticalHeader().setDefaultSectionSize(26)
        self.inventory_table.setStyleSheet(
            "QTableWidget { border: none; border-radius: 8px; }"
        )
        inv_lay.addWidget(self.inventory_table)
        left.addWidget(inv_group, stretch=3)

        root.addLayout(left, stretch=5)

        # -- RIGHT PANE ------------------------------------------------
        right = QVBoxLayout()
        right.setSpacing(8)

        rlbl = QLabel("Polar Radar")
        rlbl.setObjectName("SectionTitle")
        right.addWidget(rlbl)

        self.radar_label = QLabel("Polar Radar Ready")
        self.radar_label.setObjectName("VideoPanel")
        self.radar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.radar_label.setStyleSheet(
            "background-color:#0B0B0D;border:1px solid " + HAIRLINE + ";"
            "border-radius:12px;color:" + TEXT_3 + ";font-size:13px;"
        )
        self.radar_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        self.radar_label.setMinimumSize(240, 240)
        right.addWidget(self.radar_label, stretch=5)

        # Controls group
        ctrl = QGroupBox("Controls")
        cl = QVBoxLayout(ctrl)
        cl.setContentsMargins(10, 14, 10, 10)
        cl.setSpacing(8)

        # Mode selector - single horizontal row
        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self.radio_auto = QRadioButton("Auto Sweep")
        self.radio_phone = QRadioButton("Phone USB")
        self.radio_manual = QRadioButton("Manual Dial")
        self.radio_auto.setChecked(True)

        self.mode_group = QButtonGroup(self)
        for idx, btn in enumerate(
            (self.radio_auto, self.radio_phone, self.radio_manual)
        ):
            self.mode_group.addButton(btn, idx)
            mode_row.addWidget(btn)
        self.mode_group.idClicked.connect(self.on_mode_changed)
        cl.addLayout(mode_row)

        # Manual slider
        sl_row = QHBoxLayout()
        sl_row.setSpacing(8)
        self.manual_slider_label = QLabel("0 deg")
        self.manual_slider_label.setStyleSheet(f"font-size:11px;color:{TEXT};min-width:46px;")
        self.manual_slider_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.manual_slider = QSlider(Qt.Orientation.Horizontal)
        self.manual_slider.setRange(0, 360)
        self.manual_slider.setValue(0)
        self.manual_slider.setEnabled(False)
        self.manual_slider.valueChanged.connect(self.on_manual_slider_changed)
        sl_row.addWidget(self.manual_slider_label)
        sl_row.addWidget(self.manual_slider)
        cl.addLayout(sl_row)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self.start_btn = QPushButton("Start Scan")
        self.start_btn.setObjectName("Primary")
        self.start_btn.clicked.connect(self.start_scan)

        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("Danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scan)

        self.export_btn = QPushButton("Export")
        self.export_btn.clicked.connect(self.export_inventory_report)

        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addWidget(self.export_btn)
        cl.addLayout(btn_row)

        # Keyframe threshold + merge threshold
        th_row = QHBoxLayout()
        th_lbl = QLabel("Keyframe Trigger")
        th_lbl.setStyleSheet(f"font-size:11px;color:{TEXT_2};")
        th_row.addWidget(th_lbl)
        th_row.addStretch()
        self.yaw_spinbox = QSpinBox()
        self.yaw_spinbox.setRange(15, 60)
        self.yaw_spinbox.setValue(30)
        self.yaw_spinbox.setSuffix(" deg")
        self.yaw_spinbox.setFixedWidth(90)
        self.yaw_spinbox.valueChanged.connect(
            lambda v: setattr(self.selector, "yaw_threshold", float(v))
        )
        th_row.addWidget(self.yaw_spinbox)
        cl.addLayout(th_row)

        mg_row = QHBoxLayout()
        mg_lbl = QLabel("Merge Angle")
        mg_lbl.setStyleSheet(f"font-size:11px;color:{TEXT_2};")
        mg_row.addWidget(mg_lbl)
        mg_row.addStretch()
        self.merge_spinbox = QSpinBox()
        self.merge_spinbox.setRange(5, 60)
        self.merge_spinbox.setValue(35)
        self.merge_spinbox.setSuffix(" deg")
        self.merge_spinbox.setFixedWidth(90)
        self.merge_spinbox.valueChanged.connect(
            lambda v: setattr(self.dedup, "merge_threshold", float(v))
        )
        mg_row.addWidget(self.merge_spinbox)
        cl.addLayout(mg_row)

        # Tip: explains what Auto Sweep does with a fixed webcam
        tip = QLabel(
            "Tip: Auto Sweep simulates rotation, so a fixed webcam smears one "
            "object across angles. For a real room scan, connect your phone "
            "and walk around (Phone USB)."
        )
        tip.setWordWrap(True)
        tip.setStyleSheet(f"font-size:10px;color:{TEXT_3};")
        cl.addWidget(tip)

        right.addWidget(ctrl, stretch=3)
        root.addLayout(right, stretch=5)

        # Draw initial blank radar
        self.render_radar()

    # ----------------------------------------------------------- callbacks --
    def on_mode_changed(self, mode_id: int):
        self.manual_slider.setEnabled(mode_id == 2)
        if mode_id == 1:
            status = adb_bridge.get_phone_status()
            if status["state"] == "device":
                adb_bridge.setup_port_forward()
                self.telemetry_label.setText(f"Connected: {status['serial']}")
            elif status["state"] == "unauthorized":
                self.telemetry_label.setText(
                    "Phone unauthorized. Tap 'Allow' on phone screen."
                )
            else:
                self.telemetry_label.setText(
                    "Phone not detected. Connect USB & start app."
                )
                adb_bridge.setup_port_forward()

    def on_manual_slider_changed(self, val: int):
        self.manual_slider_label.setText(f"Angle: {val} deg")
        self.current_yaw = float(val)

    # --------------------------------------------------------- scan logic --
    def start_scan(self):
        self.selector.start_scan()
        self.dedup.reset()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.inventory_table.setRowCount(0)
        self.sweep_accumulated_deg = 0.0
        self.progress_bar.setValue(0)
        self.kf_badge.setText("Keyframes: 0")

        if self.radio_auto.isChecked():
            self.current_yaw = 0.0
        self.last_sim_tick = time.time()

    def stop_scan(self):
        self.selector.stop_scan()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.populate_inventory()
        self.render_radar()

    def get_effective_sensor_data(self) -> SensorData:
        now = time.time()

        if self.radio_phone.isChecked():
            phone_data = self.sensor_worker.get_latest_sensor()
            if phone_data and "yaw" in phone_data:
                self.current_yaw = float(phone_data["yaw"])
                self.current_pitch = float(phone_data.get("pitch", 0.0))
                return SensorData(
                    yaw=self.current_yaw,
                    pitch=self.current_pitch,
                    roll=0.0,
                    timestamp=now,
                )

        if self.radio_manual.isChecked():
            return SensorData(
                yaw=self.current_yaw,
                pitch=self.current_pitch,
                roll=0.0,
                timestamp=now,
            )

        # Auto sweep - smooth clockwise rotation
        dt = now - self.last_sim_tick
        self.last_sim_tick = now
        if self.selector.is_scanning:
            self.current_yaw = (
                self.current_yaw + self.sim_speed_deg_per_sec * dt
            ) % 360.0
            self.sweep_accumulated_deg += self.sim_speed_deg_per_sec * dt
            if self.sweep_accumulated_deg >= 360.0:
                self.stop_scan()

        return SensorData(yaw=self.current_yaw, pitch=0.0, roll=0.0, timestamp=now)

    # --------------------------------------------------- frame pipeline --
    def update_display(self, frame: np.ndarray):
        self._last_raw_frame = frame.copy()
        sensor_data = self.get_effective_sensor_data()

        # Telemetry HUD
        mode_name = (
            "Auto Sweep"
            if self.radio_auto.isChecked()
            else ("Phone Sensor" if self.radio_phone.isChecked() else "Manual Dial")
        )
        self.telemetry_label.setText(
            f"Yaw: {sensor_data.yaw:5.1f} deg | Pitch: {sensor_data.pitch:4.1f} deg | Mode: {mode_name}"
        )

        disp_cam = frame.copy()
        h, w = disp_cam.shape[:2]

        if self.selector.is_scanning:
            if self.selector.should_capture(sensor_data):
                kf = self.selector.capture(frame, sensor_data)

                result = self.engine.infer(frame)
                kf.detections = result.detections

                for det in result.detections:
                    world_angle = self.selector.estimate_object_world_angle(
                        kf, det.center[0], w
                    )
                    self.dedup.add_detection(
                        det.class_name, world_angle, det.confidence, kf.index
                    )

                self.kf_badge.setText(f"Keyframes: {self.selector.keyframe_count}")
                self.populate_inventory()

                cv2.rectangle(disp_cam, (0, 0), (w, h), (88, 209, 48), 6)
                cv2.putText(
                    disp_cam,
                    f"KEYFRAME #{kf.index} CAPTURED AT {sensor_data.yaw:.0f} DEG",
                    (20, 50),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.75,
                    (88, 209, 48),
                    2,
                )

            cov = self.selector.get_coverage_percentage()
            self.progress_bar.setValue(int(cov))
            self.cov_pct_label.setText(f"{cov:.0f}%")

        # Compass crosshair
        cx, cy = w // 2, h // 2
        cv2.drawMarker(disp_cam, (cx, cy), (0, 220, 255), cv2.MARKER_CROSS, 20, 1)

        self.show_frame(disp_cam, self.camera_label)
        self.render_radar()

    # ------------------------------------------------------------ radar --
    def render_radar(self):
        keyframes = self.selector.get_all_keyframes()
        objects = self.dedup.get_unique_objects()
        cov_pct = self.selector.get_coverage_percentage()

        radar_img = self.renderer.render(
            keyframes=keyframes,
            spatial_objects=objects,
            coverage_pct=cov_pct,
            current_yaw=self.current_yaw,
            is_scanning=self.selector.is_scanning,
        )
        self.show_frame(radar_img, self.radar_label)

    # --------------------------------------------------------- inventory --
    def populate_inventory(self):
        inventory = self.dedup.get_inventory()
        objects = self.dedup.get_unique_objects()

        self.inventory_table.setRowCount(len(inventory))
        for row, (cls_name, count) in enumerate(inventory.items()):
            objs = [o for o in objects if o.class_name == cls_name]
            bearing = ", ".join(f"{int(o.world_angle)} deg" for o in objs[:4])
            if len(objs) > 4:
                bearing += "..."

            self.inventory_table.setItem(
                row, 0, QTableWidgetItem(cls_name.capitalize())
            )
            self.inventory_table.setItem(
                row, 1, QTableWidgetItem(f"{count} unique")
            )
            self.inventory_table.setItem(row, 2, QTableWidgetItem(bearing))

    def export_inventory_report(self):
        """Export room inventory to a timestamped text report."""
        summary = self.dedup.get_summary()
        kf_count = self.selector.keyframe_count
        cov = self.selector.get_coverage_percentage()

        os.makedirs("reports", exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = f"reports/room_inventory_{ts}.txt"

        with open(report_path, "w") as f:
            f.write("SPATIALSIGHT - SENSOR-GUIDED ROOM SCAN REPORT\n")
            f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Keyframes Captured: {kf_count}\n")
            f.write(f"Angular Coverage: {cov:.1f}%\n\n")
            f.write(summary)
            f.write("\n\nDETAILED OBJECT BEARINGS:\n")
            for obj in self.dedup.get_unique_objects():
                f.write(
                    f"  - {obj.class_name.capitalize():<15} "
                    f"Azimuth: {obj.world_angle:5.1f} deg | "
                    f"Sightings: {obj.sighting_count} | "
                    f"Confidence: {obj.confidence:.2f}\n"
                )

        QMessageBox.information(
            self,
            "Inventory Exported",
            f"Report saved to:\n{os.path.abspath(report_path)}",
        )

    # ----------------------------------------------------------- helpers --
    def show_frame(self, frame: np.ndarray, label_widget: QLabel):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        lbl_size = label_widget.size()
        if lbl_size.width() > 10 and lbl_size.height() > 10:
            scaled = pixmap.scaled(
                lbl_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            label_widget.setPixmap(scaled)

    def closeEvent(self, event):
        self.sensor_worker.stop()
        super().closeEvent(event)
