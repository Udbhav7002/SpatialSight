"""
Frame Buffer — Multi-threaded video frame ingestion with zero-backlog latency.

The producer thread continuously reads frames from the video source (USB stream
or webcam). The consumer (inference engine) always gets the LATEST frame,
discarding any stale ones. This prevents the detection from lagging behind
when inference is slower than the camera's frame rate.
"""

import threading
import time
import logging
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class FrameBuffer:
    """
    Thread-safe frame buffer that always holds only the latest frame.

    Usage:
        buffer = FrameBuffer("http://127.0.0.1:8080/video")
        buffer.start()

        while True:
            frame = buffer.read()
            if frame is not None:
                # process frame
                ...

        buffer.stop()
    """

    def __init__(self, source: str | int = 0, name: str = "FrameBuffer"):
        """
        Args:
            source: Video source — can be:
                - int (0, 1, ...): Local webcam index
                - str: URL for MJPEG stream (e.g. "http://127.0.0.1:8080/video")
                - str: Path to a video file for testing
            name: Thread name for debugging.
        """
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

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def fps(self) -> float:
        return self._fps

    @property
    def frame_count(self) -> int:
        return self._frame_count

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
            self._thread.join(timeout=3.0)
            self._thread = None

        if self._cap is not None:
            self._cap.release()
            self._cap = None

        self._connected = False
        logger.info(f"{self.name}: Stopped")

    def read(self) -> Optional[np.ndarray]:
        """
        Get the latest available frame.

        Returns:
            The most recent frame as a numpy array (BGR), or None if no frame
            is available yet.
        """
        with self._lock:
            return self._frame.copy() if self._frame is not None else None

    def change_source(self, new_source: str | int) -> None:
        """Switch to a different video source (stops and restarts the grabber)."""
        was_running = self._running
        self.stop()
        self.source = new_source
        self._frame = None
        self._frame_count = 0
        if was_running:
            self.start()

    def _grab_loop(self) -> None:
        """
        Background loop that continuously grabs frames.

        Only the latest frame is kept — older frames are overwritten immediately.
        This ensures the inference engine never processes stale (old) frames.
        """
        reconnect_delay = 1.0
        fps_update_interval = 1.0
        fps_frame_counter = 0
        fps_timer = time.monotonic()

        while self._running:
            # Connect / Reconnect
            if self._cap is None or not self._cap.isOpened():
                self._connected = False
                logger.info(f"{self.name}: Connecting to {self.source}...")
                self._cap = cv2.VideoCapture(self.source)

                if not self._cap.isOpened():
                    logger.warning(
                        f"{self.name}: Failed to open {self.source}, "
                        f"retrying in {reconnect_delay}s..."
                    )
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 1.5, 10.0)
                    continue

                # Connection succeeded
                self._connected = True
                reconnect_delay = 1.0
                logger.info(f"{self.name}: Connected to {self.source}")

            # Grab frame
            ret, frame = self._cap.read()

            if not ret:
                logger.warning(f"{self.name}: Frame grab failed, reconnecting...")
                self._cap.release()
                self._cap = None
                self._connected = False
                time.sleep(0.5)
                continue

            # Store latest frame (overwrite old one)
            with self._lock:
                self._frame = frame

            self._frame_count += 1
            self._last_frame_time = time.monotonic()

            # FPS calculation (updated every second)
            fps_frame_counter += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= fps_update_interval:
                self._fps = fps_frame_counter / elapsed
                fps_frame_counter = 0
                fps_timer = time.monotonic()

        # Cleanup
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        self._connected = False
