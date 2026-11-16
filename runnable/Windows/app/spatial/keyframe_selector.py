"""
Keyframe Selector - Sensor-triggered smart keyframe capture.

Uses phone orientation data (yaw, pitch, roll) to capture frames ONLY when
the camera points at a genuinely new area of the room. This eliminates
duplicate frames and ensures complete room coverage with minimal data.
"""

import time
import math
import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SensorData:
    """Orientation data from the phone's rotation vector sensor."""
    yaw: float    # Horizontal rotation in degrees (0-360)
    pitch: float  # Vertical tilt in degrees (-90 to +90)
    roll: float   # Tilt/rotation in degrees (-180 to +180)
    timestamp: float = 0.0  # Monotonic timestamp


@dataclass
class Keyframe:
    """A captured keyframe with its sensor metadata."""
    index: int
    frame: np.ndarray  # BGR image
    sensor: SensorData
    capture_time: float
    detections: list = field(default_factory=list)  # Filled after inference


class KeyframeSelector:
    """
    Decides when to capture a new keyframe based on phone orientation changes.

    Captures a frame only when the camera has rotated or tilted beyond
    configured thresholds, ensuring each keyframe shows a new part of the room.

    Usage:
        selector = KeyframeSelector(yaw_threshold=30.0, pitch_threshold=20.0)

        while scanning:
            frame = buffer.read()
            sensor = get_sensor_data()

            if selector.should_capture(sensor):
                kf = selector.capture(frame, sensor)
                # Process keyframe...

        keyframes = selector.get_all_keyframes()
    """

    def __init__(
        self,
        yaw_threshold: float = 30.0,     # Minimum yaw change (degrees)
        pitch_threshold: float = 20.0,   # Minimum pitch change (degrees)
        min_interval: float = 0.5,       # Minimum seconds between captures
        camera_hfov: float = 65.0,       # Horizontal field-of-view of phone camera
    ):
        """
        Args:
            yaw_threshold: Minimum horizontal rotation (degrees) to trigger capture.
            pitch_threshold: Minimum vertical tilt (degrees) to trigger capture.
            min_interval: Minimum time between keyframe captures (prevents burst).
            camera_hfov: Approximate horizontal FOV of the phone camera in degrees.
                         Used for angular position calculation of detected objects.
        """
        self.yaw_threshold = yaw_threshold
        self.pitch_threshold = pitch_threshold
        self.min_interval = min_interval
        self.camera_hfov = camera_hfov

        self._keyframes: list[Keyframe] = []
        self._last_sensor: SensorData | None = None
        self._last_capture_time: float = 0.0
        self._scanning: bool = False

    @property
    def keyframe_count(self) -> int:
        return len(self._keyframes)

    @property
    def is_scanning(self) -> bool:
        return self._scanning

    def start_scan(self) -> None:
        """Start a new room scan session. Clears any previous keyframes."""
        self._keyframes.clear()
        self._last_sensor = None
        self._last_capture_time = 0.0
        self._scanning = True
        logger.info("Room scan started")

    def stop_scan(self) -> list[Keyframe]:
        """
        Stop the current scan session.

        Returns:
            All captured keyframes from this session.
        """
        self._scanning = False
        logger.info(f"Room scan stopped - {len(self._keyframes)} keyframes captured")
        return self._keyframes.copy()

    def should_capture(self, sensor: SensorData) -> bool:
        """
        Determine if the camera has moved enough to warrant a new keyframe.

        Args:
            sensor: Current orientation from the phone.

        Returns:
            True if a new keyframe should be captured.
        """
        if not self._scanning:
            return False

        now = time.monotonic()

        # Enforce minimum interval between captures
        if now - self._last_capture_time < self.min_interval:
            return False

        # First keyframe is always captured
        if self._last_sensor is None:
            return True

        # Calculate angular deltas
        delta_yaw = abs(self._angle_diff(sensor.yaw, self._last_sensor.yaw))
        delta_pitch = abs(self._angle_diff(sensor.pitch, self._last_sensor.pitch))

        return delta_yaw >= self.yaw_threshold or delta_pitch >= self.pitch_threshold

    def capture(self, frame: np.ndarray, sensor: SensorData) -> Keyframe:
        """
        Capture a keyframe with the current frame and sensor data.

        Args:
            frame: Current BGR image from the camera.
            sensor: Current orientation data.

        Returns:
            The captured Keyframe.
        """
        now = time.monotonic()

        kf = Keyframe(
            index=len(self._keyframes),
            frame=frame.copy(),
            sensor=SensorData(
                yaw=sensor.yaw,
                pitch=sensor.pitch,
                roll=sensor.roll,
                timestamp=sensor.timestamp,
            ),
            capture_time=now,
        )

        self._keyframes.append(kf)
        self._last_sensor = sensor
        self._last_capture_time = now

        logger.info(
            f"Keyframe {kf.index} captured - "
            f"Yaw: {sensor.yaw:.1f} deg, Pitch: {sensor.pitch:.1f} deg"
        )

        return kf

    def get_all_keyframes(self) -> list[Keyframe]:
        """Return all captured keyframes."""
        return self._keyframes.copy()

    def get_coverage_percentage(self) -> float:
        """
        Estimate what percentage of a full 360 deg horizontal sweep
        has been covered by the captured keyframes.

        Returns:
            Coverage as a percentage (0.0 - 100.0).
        """
        if not self._keyframes:
            return 0.0

        # Collect all yaw angles and estimate coverage using FOV
        covered_angles: set[int] = set()
        half_fov = self.camera_hfov / 2.0

        for kf in self._keyframes:
            yaw = kf.sensor.yaw
            for offset in range(int(-half_fov), int(half_fov) + 1):
                angle = int(yaw + offset) % 360
                covered_angles.add(angle)

        return (len(covered_angles) / 360.0) * 100.0

    def estimate_object_world_angle(
        self,
        keyframe: Keyframe,
        bbox_center_x: int,
        frame_width: int,
    ) -> float:
        """
        Estimate the world angle (azimuth) of a detected object.

        Combines the keyframe's camera yaw with the object's horizontal
        position within the frame to compute its approximate world angle.

        Args:
            keyframe: The keyframe the object was detected in.
            bbox_center_x: Horizontal center of the object's bounding box (pixels).
            frame_width: Width of the frame in pixels.

        Returns:
            Estimated world angle in degrees (0-360).
        """
        # Normalized position: -0.5 (far left) to +0.5 (far right)
        normalized_x = (bbox_center_x / frame_width) - 0.5

        # Angular offset within the camera's FOV
        angular_offset = normalized_x * self.camera_hfov

        # World angle = camera yaw + offset
        world_angle = (keyframe.sensor.yaw + angular_offset) % 360

        return world_angle

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        """
        Compute the shortest angular difference between two angles.

        Handles wraparound (e.g., 350 deg to 10 deg = 20 deg, not 340 deg).
        """
        diff = (a - b + 180) % 360 - 180
        return diff
