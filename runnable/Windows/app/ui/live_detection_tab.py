"""
Live Detection Tab - Real-Time Vision & Physics-Fused ADAS Hazard System.

Features:
- YOLO object detection with distance-colored bounding boxes
- Perspective forward driving corridor with optical distance estimation
- Dynamic roadway physics: friction (mu), stopping distance, kinetic energy
- Tri-color virtual traffic signal (Green, Yellow, Red)
- Weather simulation slider and vehicle speed control
- Audio alerts, screenshot, video recording, dataset capture
"""

import os
import time
import subprocess
import platform
import threading
from datetime import datetime
from typing import Optional

import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QGroupBox, QTableWidget,
    QTableWidgetItem, QCheckBox, QPushButton, QHeaderView, QProgressBar,
    QFrame, QGridLayout, QSlider, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QFont

from core.collision_zone import CollisionZone
from core.inference_engine import InferenceResult
from core.dataset_manager import DatasetManager
from ui.theme import (
    SURFACE, SURFACE_2, SURFACE_3, HAIRLINE,
    TEXT, TEXT_2, TEXT_3, ACCENT,
    GREEN, YELLOW, RED, ORANGE, TEAL,
)


class LiveDetectionTab(QWidget):
    """Mode 2 Live Detection Tab with ADAS corridor and environmental physics."""

    def __init__(self, engine_ref):
        super().__init__()
        self.engine = engine_ref
        self.dataset_manager = DatasetManager()

        # Recording & Snapshot State
        self.is_recording = False
        self.video_writer = None
        self.video_filepath = ""
        self.record_start_time = 0.0
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_result: Optional[InferenceResult] = None

        # Toast notification state
        self.toast_message: str = ""
        self.toast_expires: float = 0.0

        # State tracking for signals and audio
        self.last_severity_was_high = False
        self.last_sound_time = 0.0
        self.sound_cooldown = 1.8

        # Vehicle Speed (km/h)
        self.current_speed_kmh: float = 50.0

        self.setup_ui()

        # Clock timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timestamp)
        self.timer.start(1000)

    # ------------------------------------------------------------------ #
    #  UI Construction
    # ------------------------------------------------------------------ #
    def setup_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # -- Video Feed --
        self.video_label = QLabel("Connecting to video stream")
        self.video_label.setObjectName("VideoPanel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet(
            "background-color: #000000; border: 1px solid " + HAIRLINE + ";"
            "border-radius: 12px; color: " + TEXT_3 + "; font-size: 13px;"
        )
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored
        )
        self.video_label.setMinimumSize(320, 240)
        root.addWidget(self.video_label, stretch=1)

        # -- Control Panel (fixed-width scrollable sidebar) --
        panel = QVBoxLayout()
        panel.setContentsMargins(0, 0, 0, 0)
        panel.setSpacing(10)

        panel.addWidget(self._build_signal_group())
        panel.addWidget(self._build_physics_group())
        panel.addWidget(self._build_corridor_group())
        panel.addWidget(self._build_counts_group())
        panel.addWidget(self._build_actions_group())
        panel.addStretch()

        control_container = QWidget()
        control_container.setLayout(panel)

        # Scroll area so the sidebar never clips, even on small windows
        scroll = QScrollArea()
        scroll.setWidget(control_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; }")
        scroll.setFixedWidth(370)
        root.addWidget(scroll)

    # ---- Signal HUD ----
    def _build_signal_group(self) -> QGroupBox:
        box = QGroupBox("Status")
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(8)

        lamp_row = QHBoxLayout()
        lamp_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lamp_row.setSpacing(16)

        self.lamp_red = QLabel()
        self.lamp_red.setFixedSize(16, 16)

        self.lamp_yellow = QLabel()
        self.lamp_yellow.setFixedSize(16, 16)

        self.lamp_green = QLabel()
        self.lamp_green.setFixedSize(16, 16)

        self._set_lamp_styles(False, False, True)

        for lmp in (self.lamp_red, self.lamp_yellow, self.lamp_green):
            lamp_row.addWidget(lmp)
        lay.addLayout(lamp_row)

        self.status_text = QLabel("SYSTEM ACTIVE - PATH CLEAR")
        self.status_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_text.setStyleSheet(
            f"color: {GREEN}; font-weight: 600; font-size: 12px;"
            f"background: #30D1581A; border-radius: 8px; padding: 8px;"
        )
        lay.addWidget(self.status_text)

        self.timestamp_label = QLabel(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.timestamp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timestamp_label.setStyleSheet(f"color: {TEXT_3}; font-size: 10px;")
        lay.addWidget(self.timestamp_label)

        box.setLayout(lay)
        return box

    def _set_lamp_styles(self, red_on: bool, yellow_on: bool, green_on: bool):
        off_style = f"background-color: {SURFACE_2}; border: 1px solid {HAIRLINE}; border-radius: 8px;"
        red_style = f"background-color: {RED}; border: 1px solid #FF6961; border-radius: 8px;"
        yellow_style = f"background-color: {YELLOW}; border: 1px solid #FFE156; border-radius: 8px;"
        green_style = f"background-color: {GREEN}; border: 1px solid #66E39C; border-radius: 8px;"

        self.lamp_red.setStyleSheet(red_style if red_on else off_style)
        self.lamp_yellow.setStyleSheet(yellow_style if yellow_on else off_style)
        self.lamp_green.setStyleSheet(green_style if green_on else off_style)

    # ---- Physics & Friction ----
    def _build_physics_group(self) -> QGroupBox:
        box = QGroupBox("Physics")
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(7)

        self.road_cond_label = QLabel("Road Condition: DRY (0.0% wet)")
        self.road_cond_label.setStyleSheet(f"font-weight: 600; font-size: 11px; color: {TEXT};")
        lay.addWidget(self.road_cond_label)

        # Friction bar
        fric_row = QHBoxLayout()
        fric_lbl = QLabel("Friction")
        fric_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_2};")
        fric_row.addWidget(fric_lbl)
        self.friction_bar = QProgressBar()
        self.friction_bar.setRange(0, 100)
        self.friction_bar.setValue(80)
        fric_row.addWidget(self.friction_bar)
        self.fric_val_label = QLabel("0.80")
        self.fric_val_label.setStyleSheet(f"font-size: 11px; color: {TEXT}; min-width: 34px;")
        self.fric_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        fric_row.addWidget(self.fric_val_label)
        lay.addLayout(fric_row)

        # Stopping multiplier bar
        stop_row = QHBoxLayout()
        stop_lbl = QLabel("Stopping")
        stop_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_2};")
        stop_row.addWidget(stop_lbl)
        self.stopping_dist_bar = QProgressBar()
        self.stopping_dist_bar.setRange(100, 250)
        self.stopping_dist_bar.setValue(100)
        stop_row.addWidget(self.stopping_dist_bar)
        self.stop_val_label = QLabel("1.0x")
        self.stop_val_label.setStyleSheet(f"font-size: 11px; color: {TEXT}; min-width: 34px;")
        self.stop_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        stop_row.addWidget(self.stop_val_label)
        lay.addLayout(stop_row)

        # Kinematic formula
        self.formula_label = QLabel("s = (13.9)^2 / (2*0.80*9.81) = 12.3m")
        self.formula_label.setStyleSheet(
            f"font-family: 'Menlo', 'SF Mono', 'Consolas', monospace; font-size: 10px;"
            f"background: {SURFACE_2}; border: 1px solid {HAIRLINE};"
            f"color: {TEAL}; padding: 6px 8px; border-radius: 8px;"
        )
        lay.addWidget(self.formula_label)

        self.ke_label = QLabel("Kinetic Energy (50 km/h): 144.7 kJ")
        self.ke_label.setStyleSheet(f"font-size: 10px; color: {TEXT_3};")
        lay.addWidget(self.ke_label)

        # Weather slider
        sim_row = QHBoxLayout()
        self.sim_checkbox = QCheckBox("Simulate Weather")
        self.sim_checkbox.setChecked(False)
        sim_row.addWidget(self.sim_checkbox)

        self.weather_slider = QSlider(Qt.Orientation.Horizontal)
        self.weather_slider.setRange(0, 100)
        self.weather_slider.setValue(0)
        self.weather_slider.setEnabled(False)
        self.sim_checkbox.toggled.connect(self.weather_slider.setEnabled)
        sim_row.addWidget(self.weather_slider)

        self.weather_slider_val = QLabel("0%")
        self.weather_slider_val.setStyleSheet(f"font-size: 11px; color: {TEXT}; min-width: 30px;")
        self.weather_slider_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        sim_row.addWidget(self.weather_slider_val)
        lay.addLayout(sim_row)

        # Speed slider
        speed_row = QHBoxLayout()
        spd_lbl = QLabel("Speed")
        spd_lbl.setStyleSheet(f"font-size: 11px; color: {TEXT_2};")
        speed_row.addWidget(spd_lbl)

        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(20, 100)
        self.speed_slider.setValue(50)
        self.speed_slider.valueChanged.connect(self.on_speed_changed)
        speed_row.addWidget(self.speed_slider)

        self.speed_val_label = QLabel("50 km/h")
        self.speed_val_label.setStyleSheet(f"font-size: 11px; color: {TEXT}; min-width: 52px;")
        self.speed_val_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        speed_row.addWidget(self.speed_val_label)
        lay.addLayout(speed_row)

        box.setLayout(lay)
        return box

    # ---- Corridor Telemetry ----
    def _build_corridor_group(self) -> QGroupBox:
        box = QGroupBox("Corridor")
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(6)

        def metric(label: str) -> QLabel:
            lab = QLabel(label)
            lab.setStyleSheet(f"font-size: 11px; color: {TEXT}; background: {SURFACE_2};"
                              f"border-radius: 6px; padding: 5px 8px;")
            return lab

        row1 = QHBoxLayout()
        self.tracked_count_label = metric("Tracked: 0")
        self.danger_count_label = metric("In Lane: 0")
        row1.addWidget(self.tracked_count_label)
        row1.addWidget(self.danger_count_label)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        self.nearest_dist_label = metric("Nearest: -- m")
        self.ttc_label = metric("TTC: -- s")
        row2.addWidget(self.nearest_dist_label)
        row2.addWidget(self.ttc_label)
        lay.addLayout(row2)

        self.approach_speed_label = metric("Approach: -- km/h")
        lay.addWidget(self.approach_speed_label)

        box.setLayout(lay)
        return box

    # ---- Object Counts ----
    def _build_counts_group(self) -> QGroupBox:
        box = QGroupBox("Objects")
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(4)

        self.counts_table = QTableWidget(0, 2)
        self.counts_table.setHorizontalHeaderLabels(["Class", "Count"])
        self.counts_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.counts_table.verticalHeader().setVisible(False)
        self.counts_table.verticalHeader().setDefaultSectionSize(26)
        self.counts_table.setMaximumHeight(130)
        self.counts_table.setStyleSheet(
            "QTableWidget { border: none; border-radius: 8px; }"
        )
        lay.addWidget(self.counts_table)

        box.setLayout(lay)
        return box

    # ---- Actions & Controls ----
    def _build_actions_group(self) -> QGroupBox:
        box = QGroupBox("Actions")
        lay = QVBoxLayout()
        lay.setContentsMargins(8, 14, 8, 8)
        lay.setSpacing(8)

        btn_row = QHBoxLayout()
        self.record_btn = QPushButton("Record")
        self.record_btn.clicked.connect(self.toggle_recording)

        self.screenshot_btn = QPushButton("Snapshot")
        self.screenshot_btn.clicked.connect(self.take_screenshot)

        self.capture_dataset_btn = QPushButton("Capture (C)")
        self.capture_dataset_btn.setObjectName("Primary")
        self.capture_dataset_btn.clicked.connect(self.capture_dataset_frame)

        btn_row.addWidget(self.record_btn)
        btn_row.addWidget(self.screenshot_btn)
        btn_row.addWidget(self.capture_dataset_btn)
        lay.addLayout(btn_row)

        opt_row = QHBoxLayout()
        self.zone_checkbox = QCheckBox("Driving Corridor")
        self.zone_checkbox.setChecked(True)

        self.audio_checkbox = QCheckBox("Audio Alert")
        self.audio_checkbox.setChecked(True)

        opt_row.addWidget(self.zone_checkbox)
        opt_row.addWidget(self.audio_checkbox)
        lay.addLayout(opt_row)

        # Hardware LED Diagnostic Test Bar
        hw_row = QHBoxLayout()
        hw_lbl = QLabel("LED Test")
        hw_lbl.setStyleSheet(f"font-size: 10px; color: {TEXT_3};")
        hw_row.addWidget(hw_lbl)

        self.btn_led_red = QPushButton("Red")
        self.btn_led_yellow = QPushButton("Yellow")
        self.btn_led_green = QPushButton("Green")
        self.btn_led_all = QPushButton("All")

        self.btn_led_red.setStyleSheet(f"font-size: 10px; padding: 3px 8px; color: {RED};")
        self.btn_led_yellow.setStyleSheet(f"font-size: 10px; padding: 3px 8px; color: {YELLOW};")
        self.btn_led_green.setStyleSheet(f"font-size: 10px; padding: 3px 8px; color: {GREEN};")

        for b in (self.btn_led_red, self.btn_led_yellow, self.btn_led_green, self.btn_led_all):
            hw_row.addWidget(b)
        lay.addLayout(hw_row)

        self.btn_led_red.clicked.connect(lambda: self.trigger_manual_led("RED"))
        self.btn_led_yellow.clicked.connect(lambda: self.trigger_manual_led("YELLOW"))
        self.btn_led_green.clicked.connect(lambda: self.trigger_manual_led("GREEN"))
        self.btn_led_all.clicked.connect(lambda: self.trigger_manual_led("ALL_ON"))

        self.polarity_checkbox = QCheckBox("Invert Polarity (Active-Low Module)")
        self.polarity_checkbox.setStyleSheet(f"font-size: 10px; color: {TEXT_3};")
        self.polarity_checkbox.toggled.connect(self.on_polarity_toggled)
        lay.addWidget(self.polarity_checkbox)

        box.setLayout(lay)
        return box

    def trigger_manual_led(self, signal: str):
        if hasattr(self, '_arduino_ref') and self._arduino_ref:
            self._arduino_ref.send_signal(signal)
            self.show_toast(f"Hardware Signal: {signal}")

    def on_polarity_toggled(self, checked: bool):
        if hasattr(self, '_arduino_ref') and self._arduino_ref:
            self._arduino_ref.set_inverted_polarity(checked)
            self.show_toast("LED Polarity: Inverted" if checked else "LED Polarity: Normal")

    # ------------------------------------------------------------------ #
    #  Helpers
    # ------------------------------------------------------------------ #
    def set_weather_preset(self, val: int):
        self.weather_slider.setValue(val)

    def on_speed_changed(self, val: int):
        self.current_speed_kmh = float(val)
        self.speed_val_label.setText(f"{val} km/h")

    def update_timestamp(self):
        self.timestamp_label.setText(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def toggle_recording(self):
        if not self.is_recording:
            os.makedirs("recordings", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.video_filepath = f"recordings/recording_{ts}.mp4"
            self.is_recording = True
            self.record_start_time = time.time()
            self.record_btn.setText("Stop")
            self.record_btn.setStyleSheet(
                f"color: {RED}; font-weight: 600;"
                f"background: #FF453A22; border: 1px solid #FF453A55;"
            )
            self.show_toast("Recording Started")
        else:
            self.is_recording = False
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
            self.record_btn.setText("Record")
            self.record_btn.setStyleSheet("")
            self.show_toast(f"Saved: {os.path.basename(self.video_filepath)}")

    def take_screenshot(self):
        if self._latest_frame is not None:
            os.makedirs("screenshots", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = f"screenshots/screenshot_{ts}.jpg"
            cv2.imwrite(path, self._latest_frame)
            self.show_toast(f"Screenshot: {os.path.basename(path)}")

    def capture_dataset_frame(self):
        if self._latest_frame is not None and self._latest_result is not None:
            saved_path = self.dataset_manager.capture_frame(self._latest_frame, self._latest_result.detections)
            self.show_toast(f"Dataset Frame: {os.path.basename(saved_path)}")

    def show_toast(self, message: str, duration: float = 2.5):
        self.toast_message = message
        self.toast_expires = time.time() + duration

    def _play_alert_sound(self):
        """Cross-platform non-blocking audio alert."""
        if not self.audio_checkbox.isChecked():
            return
        now = time.time()
        if now - self.last_sound_time < self.sound_cooldown:
            return
        self.last_sound_time = now

        def _sound():
            try:
                system = platform.system()
                if system == "Darwin":
                    sound_file = "/System/Library/Sounds/Sosumi.aiff"
                    if not os.path.exists(sound_file):
                        sound_file = "/System/Library/Sounds/Ping.aiff"
                    subprocess.run(["afplay", sound_file], timeout=1.0)
                elif system == "Windows":
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                else:
                    print('\a', end='', flush=True)
            except Exception:
                pass

        threading.Thread(target=_sound, daemon=True).start()

    # ------------------------------------------------------------------ #
    #  Main Display Update  (logic unchanged)
    # ------------------------------------------------------------------ #
    def update_display(self, frame: np.ndarray, result: InferenceResult, collision_zone: CollisionZone, arduino_bridge=None):
        self._arduino_ref = arduino_bridge
        self._latest_frame = frame.copy()
        self._latest_result = result

        disp_frame = frame.copy()
        h, w = disp_frame.shape[:2]

        # 1. Update Physics / Environmental State
        sim_val = self.weather_slider.value()
        self.weather_slider_val.setText(f"{sim_val}%")

        if arduino_bridge:
            # Sync simulation override
            if self.sim_checkbox.isChecked():
                arduino_bridge.set_simulation_override(True, float(sim_val))
            else:
                arduino_bridge.set_simulation_override(False)

            summary = arduino_bridge.get_physics_summary(speed_kmh=self.current_speed_kmh)
            stopping_multiplier = summary["stopping_dist_multiplier"]
            friction_mu = summary["friction_mu"]

            adc_info = f" [ADC: {arduino_bridge.raw_rain_adc}]" if (arduino_bridge.is_connected and not self.sim_checkbox.isChecked()) else ""
            self.road_cond_label.setText(f"Road: {summary['road_condition']} ({summary['wetness_percent']}%) {adc_info}")

            # Update friction bar
            fval = int(friction_mu * 100)
            self.friction_bar.setValue(fval)
            self.fric_val_label.setText(f"{friction_mu:.2f}")
            if friction_mu > 0.6:
                self.friction_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {GREEN}; }}")
            elif friction_mu > 0.4:
                self.friction_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {YELLOW}; }}")
            else:
                self.friction_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {RED}; }}")

            # Update stopping multiplier bar
            sval = int(stopping_multiplier * 100)
            self.stopping_dist_bar.setValue(min(250, sval))
            self.stop_val_label.setText(f"{stopping_multiplier:.1f}x")
            if stopping_multiplier < 1.3:
                self.stopping_dist_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {GREEN}; }}")
            elif stopping_multiplier < 1.9:
                self.stopping_dist_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {YELLOW}; }}")
            else:
                self.stopping_dist_bar.setStyleSheet(f"QProgressBar::chunk {{ background-color: {RED}; }}")

            # Dynamic kinematic calculations
            self.formula_label.setText(summary["formula_text"])
            self.ke_label.setText(f"Kinetic Energy ({self.current_speed_kmh:.0f} km/h): {summary['kinetic_energy_kj']:.1f} kJ")
        else:
            stopping_multiplier = 1.0
            friction_mu = 0.80

        # 2. Collision Corridor Check
        alerts = []
        if self.zone_checkbox.isChecked():
            alerts = collision_zone.check_hazards(result.detections, disp_frame.shape, stopping_multiplier=stopping_multiplier)
            disp_frame = collision_zone.draw_zone(disp_frame, alerts, stopping_multiplier=stopping_multiplier, friction_mu=friction_mu)

        current_high = any(a.severity == "HIGH" for a in alerts)
        current_medium = any(a.severity in ("MEDIUM", "LOW") for a in alerts)

        # 3. Update Visual Tri-Color Signal Lamps
        if current_high:
            self._set_lamp_styles(True, False, False)
            self.status_text.setText("EMERGENCY BRAKE - STOP")
            self.status_text.setStyleSheet(
                f"background-color: #FF453A33; color: {RED}; font-weight: 700; font-size: 12px;"
                f"padding: 8px; border-radius: 8px;"
            )

            if arduino_bridge:
                arduino_bridge.send_signal("RED")

            if not self.last_severity_was_high:
                self._play_alert_sound()
        elif current_medium:
            self._set_lamp_styles(False, True, False)
            self.status_text.setText("CAUTION - HAZARD IN PATH")
            self.status_text.setStyleSheet(
                f"background-color: #FFD60A26; color: {YELLOW}; font-weight: 600; font-size: 12px;"
                f"padding: 8px; border-radius: 8px;"
            )

            if arduino_bridge:
                arduino_bridge.send_signal("YELLOW")
        else:
            self._set_lamp_styles(False, False, True)
            self.status_text.setText("SYSTEM ACTIVE - LANE CLEAR")
            self.status_text.setStyleSheet(
                f"background-color: #30D1581A; color: {GREEN}; font-weight: 600; font-size: 12px;"
                f"padding: 8px; border-radius: 8px;"
            )

            if arduino_bridge:
                arduino_bridge.send_signal("GREEN")

        self.last_severity_was_high = current_high

        # 4. Draw Distance-Coded Bounding Boxes
        alert_bboxes = set(a.bbox for a in alerts)
        for det in result.detections:
            if det.bbox in alert_bboxes:
                continue

            dist_m = collision_zone.estimate_distance(det.class_name, det.bbox[3] - det.bbox[1], w)
            if dist_m < 5.0:
                box_color = (58, 69, 255)     # Apple Red #FF453A: <5m
            elif dist_m < 15.0:
                box_color = (10, 214, 255)    # Apple Yellow #FFD60A: 5-15m
            else:
                box_color = (88, 209, 48)     # Apple Green #30D158: >15m

            x1, y1, x2, y2 = det.bbox
            cv2.rectangle(disp_frame, (x1, y1), (x2, y2), box_color, 2)
            lbl = f"{det.class_name} {dist_m:.1f}m"
            cv2.putText(disp_frame, lbl, (x1, max(18, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, box_color, 2)

        # 5. Collision Status Summary
        status = collision_zone.get_status_summary()
        self.tracked_count_label.setText(f"Tracked: {status['total_tracked']}")
        self.danger_count_label.setText(f"In Lane: {status['objects_in_lane']}")
        if status['closest_distance_m'] < 999:
            self.nearest_dist_label.setText(f"Nearest: {status['closest_distance_m']:.1f}m")
        else:
            self.nearest_dist_label.setText("Nearest: -- m")
        if status['closest_ttc_s'] < 999:
            self.ttc_label.setText(f"TTC: {status['closest_ttc_s']:.1f}s")
        else:
            self.ttc_label.setText("TTC: -- s")
        self.approach_speed_label.setText(f"Max Approach: {status['approach_speed_kmh']:.1f} km/h")

        # 6. Toast Notification Banner
        if time.time() < self.toast_expires and self.toast_message:
            tw = len(self.toast_message) * 11 + 30
            cv2.rectangle(disp_frame, (w // 2 - tw // 2, h - 55), (w // 2 + tw // 2, h - 18), (30, 28, 26), -1)
            cv2.rectangle(disp_frame, (w // 2 - tw // 2, h - 55), (w // 2 + tw // 2, h - 18), (60, 58, 56), 1)
            cv2.putText(disp_frame, self.toast_message, (w // 2 - tw // 2 + 15, h - 28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (245, 245, 245), 2)

        # 8. Recording Output
        if self.is_recording:
            dur = time.time() - self.record_start_time
            rec_text = f"REC {int(dur // 60):02d}:{int(dur % 60):02d}"
            cv2.circle(disp_frame, (w - 120, 20), 8, (0, 0, 255), -1)
            cv2.putText(disp_frame, rec_text, (w - 100, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if self.video_writer is None:
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                self.video_writer = cv2.VideoWriter(self.video_filepath, fourcc, 30.0, (w, h))
            self.video_writer.write(disp_frame)

        # 9. Render to PyQt Widget
        disp_frame_rgb = cv2.cvtColor(disp_frame, cv2.COLOR_BGR2RGB)
        ch = 3
        bytes_per_line = ch * w
        qimg = QImage(disp_frame_rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        lbl_size = self.video_label.size()
        if lbl_size.width() > 10 and lbl_size.height() > 10:
            scaled_pixmap = pixmap.scaled(lbl_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.video_label.setPixmap(scaled_pixmap)

        # 10. Update Classification Counts Table
        counts = result.count_by_class
        self.counts_table.setRowCount(len(counts))
        for row, (cls_name, count) in enumerate(counts.items()):
            self.counts_table.setItem(row, 0, QTableWidgetItem(cls_name.capitalize()))
            self.counts_table.setItem(row, 1, QTableWidgetItem(str(count)))
