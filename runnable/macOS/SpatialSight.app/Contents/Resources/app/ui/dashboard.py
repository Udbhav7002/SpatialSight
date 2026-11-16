"""
SpatialSight Desktop Dashboard - Unified Rebuilt UI (Mac & Windows).

Follows exact design specifications from PDF:
- Screen 1: Minimal Start View with central [START] button and auto-connect flow.
- Screen 2: Tesla-Style Customer Detection View:
    - Top Bar: Phone connection dot, [ ] Sound checkbox, "Spatial Sight" center title.
    - Main Feed: Massive central video feed with Tesla vector bounding boxes (#E5CD82).
    - Right Sidebar: Dynamic "Objects" list showing ONLY objects in front of the camera,
      plus large [STOP] button at the bottom.
- Color Palette: #15370D (background), #1E4714 (panels), #E5CD82 (brass borders & accents), #FFF2B4 (headers & text).
- Firmware: Arduino cycles Red -> Yellow -> Green sequentially when waiting/no phone;
  Green ON on clear path; Yellow ON on caution hazard; Red ON (0ms) on imminent hazard.
- Audio: Dual-stage sound alert (caution < 10m chime, emergency < 5m rapid tone).
- Zero emojis across the entire UI.
"""

import sys
import os
import time
import logging
from typing import Union, Dict, Any, Optional

import cv2
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QCheckBox, QFrame, QScrollArea,
    QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QPainter, QColor

from core.frame_buffer import FrameBuffer
from core.inference_engine import InferenceEngine, InferenceResult
from core.arduino_bridge import ArduinoBridge
from core import adb_bridge
from core.categories import TARGET_CATEGORIES

from ui.theme import (
    GLOBAL_STYLESHEET, BG, SURFACE, SURFACE_HOVER, SURFACE_DARK,
    BORDER, BORDER_MUTED, TEXT, TEXT_MUTED, GREEN, YELLOW, RED,
    pill
)
from ui.sound_controller import SoundController
from ui.detection_renderer import DetectionRenderer
from ui.connect_modal import ConnectPhoneDialog

logger = logging.getLogger("SpatialSight")


# ============================================================================ #
#  Screen 1: Minimal Start View (PDF Page 1)                                   #
# ============================================================================ #
class StartScreen(QWidget):
    """Minimalist landing screen with central [START] button."""

    def __init__(self, on_start_callback, parent=None):
        super().__init__(parent)
        self.on_start_callback = on_start_callback
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center Container
        center_box = QVBoxLayout()
        center_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_box.setSpacing(28)

        # Title
        title = QLabel("Spatial Sight")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            color: {TEXT};
            font-size: 38px;
            font-weight: 800;
            letter-spacing: 2.5px;
        """)
        center_box.addWidget(title)

        # Subtitle
        sub = QLabel("Autonomous Forward Perception System")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 14px;
            font-weight: 500;
            letter-spacing: 1px;
        """)
        center_box.addWidget(sub)

        # Spacer
        center_box.addSpacing(16)

        # Large START Button (PDF Page 1 mockup)
        self.btn_start = QPushButton("START")
        self.btn_start.setObjectName("StartHeroButton")
        self.btn_start.setFixedSize(260, 72)
        self.btn_start.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_start.clicked.connect(self.on_start_callback)
        center_box.addWidget(self.btn_start)

        # Status note
        self.lbl_status = QLabel("Connect phone via USB-C or tap START to begin")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 12px;
            margin-top: 8px;
        """)
        center_box.addWidget(self.lbl_status)

        root.addLayout(center_box)

    def set_status(self, text: str):
        self.lbl_status.setText(text)


# ============================================================================ #
#  Screen 2: Tesla-Style Customer Detection View (PDF Page 2)                  #
# ============================================================================ #
class DetectionScreen(QWidget):
    """Tesla-style main feed with live dynamic object sidebar."""

    def __init__(self, on_stop_callback, parent=None):
        super().__init__(parent)
        self.on_stop_callback = on_stop_callback
        self._row_cache: Dict[str, Any] = {}
        self._empty_label: Optional[QLabel] = None
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 16)
        root.setSpacing(12)

        # ---------------- Top Bar ----------------
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(4, 0, 4, 0)
        top_bar.setSpacing(14)

        # Left: Phone connection indicator with circular dot
        phone_box = QHBoxLayout()
        phone_box.setSpacing(8)

        self.dot_indicator = QLabel()
        self.dot_indicator.setFixedSize(12, 12)
        self.set_phone_connected(False)
        phone_box.addWidget(self.dot_indicator)

        self.lbl_phone = QLabel("Phone")
        self.lbl_phone.setStyleSheet(f"color: {TEXT}; font-size: 14px; font-weight: 600;")
        phone_box.addWidget(self.lbl_phone)
        top_bar.addLayout(phone_box)

        # Subtle divider |
        div1 = QFrame()
        div1.setFrameShape(QFrame.Shape.VLine)
        div1.setStyleSheet(f"background-color: {BORDER_MUTED}; width: 1px; border: none; margin: 4px 4px;")
        top_bar.addWidget(div1)

        # Sound toggle checkbox
        self.chk_sound = QCheckBox("Sound")
        self.chk_sound.setCursor(Qt.CursorShape.PointingHandCursor)
        top_bar.addWidget(self.chk_sound)

        # Subtle divider |
        div2 = QFrame()
        div2.setFrameShape(QFrame.Shape.VLine)
        div2.setStyleSheet(f"background-color: {BORDER_MUTED}; width: 1px; border: none; margin: 4px 4px;")
        top_bar.addWidget(div2)

        # Water Sensor Road Status Indicator (Rule 1)
        self.lbl_water_status = QLabel("Dry")
        self.lbl_water_status.setStyleSheet(f"""
            background-color: {SURFACE_DARK};
            color: {TEXT_MUTED};
            border-radius: 6px;
            padding: 3px 8px;
            font-size: 11px;
            font-weight: 600;
            border: 1px solid {BORDER_MUTED};
        """)
        top_bar.addWidget(self.lbl_water_status)

        # Subtle divider |
        div3 = QFrame()
        div3.setFrameShape(QFrame.Shape.VLine)
        div3.setStyleSheet(f"background-color: {BORDER_MUTED}; width: 1px; border: none; margin: 4px 4px;")
        top_bar.addWidget(div3)

        # Stretch before title
        top_bar.addStretch(1)

        # Center Title: "Spatial Sight"
        center_title = QLabel("Spatial Sight")
        center_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_title.setStyleSheet(f"""
            color: {TEXT};
            font-size: 22px;
            font-weight: 700;
            letter-spacing: 1.5px;
        """)
        top_bar.addWidget(center_title)

        # Stretch after title
        top_bar.addStretch(1)

        # Right: Stream / FPS Pill
        self.lbl_fps = QLabel("30 FPS")
        self.lbl_fps.setStyleSheet(pill(SURFACE_DARK, TEXT_MUTED))
        top_bar.addWidget(self.lbl_fps)

        root.addLayout(top_bar)

        # ---------------- Main Body ----------------
        body = QHBoxLayout()
        body.setSpacing(14)

        # Central Video Feed (Massive view occupying vast majority of window)
        self.video_frame = QLabel()
        self.video_frame.setObjectName("VideoPanel")
        self.video_frame.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_frame.setStyleSheet(f"""
            background-color: {SURFACE_DARK};
            border: 1.5px solid {BORDER};
            border-radius: 10px;
            color: {TEXT_MUTED};
            font-size: 14px;
        """)
        self.video_frame.setText("Feed from phone")
        body.addWidget(self.video_frame, stretch=4)

        # Right Sidebar: Objects card and STOP button
        sidebar = QFrame()
        sidebar.setObjectName("SidebarCard")
        sidebar.setFixedWidth(260)
        sidebar.setStyleSheet(f"""
            QFrame#SidebarCard {{
                background-color: {SURFACE};
                border: 1.5px solid {BORDER};
                border-radius: 12px;
            }}
        """)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(14, 16, 14, 16)
        sidebar_layout.setSpacing(10)

        # Header: "Objects" (Page 2)
        header = QLabel("Objects")
        header.setStyleSheet(f"""
            color: {TEXT};
            font-size: 18px;
            font-weight: 700;
            letter-spacing: 0.8px;
        """)
        sidebar_layout.addWidget(header)

        sub_header = QLabel("In front of camera")
        sub_header.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 11px;
            font-weight: 500;
            margin-bottom: 4px;
        """)
        sidebar_layout.addWidget(sub_header)

        # Hairline separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"background-color: {BORDER_MUTED}; height: 1px; border: none;")
        sidebar_layout.addWidget(line)

        # Dynamic Object List Container (Scrollable)
        self.objects_container = QWidget()
        self.objects_layout = QVBoxLayout(self.objects_container)
        self.objects_layout.setContentsMargins(0, 4, 0, 4)
        self.objects_layout.setSpacing(8)
        self.objects_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty placeholder
        self._empty_label = QLabel("Scanning path...\nClear")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: 12px;
            padding: 24px 8px;
        """)
        self.objects_layout.addWidget(self._empty_label)

        scroll = QScrollArea()
        scroll.setWidget(self.objects_container)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        sidebar_layout.addWidget(scroll, stretch=1)

        # Bottom STOP Button
        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setObjectName("StopButton")
        self.btn_stop.setFixedHeight(48)
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.on_stop_callback)
        sidebar_layout.addWidget(self.btn_stop)

        body.addWidget(sidebar, stretch=0)
        root.addLayout(body, stretch=1)

    def set_phone_connected(self, connected: bool):
        """Update circular dot indicator (brass-gold #E5CD82 when connected, gray when offline)."""
        color = BORDER if connected else "#555555"
        self.dot_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 6px;
            border: 1px solid {BORDER_MUTED};
        """)

    def set_water_status(self, water_detected: bool):
        """Update top bar road water status badge (User Requirement 1)."""
        if water_detected:
            self.lbl_water_status.setText("Water Detected")
            self.lbl_water_status.setStyleSheet(f"""
                background-color: {BORDER};
                color: {BG};
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 700;
                border: 1px solid {BORDER};
            """)
        else:
            self.lbl_water_status.setText("Dry")
            self.lbl_water_status.setStyleSheet(f"""
                background-color: {SURFACE_DARK};
                color: {TEXT_MUTED};
                border-radius: 6px;
                padding: 3px 8px;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid {BORDER_MUTED};
            """)

    def update_objects_list(self, active_objects: Dict[str, Dict[str, Any]]):
        """
        Dynamically render only the objects currently in front of the camera.
        Page 2 Rule: "Only display that objects that are in front of the cam".
        Reuses cached row widgets to prevent GC/widget allocation churn at 30 FPS.
        """
        if not active_objects:
            # Hide all cached rows and remove them from layout
            for cat, (row, _, _) in list(self._row_cache.items()):
                if self.objects_layout.indexOf(row) != -1:
                    self.objects_layout.removeWidget(row)
                row.hide()
            if self.objects_layout.indexOf(self._empty_label) == -1:
                self.objects_layout.addWidget(self._empty_label)
            self._empty_label.show()
            return

        # Active objects detected - remove empty placeholder
        if self.objects_layout.indexOf(self._empty_label) != -1:
            self.objects_layout.removeWidget(self._empty_label)
            self._empty_label.hide()

        # Target display order: canonical TARGET_CATEGORIES first, then any extra
        display_categories = [c for c in TARGET_CATEGORIES if c in active_objects]
        for c in active_objects:
            if c not in display_categories:
                display_categories.append(c)

        # Remove/hide any cached row that is no longer active
        for cat, (row, _, _) in list(self._row_cache.items()):
            if cat not in active_objects:
                if self.objects_layout.indexOf(row) != -1:
                    self.objects_layout.removeWidget(row)
                row.hide()

        # Update or create rows in ordered sequence
        for category in display_categories:
            info = active_objects[category]
            count = info.get("count", 1)
            dist_m = info.get("closest_m", 0.0)

            if category not in self._row_cache:
                row = QFrame()
                row.setStyleSheet(f"""
                    background-color: {SURFACE_DARK};
                    border: 1px solid {BORDER_MUTED};
                    border-radius: 6px;
                    padding: 6px 8px;
                """)
                r_layout = QHBoxLayout(row)
                r_layout.setContentsMargins(6, 4, 6, 4)

                lbl_name = QLabel(category)
                lbl_name.setStyleSheet(f"color: {TEXT}; font-size: 13px; font-weight: 600;")
                r_layout.addWidget(lbl_name)
                r_layout.addStretch(1)

                lbl_info = QLabel()
                lbl_info.setStyleSheet(f"color: {TEXT_MUTED}; font-size: 12px; font-weight: 700;")
                r_layout.addWidget(lbl_info)

                self._row_cache[category] = (row, lbl_name, lbl_info)

            row, lbl_name, lbl_info = self._row_cache[category]
            lbl_info.setText(f"x{count}  {dist_m:.1f}m")

            if self.objects_layout.indexOf(row) == -1:
                self.objects_layout.addWidget(row)
            row.show()


# ============================================================================ #
#  Dashboard Window - Primary Controller                                       #
# ============================================================================ #
class DashboardWindow(QMainWindow):
    """Main window orchestrating Screen 1, Screen 2, ADB, inference, and Arduino."""

    def __init__(self, source: Union[int, str] = 0, model: str = "yolov8n.pt"):
        super().__init__()
        self.setWindowTitle("Spatial Sight")

        # Responsive window sizing
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            win_w = min(1360, max(1000, int(avail.width() * 0.88)))
            win_h = min(840, max(650, int(avail.height() * 0.88)))
            self.resize(win_w, win_h)
        else:
            self.resize(1200, 760)

        self.setMinimumSize(960, 620)
        self.setStyleSheet(GLOBAL_STYLESHEET)

        self.initial_source = source
        self.active_source = source
        self.model_path = model

        # Core Engines
        self.engine = InferenceEngine()
        self.buffer = FrameBuffer(source=self.initial_source)
        self.arduino = ArduinoBridge()
        self.arduino.start()

        self.sound = SoundController()
        self.renderer = DetectionRenderer()

        # Alert & signal debouncing state (User Rules 1 & 2)
        self._last_sent_signal: str = "GREEN"
        self._current_debounced_signal: str = "GREEN"
        self._red_hold_until: float = 0.0
        self._yellow_hold_until: float = 0.0

        # Load YOLO model
        self.engine.load_model(self.model_path)

        # Navigation: QStackedWidget (Screen 1 = Start, Screen 2 = Detection)
        self.stack = QStackedWidget()
        self.start_screen = StartScreen(self.handle_start_clicked)
        self.detection_screen = DetectionScreen(self.handle_stop_clicked)

        self.stack.addWidget(self.start_screen)      # Index 0
        self.stack.addWidget(self.detection_screen)  # Index 1

        self.setCentralWidget(self.stack)

        # Connect sound toggle
        self.detection_screen.chk_sound.toggled.connect(self.sound.set_enabled)

        # Video update timer (~30 FPS)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.video_loop)

        # Hardware monitoring timer (every 2.5s)
        self.hw_timer = QTimer(self)
        self.hw_timer.timeout.connect(self.check_hardware)
        self.hw_timer.start(2500)

        # Start in waiting/cycle mode on Arduino
        self.arduino.send_waiting_cycle()

    # ---------------------------------------------------------------------- #
    #  Screen 1 -> Screen 2 Transition Flow                                  #
    # ---------------------------------------------------------------------- #
    def handle_start_clicked(self):
        """
        When [START] is clicked:
        1. Check ADB connection to Android phone.
        2. If not connected:
           - Send command to Arduino to blink Red -> Yellow -> Green sequentially.
           - Open sleek modal dialog instructing user to connect phone.
        3. If connected:
           - Auto-forward port 8080 (`adb forward tcp:8080 tcp:8080`).
           - Auto-launch the Android app via ADB.
           - Switch FrameBuffer to http://127.0.0.1:8080/video.
           - Transition to Screen 2.
        """
        logger.info("START button clicked - checking phone connection...")
        phone_status = adb_bridge.get_phone_status()
        serial = phone_status.get("serial")

        if phone_status.get("state") == "device":
            # Phone is connected and authorized
            self._launch_and_start_phone_stream(serial=serial)
        else:
            # Phone not connected
            self.arduino.send_waiting_cycle()

            msg = phone_status.get("message", "No Android device detected.")
            dialog = ConnectPhoneDialog(self, diagnostic_msg=msg)
            dialog.exec()

            if dialog.action_result == ConnectPhoneDialog.RESULT_RETRY:
                # Re-check phone
                self.handle_start_clicked()
            elif dialog.action_result == ConnectPhoneDialog.RESULT_USE_WEBCAM:
                # Developer fallback to local webcam
                self._start_dev_webcam_stream()

    def _launch_and_start_phone_stream(self, serial: Optional[str] = None):
        """Auto-configure ADB port forwarding, launch app, and start video loop."""
        logger.info(f"Setting up ADB port forwarding 8080 -> 8080 (serial={serial or 'auto'})...")
        adb_bridge.setup_port_forward(8080, 8080, serial=serial)

        logger.info(f"Launching SpatialSight Android app via ADB (serial={serial or 'auto'})...")
        adb_bridge.launch_android_app(serial=serial, auto_stream=True)

        # Connect video buffer to phone stream URL
        stream_url = adb_bridge.get_stream_url(8080)
        self.active_source = stream_url

        self.buffer.stop()
        self.buffer = FrameBuffer(source=stream_url)
        self.buffer.start()

        # Safe green path initially
        self.arduino.send_signal("GREEN")

        # Switch to Screen 2
        self.detection_screen.set_phone_connected(True)
        self.stack.setCurrentIndex(1)
        self.timer.start(30)

    def _start_dev_webcam_stream(self):
        """Start stream using local webcam for developer/testing mode."""
        logger.info("Starting Developer mode with webcam source 0...")
        self.active_source = 0
        self.buffer.stop()
        self.buffer = FrameBuffer(source=0)
        self.buffer.start()

        self.arduino.send_signal("GREEN")
        self.detection_screen.set_phone_connected(False)
        self.stack.setCurrentIndex(1)
        self.timer.start(30)

    def handle_stop_clicked(self):
        """
        When [STOP] is clicked:
        1. Stop video loop and frame buffer.
        2. Tell Arduino to return to waiting / sequential cycling.
        3. Transition cleanly back to Screen 1.
        """
        logger.info("STOP button clicked - stopping stream and returning to Screen 1")
        self.timer.stop()
        self.buffer.stop()

        # Return Arduino to waiting/cycle state
        self.arduino.send_waiting_cycle()
        self.renderer.reset()
        self._current_debounced_signal = "GREEN"
        self._last_sent_signal = "WAITING"

        # Reset UI and switch to Screen 1
        self.detection_screen.video_frame.setText("Feed from phone")
        self.stack.setCurrentIndex(0)

    # ---------------------------------------------------------------------- #
    #  Main Video Processing & Hazard Loop (~30 FPS)                         #
    # ---------------------------------------------------------------------- #
    def video_loop(self):
        """Main rendering loop handling frame grabbing, inference, HUD, and audio."""
        frame = self.buffer.read()
        if frame is None:
            # Show waiting placeholder if frame is not ready
            return

        # Run YOLO inference
        result: InferenceResult = self.engine.infer(frame)

        # Process Tesla HUD overlays and dynamic active objects
        stopping_mult = self.arduino.stopping_dist_multiplier if self.arduino else 1.0
        annotated_frame, active_objects, severity = self.renderer.process_and_render(
            frame, result, stopping_multiplier=stopping_mult
        )

        # Update dynamic active objects list in sidebar
        self.detection_screen.update_objects_list(active_objects)

        # Update FPS label
        fps_val = self.buffer.fps
        self.detection_screen.lbl_fps.setText(f"{fps_val:.0f} FPS" if fps_val > 0 else "Live")

        # Water sensor detection check (User Requirement 1)
        water_detected = self.arduino.is_water_detected if self.arduino else False
        self.detection_screen.set_water_status(water_detected)

        # User Requirements 1 & 2 Alert State Machine:
        # Rule 1: Water detected -> keep light in YELLOW; if something comes (emergency) -> RED; DO NOT go to GREEN!
        # Rule 2: If camera sees object near corridor box -> YELLOW; if emergency -> RED; if nothing -> GREEN!
        if severity == "EMERGENCY":
            target_signal = "RED"
            self.sound.trigger_emergency_alert()
        elif water_detected:
            # Water detected: MUST BE YELLOW, NEVER GREEN!
            target_signal = "YELLOW"
            if severity == "CAUTION":
                self.sound.trigger_caution_alert()
        elif severity == "CAUTION":
            target_signal = "YELLOW"
            self.sound.trigger_caution_alert()
        else:
            target_signal = "GREEN"

        # Apply debounced signal transition to prevent rapid strobing
        final_signal = self._evaluate_debounced_signal(target_signal, water_detected)
        if final_signal != self._last_sent_signal:
            self._last_sent_signal = final_signal
            if self.arduino:
                self.arduino.send_signal(final_signal)

        # Convert OpenCV BGR image to QPixmap and display
        h, w, ch = annotated_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(annotated_frame.data, w, h, bytes_per_line, QImage.Format.Format_BGR888)
        pix = QPixmap.fromImage(q_img)

        # Scale pixmap smoothly into video frame label
        lbl_size = self.detection_screen.video_frame.size()
        scaled = pix.scaled(
            lbl_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.detection_screen.video_frame.setPixmap(scaled)

    def _evaluate_debounced_signal(self, target: str, water_detected: bool) -> str:
        """
        Hardware signal debouncer with instant emergency assertion and hold hysteresis.
        - RED: 0ms instant trigger. Holds for at least 450ms.
        - YELLOW: Promotes immediately. Holds for at least 350ms before downgrading to GREEN.
        - GREEN: Forbidden if water_detected is True. Requires hold timers to expire.
        """
        now = time.monotonic()

        # Rule 1 Hardware Guard: Never allow GREEN while water is detected
        if water_detected and target == "GREEN":
            target = "YELLOW"

        if target == "RED":
            self._current_debounced_signal = "RED"
            self._red_hold_until = now + 0.45
            return "RED"

        if self._current_debounced_signal == "RED":
            if now < self._red_hold_until:
                return "RED"

        if target == "YELLOW":
            self._current_debounced_signal = "YELLOW"
            self._yellow_hold_until = now + 0.35
            return "YELLOW"

        if self._current_debounced_signal == "YELLOW":
            if now < self._yellow_hold_until:
                return "YELLOW"

        self._current_debounced_signal = "GREEN"
        return "GREEN"

    # ---------------------------------------------------------------------- #
    #  Hardware & Connection Check (every 2.5s)                               #
    # ---------------------------------------------------------------------- #
    def check_hardware(self):
        """Periodically verify ADB phone connection and Arduino status."""
        phone_connected = adb_bridge.is_phone_connected()

        # Update phone indicator if in Screen 2
        if self.stack.currentIndex() == 1 and isinstance(self.active_source, str):
            self.detection_screen.set_phone_connected(phone_connected)

        # Update status note if in Screen 1
        if self.stack.currentIndex() == 0:
            if phone_connected:
                self.start_screen.set_status("Phone detected via USB. Tap START to launch stream.")
            else:
                self.start_screen.set_status("Connect phone via USB-C or tap START to begin")

    def closeEvent(self, event):
        """Clean shutdown when closing window."""
        self.timer.stop()
        self.hw_timer.stop()
        self.buffer.stop()
        if self.arduino:
            self.arduino.stop()
        event.accept()
