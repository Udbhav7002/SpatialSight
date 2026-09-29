"""
Collision Zone — Region-of-Interest based forward hazard warning system.

Defines a configurable rectangular zone in the center/lower portion of the
video frame. When a detected object's bounding box overlaps this zone,
the system triggers a visual warning. Proximity is estimated by tracking
the rate of bounding box area expansion (growing rapidly = approaching fast).
"""

import time
import logging
from dataclasses import dataclass

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# COCO class IDs for objects that are real collision hazards
HAZARD_CLASSES = {
    0: "person",
    1: "bicycle",
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    15: "cat",
    16: "dog",
}


@dataclass
class HazardAlert:
    """A triggered collision warning."""
    class_name: str
    overlap_ratio: float   # 0.0 – 1.0 (how much of the object is in the zone)
    bbox_area: int         # Bounding box area in pixels
    approach_rate: float   # Rate of area change (positive = approaching)
    severity: str          # "LOW", "MEDIUM", "HIGH"


class CollisionZone:
    """
    Defines a forward hazard warning zone in the video frame.

    The zone is a rectangle in the center/lower portion of the frame.
    Objects that overlap this zone trigger graduated warnings.
    """

    def __init__(
        self,
        zone_x_ratio: float = 0.2,   # Zone starts at 20% from left
        zone_y_ratio: float = 0.4,   # Zone starts at 40% from top
        zone_w_ratio: float = 0.6,   # Zone is 60% of frame width
        zone_h_ratio: float = 0.55,  # Zone is 55% of frame height
    ):
        """
        Define the collision zone as ratios of the frame dimensions.

        This way the zone scales automatically to any resolution.
        """
        self.zone_x_ratio = zone_x_ratio
        self.zone_y_ratio = zone_y_ratio
        self.zone_w_ratio = zone_w_ratio
        self.zone_h_ratio = zone_h_ratio

        # Track previous bbox areas for approach rate estimation
        self._prev_areas: dict[str, list[tuple[float, int]]] = {}  # class -> [(time, area)]
        self._history_window = 1.0  # seconds to track

    def get_zone_rect(self, frame_w: int, frame_h: int) -> tuple[int, int, int, int]:
        """Get the zone rectangle in pixel coordinates (x1, y1, x2, y2)."""
        x1 = int(frame_w * self.zone_x_ratio)
        y1 = int(frame_h * self.zone_y_ratio)
        x2 = int(frame_w * (self.zone_x_ratio + self.zone_w_ratio))
        y2 = int(frame_h * (self.zone_y_ratio + self.zone_h_ratio))
        return (x1, y1, x2, y2)

    def check_hazards(self, detections: list, frame_shape: tuple) -> list[HazardAlert]:
        """
        Check all detections against the collision zone.

        Args:
            detections: List of Detection objects from the inference engine.
            frame_shape: (H, W, C) shape of the frame.

        Returns:
            List of HazardAlert for objects in the danger zone.
        """
        frame_h, frame_w = frame_shape[:2]
        zx1, zy1, zx2, zy2 = self.get_zone_rect(frame_w, frame_h)
        zone_area = (zx2 - zx1) * (zy2 - zy1)

        now = time.monotonic()
        alerts: list[HazardAlert] = []

        for det in detections:
            # Only check hazard-class objects
            if det.class_id not in HAZARD_CLASSES:
                continue

            bx1, by1, bx2, by2 = det.bbox
            bbox_area = (bx2 - bx1) * (by2 - by1)

            # Calculate overlap between detection bbox and collision zone
            overlap_x1 = max(bx1, zx1)
            overlap_y1 = max(by1, zy1)
            overlap_x2 = min(bx2, zx2)
            overlap_y2 = min(by2, zy2)

            if overlap_x1 >= overlap_x2 or overlap_y1 >= overlap_y2:
                continue  # No overlap — not in danger zone

            overlap_area = (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
            overlap_ratio = overlap_area / max(bbox_area, 1)

            # Track approach rate (bbox area change over time)
            key = f"{det.class_name}_{det.class_id}"
            if key not in self._prev_areas:
                self._prev_areas[key] = []

            self._prev_areas[key].append((now, bbox_area))

            # Prune old entries
            self._prev_areas[key] = [
                (t, a) for t, a in self._prev_areas[key]
                if now - t <= self._history_window
            ]

            # Calculate approach rate
            approach_rate = 0.0
            history = self._prev_areas[key]
            if len(history) >= 2:
                dt = history[-1][0] - history[0][0]
                if dt > 0.05:
                    da = history[-1][1] - history[0][1]
                    approach_rate = da / dt  # pixels²/second

            # Determine severity
            if overlap_ratio > 0.6 or (approach_rate > 50000 and overlap_ratio > 0.3):
                severity = "HIGH"
            elif overlap_ratio > 0.3 or approach_rate > 20000:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            alerts.append(HazardAlert(
                class_name=det.class_name,
                overlap_ratio=overlap_ratio,
                bbox_area=bbox_area,
                approach_rate=approach_rate,
                severity=severity,
            ))

        return alerts

    def draw_zone(
        self,
        frame: np.ndarray,
        alerts: list[HazardAlert] | None = None,
    ) -> np.ndarray:
        """
        Draw the collision zone overlay on the frame.

        The zone is green when clear, yellow for LOW, orange for MEDIUM,
        and red for HIGH severity.
        """
        frame_h, frame_w = frame.shape[:2]
        zx1, zy1, zx2, zy2 = self.get_zone_rect(frame_w, frame_h)

        # Determine zone color based on worst alert
        if not alerts:
            color = (0, 255, 0)      # Green — clear
            label = "CLEAR"
        else:
            max_severity = max(alerts, key=lambda a: {"LOW": 1, "MEDIUM": 2, "HIGH": 3}[a.severity])
            if max_severity.severity == "HIGH":
                color = (0, 0, 255)  # Red
                label = f"!! COLLISION WARNING: {max_severity.class_name.upper()} !!"
            elif max_severity.severity == "MEDIUM":
                color = (0, 165, 255)  # Orange
                label = f"CAUTION: {max_severity.class_name}"
            else:
                color = (0, 255, 255)  # Yellow
                label = f"WATCH: {max_severity.class_name}"

        # Draw semi-transparent zone overlay
        overlay = frame.copy()
        cv2.rectangle(overlay, (zx1, zy1), (zx2, zy2), color, -1)
        cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

        # Draw zone border
        cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), color, 2)

        # Draw label
        font_scale = 0.7 if frame_w < 1280 else 1.0
        thickness = 2
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        label_x = zx1 + (zx2 - zx1 - tw) // 2
        label_y = zy1 - 10 if zy1 > 30 else zy2 + th + 10

        cv2.putText(
            frame, label, (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness,
        )

        return frame
