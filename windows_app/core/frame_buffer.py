"""
Frame Buffer - Multi-threaded video frame ingestion with zero-backlog latency.

The producer thread continuously reads frames from the video source (USB stream,
webcam, or test video file). The consumer (inference engine / UI) always gets
the LATEST frame, discarding stale ones. This guarantees low-latency performance.
"""

import threading
import time
import logging
from typing import Optional, Union

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameBuffer:
    """
    Thread-safe frame buffer that always holds only the latest frame.
    Supports seamless video file looping, live webcam, and HTTP MJPEG streams.
    """

    def __init__(self, source: Union[str, int] = 0, name: str = "FrameBuffer"):
        if isinstance(source, str) and source.lower() in ("usb", "phone", "android"):
            source = "http://127.0.0.1:8080/video"

        self.source = source
        self.name = name

        self._frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cap: Optional[cv2.VideoCapture] = None

        # Diagnostics
        self._fps: float = 0.0
        self._frame_count: int = 0
        self._connected: bool = False
        self._last_frame_time: float = 0.0
        self._consecutive_failures: int = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def source_name(self) -> str:
        if isinstance(self.source, int):
            return f"Webcam #{self.source}"
        elif isinstance(self.source, str):
            if "8080" in self.source or "video" in self.source:
                return "Android Phone (USB-C)"
            return self.source.split("/")[-1]
        return str(self.source)

    def start(self) -> None:
        """Start the background frame grabber thread."""
        if self._running:
            logger.warning(f"{self.name}: Already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._grab_loop,
            name=self.name,
            daemon=True,
        )
        self._thread.start()
        logger.info(f"{self.name}: Started grabbing from {self.source}")

    def stop(self) -> None:
        """Stop the background frame grabber thread and release resources."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

        self._connected = False
        logger.info(f"{self.name}: Stopped")

    def read(self) -> Optional[np.ndarray]:
        """
        Get the latest available frame.
        If no camera is reachable, generates a clean fallback frame with instructions.
        """
        with self._lock:
            if self._frame is not None:
                return self._frame.copy()

        # Fallback if disconnected
        if not self._connected:
            return self._create_fallback_frame()
        return None

    def change_source(self, new_source: Union[str, int]) -> None:
        """Switch to a different video source (stops and restarts the grabber)."""
        if isinstance(new_source, str) and new_source.lower() in ("usb", "phone", "android"):
            new_source = "http://127.0.0.1:8080/video"

        logger.info(f"{self.name}: Switching source to {new_source}")
        was_running = self._running
        self.stop()
        self.source = new_source
        with self._lock:
            self._frame = None
        self._frame_count = 0
        self._consecutive_failures = 0
        if was_running:
            self.start()

    def _create_fallback_frame(self) -> np.ndarray:
        """Generate a standby image when no video stream is connected (uniform palette #15370D)."""
        h, w = 720, 1280
        img = np.zeros((h, w, 3), dtype=np.uint8)
        # Deep forest dark green background #15370D (BGR: 13, 55, 21)
        img[:] = (13, 55, 21)

        # Subtle dark green grid #1E4714 (BGR: 20, 71, 30)
        for x in range(0, w, 60):
            cv2.line(img, (x, 0), (x, h), (20, 71, 30), 1)
        for y in range(0, h, 60):
            cv2.line(img, (0, y), (w, y), (20, 71, 30), 1)

        is_phone_src = "8080" in str(self.source) or "android" in str(self.source).lower()

        # Center banner in cream #FFF2B4 (BGR: 180, 242, 255) and brass gold #E5CD82 (BGR: 130, 205, 229)
        title = "WAITING FOR CAMERA STREAM"
        cv2.putText(img, title, (w // 2 - 250, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (180, 242, 255), 2, cv2.LINE_AA)
        cv2.putText(img, f"Source: {self.source_name}", (w // 2 - 140, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (130, 205, 229), 1, cv2.LINE_AA)

        if is_phone_src:
            card_x1, card_y1, card_x2, card_y2 = w // 2 - 340, 280, w // 2 + 340, 500
            cv2.rectangle(img, (card_x1, card_y1), (card_x2, card_y2), (20, 71, 30), -1)
            cv2.rectangle(img, (card_x1, card_y1), (card_x2, card_y2), (130, 205, 229), 1, cv2.LINE_AA)

            steps = [
                "Phone Connection Checklist:",
                "1. Connect Android phone to computer via USB-C cable.",
                "2. Enable Developer Options and USB Debugging on phone.",
                "3. Tap 'Allow USB debugging' when prompted on phone.",
                "4. SpatialSight app will auto-launch and stream feed.",
            ]
            y_offset = card_y1 + 40
            for i, step in enumerate(steps):
                color = (180, 242, 255) if i == 0 else (130, 205, 229)
                scale = 0.55 if i == 0 else 0.50
                thickness = 2 if i == 0 else 1
                cv2.putText(img, step, (card_x1 + 25, y_offset), cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness, cv2.LINE_AA)
                y_offset += 38
        else:
            cv2.putText(img, "Initializing video stream...",
                        (w // 2 - 140, 320), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (130, 205, 229), 1, cv2.LINE_AA)

        return img

    def _grab_loop(self) -> None:
        """Background loop continuously capturing the latest frame."""
        reconnect_delay = 1.0
        fps_update_interval = 1.0
        fps_frame_counter = 0
        fps_timer = time.monotonic()

        is_file_source = isinstance(self.source, str) and not self.source.startswith("http")

        while self._running:
            # 1. Connect / Reconnect
            if self._cap is None or not self._cap.isOpened():
                self._connected = False
                logger.info(f"{self.name}: Connecting to {self.source}...")
                self._cap = cv2.VideoCapture(self.source)

                if not self._cap.isOpened():
                    self._consecutive_failures += 1
                    time.sleep(min(reconnect_delay, 3.0))
                    continue

                self._connected = True
                self._consecutive_failures = 0
                logger.info(f"{self.name}: Connected successfully to {self.source}")

            # 2. Grab frame
            ret, frame = self._cap.read()

            if not ret:
                # If reading a video file, loop back to the start seamlessly
                if is_file_source and self._cap is not None:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self._cap.read()

                if not ret:
                    self._consecutive_failures += 1
                    if self._cap is not None:
                        self._cap.release()
                        self._cap = None
                    self._connected = False
                    time.sleep(0.5)
                    continue

            # Ensure incoming video feed is strictly horizontal / landscape (width > height)
            if frame is not None and frame.shape[0] > frame.shape[1]:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

            # Store latest frame
            with self._lock:
                self._frame = frame

            self._frame_count += 1
            self._last_frame_time = time.monotonic()

            # Pacing for video files to mimic real-time ~30 FPS
            if is_file_source:
                time.sleep(0.033)

            # FPS calculation
            fps_frame_counter += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= fps_update_interval:
                self._fps = fps_frame_counter / max(0.001, elapsed)
                fps_frame_counter = 0
                fps_timer = time.monotonic()

        # Cleanup
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._connected = False
