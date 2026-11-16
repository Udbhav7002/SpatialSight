"""
Collision Zone - Physics-based ADAS Forward Driving Corridor & Distance Estimation.

Features:
- Perspective trapezoidal driving lane corridor (ignores parked / side vehicles)
- Universal obstacle detection (detects suitcases, chairs, boxes, vehicles, pedestrians)
- Optical pinhole physics distance estimation (Z = f * H / h)
- Graduated severity based on physical distance (Yellow for far obstacles, Red for close)
- Adaptive wet-road stopping distance expansion
- Per-object tracking with unique IDs using IoU matching
- Speed estimation and Time-to-collision (TTC)
- Hysteresis / debouncing for hazard alerts
"""

import time
import logging
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict, Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Classes that are small personal items, not road/corridor collision hazards
IGNORED_CLASSES = {
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich",
    "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
    "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush", "tie", "cell phone"
}

# Real-world physical heights in meters for distance estimation (Pinhole optics model)
OBJECT_REAL_HEIGHTS = {
    "person": 1.70,
    "bicycle": 1.20,
    "car": 1.50,
    "motorcycle": 1.30,
    "bus": 3.20,
    "truck": 2.80,
    "cat": 0.35,
    "dog": 0.55,
    "horse": 1.60,
    "cow": 1.50,
    "sheep": 0.85,
    "backpack": 0.50,
    "suitcase": 0.65,
    "handbag": 0.40,
    "umbrella": 0.90,
    "chair": 0.85,
    "couch": 0.85,
    "sofa": 0.85,
    "bed": 0.70,
    "dining table": 0.75,
    "toilet": 0.75,
    "tv": 0.60,
    "laptop": 0.30,
    "refrigerator": 1.75,
    "potted plant": 0.65,
    "traffic light": 1.00,
    "stop sign": 0.90,
    "bench": 0.85,
    "box": 0.50,
    "rock": 0.40,
    "table": 0.75,
    "object": 0.70,
    "animal": 0.80,
    "bike": 1.25,
    "sign": 1.00,
}

def get_iou(bb1: Tuple[int, int, int, int], bb2: Tuple[int, int, int, int]) -> float:
    """Calculate Intersection over Union (IoU) of two bounding boxes."""
    x_left = max(bb1[0], bb2[0])
    y_top = max(bb1[1], bb2[1])
    x_right = min(bb1[2], bb2[2])
    y_bottom = min(bb1[3], bb2[3])

    if x_right < x_left or y_bottom < y_top:
        return 0.0

    intersection_area = (x_right - x_left) * (y_bottom - y_top)
    bb1_area = (bb1[2] - bb1[0]) * (bb1[3] - bb1[1])
    bb2_area = (bb2[2] - bb2[0]) * (bb2[3] - bb2[1])
    union_area = bb1_area + bb2_area - intersection_area
    if union_area == 0:
        return 0.0
    return intersection_area / float(union_area)

@dataclass
class HazardAlert:
    """A triggered collision warning with physical distance."""
    class_name: str
    class_id: int
    overlap_ratio: float   # 0.0 - 1.0 (how much of the object is in the driving lane)
    distance_m: float      # Estimated physical distance in meters
    bbox_area: int         # Bounding box area in pixels
    approach_rate: float   # Rate of area change (positive = approaching)
    severity: str          # "LOW", "MEDIUM", "HIGH"
    track_id: int = -1
    bbox: Tuple[int, int, int, int] = (0, 0, 0, 0)
    speed_kmh: float = 0.0
    ttc_s: float = float('inf')


class CollisionZone:
    """
    Defines a perspective forward driving corridor and calculates physical distances.
    """

    def __init__(
        self,
        lane_top_width_ratio: float = 0.28,     # Lane width at horizon (28% of frame)
        lane_bottom_width_ratio: float = 0.62,  # Lane width at bumper (62% of frame)
        horizon_y_ratio: float = 0.42,          # Horizon starts at 42% from top
        bottom_y_ratio: float = 0.96,           # Bottom of lane ends near hood (96%)
        focal_length_multiplier: float = 0.75,  # Phone camera calibration multiplier
    ):
        self.lane_top_width_ratio = lane_top_width_ratio
        self.lane_bottom_width_ratio = lane_bottom_width_ratio
        self.horizon_y_ratio = horizon_y_ratio
        self.bottom_y_ratio = bottom_y_ratio
        self.focal_length_multiplier = focal_length_multiplier

        # Per-object tracking with unique IDs
        self._tracked_objects: Dict[int, Dict[str, Any]] = {}
        self._next_track_id = 1

    def estimate_distance(self, target: str | int, bbox_height: int, frame_w: int) -> float:
        """
        Calculates physical distance in meters using optical pinhole camera geometry:
        distance = (focal_length * real_height) / bbox_height_pixels
        """
        if isinstance(target, str):
            real_height_m = OBJECT_REAL_HEIGHTS.get(target.lower(), 0.70)
        else:
            real_height_m = 1.50 if target in (2, 5, 7) else (1.70 if target == 0 else 0.70)

        # Approximate focal length in pixels for smartphone FOV
        focal_length_px = frame_w * self.focal_length_multiplier
        
        h_px = max(bbox_height, 8)
        dist_m = (focal_length_px * real_height_m) / h_px
        # Clamp to realistic perception limits (0.5m to 60.0m)
        return round(float(np.clip(dist_m, 0.5, 60.0)), 1)

    def get_lane_polygon(self, frame_w: int, frame_h: int, stopping_multiplier: float = 1.0) -> np.ndarray:
        """
        Get the 4-point perspective trapezoid representing the vehicle's driving corridor.
        Expands upward toward the horizon on wet roads (stopping_multiplier > 1.0).
        """
        # Expand horizon upwards on wet road (earlier warning)
        expansion = min(0.12, (stopping_multiplier - 1.0) * 0.08)
        top_y = int(frame_h * max(0.30, self.horizon_y_ratio - expansion))
        bottom_y = int(frame_h * self.bottom_y_ratio)

        # Center lane horizontal boundaries
        cx = frame_w / 2.0
        half_top_w = (frame_w * self.lane_top_width_ratio) / 2.0
        half_bot_w = (frame_w * self.lane_bottom_width_ratio) / 2.0

        p_top_left = (int(cx - half_top_w), top_y)
        p_top_right = (int(cx + half_top_w), top_y)
        p_bot_right = (int(cx + half_bot_w), bottom_y)
        p_bot_left = (int(cx - half_bot_w), bottom_y)

        return np.array([p_top_left, p_top_right, p_bot_right, p_bot_left], dtype=np.int32)

    def is_in_driving_corridor(
        self,
        bx1: int, by1: int, bx2: int, by2: int,
        frame_w: int, frame_h: int,
        stopping_multiplier: float = 1.0,
    ) -> tuple[bool, float]:
        """
        Determines if an object is inside the forward driving lane.
        Filters out parked cars or roadside furniture on the left/right.
        """
        poly = self.get_lane_polygon(frame_w, frame_h, stopping_multiplier=stopping_multiplier)
        top_y = poly[0][1]
        bottom_y = poly[2][1]

        # Ground contact point of the object (bottom center of bounding box)
        ground_x = (bx1 + bx2) / 2.0
        ground_y = float(by2)

        # If object is above horizon or below front bumper, check for box intersection
        if ground_y < top_y or ground_y > bottom_y:
            if by1 < top_y and by2 > top_y:
                ground_y = float(top_y + 10)
            elif by1 < bottom_y and by2 > bottom_y:
                ground_y = float(bottom_y - 10)
            else:
                return False, 0.0

        # Compute lane left and right boundaries at this vertical depth
        t = (ground_y - top_y) / max(1.0, float(bottom_y - top_y))
        t = float(np.clip(t, 0.0, 1.0))
        lane_left_x = poly[0][0] + t * (poly[3][0] - poly[0][0])
        lane_right_x = poly[1][0] + t * (poly[2][0] - poly[1][0])

        box_w = max(1, bx2 - bx1)
        # Compute horizontal overlap with lane at this depth
        overlap_left = max(float(bx1), lane_left_x)
        overlap_right = min(float(bx2), lane_right_x)
        overlap_w = max(0.0, overlap_right - overlap_left)
        overlap_ratio = overlap_w / box_w

        # PARKED / SIDE VEHICLE FILTER:
        # If the object center is outside the lane AND overlap is small (< 30%), ignore
        if (ground_x < lane_left_x or ground_x > lane_right_x) and overlap_ratio < 0.30:
            return False, 0.0

        in_lane = (overlap_ratio >= 0.20) or (lane_left_x <= ground_x <= lane_right_x)
        return in_lane, overlap_ratio

    def is_near_driving_corridor(
        self,
        bx1: int, by1: int, bx2: int, by2: int,
        frame_w: int, frame_h: int,
        stopping_multiplier: float = 1.0,
        margin_factor: float = 0.40,
    ) -> tuple[bool, float]:
        """
        Determines if an object is near the driving lane corridor (caution buffer zone).
        User Rule 2: "If the camera can see any object near the box in the cam keep the light to yellow"
        """
        poly = self.get_lane_polygon(frame_w, frame_h, stopping_multiplier=stopping_multiplier)
        top_y = poly[0][1]
        bottom_y = poly[2][1]

        ground_x = (bx1 + bx2) / 2.0
        ground_y = float(by2)

        if ground_y < top_y or ground_y > bottom_y:
            if by1 < top_y and by2 > top_y:
                ground_y = float(top_y + 10)
            elif by1 < bottom_y and by2 > bottom_y:
                ground_y = float(bottom_y - 10)
            else:
                return False, 0.0

        t = (ground_y - top_y) / max(1.0, float(bottom_y - top_y))
        t = float(np.clip(t, 0.0, 1.0))
        lane_left_x = poly[0][0] + t * (poly[3][0] - poly[0][0])
        lane_right_x = poly[1][0] + t * (poly[2][0] - poly[1][0])
        lane_w = max(1.0, lane_right_x - lane_left_x)

        # Expanded caution boundary (margin_factor buffer on either side of the lane)
        caution_left_x = lane_left_x - (margin_factor * lane_w)
        caution_right_x = lane_right_x + (margin_factor * lane_w)

        box_w = max(1, bx2 - bx1)
        overlap_left = max(float(bx1), caution_left_x)
        overlap_right = min(float(bx2), caution_right_x)
        overlap_w = max(0.0, overlap_right - overlap_left)
        overlap_ratio = overlap_w / box_w

        near_lane = (overlap_ratio >= 0.15) or (caution_left_x <= ground_x <= caution_right_x)
        return near_lane, overlap_ratio

    def check_hazards(
        self,
        detections: list,
        frame_shape: tuple,
        stopping_multiplier: float = 1.0,
    ) -> list[HazardAlert]:
        """
        Check detections against the lane corridor and assign distance-based severity.
        Uses tracking, speed estimation, and hysteresis to provide stable alerts.
        """
        frame_h, frame_w = frame_shape[:2]
        now = time.monotonic()
        alerts: list[HazardAlert] = []

        # Safe braking distance threshold: 5.5m on dry road, up to 9m on wet road
        emergency_brake_dist = 5.5 * stopping_multiplier
        caution_dist = 18.0 * max(1.0, stopping_multiplier * 0.9)

        det_infos = []
        for det in detections:
            if det.class_name.lower() in IGNORED_CLASSES:
                continue

            bx1, by1, bx2, by2 = det.bbox
            bbox_h = by2 - by1
            dist_m = self.estimate_distance(det.class_name, bbox_h, frame_w)
            in_corridor, overlap_ratio = self.is_in_driving_corridor(
                bx1, by1, bx2, by2, frame_w, frame_h, stopping_multiplier=stopping_multiplier
            )
            
            det_infos.append({
                "det": det,
                "bbox": det.bbox,
                "dist_m": dist_m,
                "in_corridor": in_corridor,
                "overlap_ratio": overlap_ratio,
                "matched": False
            })

        # Match detections to existing tracked objects using IoU
        current_tracked = {}
        for track_id, track in self._tracked_objects.items():
            best_iou = 0.3  # IoU matching threshold
            best_idx = -1
            for i, info in enumerate(det_infos):
                if info["matched"] or info["det"].class_id != track["class_id"]:
                    continue
                iou = get_iou(track["last_bbox"], info["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i
            
            if best_idx != -1:
                info = det_infos[best_idx]
                info["matched"] = True
                track["history"].append((now, info["dist_m"], info["bbox"]))
                # Keep up to ~1 second of history (at 15 fps)
                track["history"] = track["history"][-15:]
                track["last_bbox"] = info["bbox"]
                track["last_seen"] = now
                track["in_corridor"] = info["in_corridor"]
                track["overlap_ratio"] = info["overlap_ratio"]
                track["dist_m"] = info["dist_m"]
                current_tracked[track_id] = track
            else:
                # Retain track briefly even if missing for a frame or two (debouncing)
                if now - track["last_seen"] < 0.5:
                    current_tracked[track_id] = track

        # Add unmatched detections as new tracked objects
        for info in det_infos:
            if not info["matched"]:
                track_id = self._next_track_id
                self._next_track_id += 1
                new_track = {
                    "class_name": info["det"].class_name,
                    "class_id": info["det"].class_id,
                    "history": [(now, info["dist_m"], info["bbox"])],
                    "last_bbox": info["bbox"],
                    "last_seen": now,
                    "in_corridor": info["in_corridor"],
                    "overlap_ratio": info["overlap_ratio"],
                    "dist_m": info["dist_m"],
                    "speed_kmh": 0.0,
                    "ttc_s": float('inf'),
                    "frames_danger": 0,
                    "frames_safe": 0,
                    "severity": "LOW"
                }
                current_tracked[track_id] = new_track

        self._tracked_objects = current_tracked

        # Update speed, TTC, and evaluate hazards
        for track_id, track in self._tracked_objects.items():
            if len(track["history"]) >= 2:
                dt = track["history"][-1][0] - track["history"][0][0]
                ddist = track["history"][0][1] - track["history"][-1][1]
                if dt > 0.05:
                    speed_mps = ddist / dt
                    track["speed_kmh"] = speed_mps * 3.6
                    if speed_mps > 0.1:
                        track["ttc_s"] = track["dist_m"] / speed_mps
                    else:
                        track["ttc_s"] = float('inf')

            dist_m = track["dist_m"]
            speed_kmh = track["speed_kmh"]
            ttc_s = track["ttc_s"]
            in_corridor = track["in_corridor"]

            # Determine raw severity for current frame
            raw_severity = "SAFE"
            if in_corridor:
                if dist_m <= emergency_brake_dist or (ttc_s < 2.5 and dist_m < 15.0):
                    raw_severity = "HIGH"
                elif dist_m <= caution_dist or ttc_s < 5.0:
                    raw_severity = "MEDIUM"
                elif dist_m <= 35.0:
                    raw_severity = "LOW"

            # Hysteresis / Debouncing
            if raw_severity == "HIGH":
                track["frames_danger"] += 1
                track["frames_safe"] = 0
            else:
                track["frames_danger"] = 0
                track["frames_safe"] += 1

            if track["frames_danger"] >= 3:
                track["severity"] = "HIGH"
            elif track["frames_safe"] >= 5:
                track["severity"] = raw_severity
            else:
                # Maintain HIGH if debouncing hasn't finished, else use raw
                if track["severity"] == "HIGH" and track["frames_safe"] < 5:
                    pass # stays HIGH
                else:
                    track["severity"] = raw_severity

            if in_corridor and track["severity"] != "SAFE":
                bx1, by1, bx2, by2 = track["last_bbox"]
                bbox_area = (bx2 - bx1) * (by2 - by1)
                
                alerts.append(HazardAlert(
                    class_name=track["class_name"],
                    class_id=track["class_id"],
                    overlap_ratio=track["overlap_ratio"],
                    distance_m=dist_m,
                    bbox_area=bbox_area,
                    approach_rate=0.0, # Kept for backward compatibility
                    severity=track["severity"],
                    track_id=track_id,
                    bbox=track["last_bbox"],
                    speed_kmh=speed_kmh,
                    ttc_s=ttc_s
                ))

        return alerts

    def get_status_summary(self) -> dict:
        """
        Returns a summary of the current tracking and hazard state.
        """
        total_tracked = len(self._tracked_objects)
        objects_in_lane = sum(1 for t in self._tracked_objects.values() if t["in_corridor"])
        
        hazards = [t for t in self._tracked_objects.values() if t["in_corridor"] and t["severity"] != "SAFE"]
        
        closest_distance_m = min([t["dist_m"] for t in hazards], default=float('inf'))
        closest_ttc_s = min([t["ttc_s"] for t in hazards], default=float('inf'))
        
        severity_map = {"HIGH": 3, "MEDIUM": 2, "LOW": 1, "SAFE": 0}
        if hazards:
            worst_severity = max(hazards, key=lambda t: severity_map.get(t["severity"], 0))["severity"]
        else:
            worst_severity = "SAFE"
            
        approach_speed_kmh = max([t["speed_kmh"] for t in hazards], default=0.0)
        
        return {
            "total_tracked": total_tracked,
            "objects_in_lane": objects_in_lane,
            "closest_distance_m": closest_distance_m,
            "closest_ttc_s": closest_ttc_s,
            "worst_severity": worst_severity,
            "approach_speed_kmh": approach_speed_kmh
        }

    def draw_zone(
        self,
        frame: np.ndarray,
        alerts: list[HazardAlert] | None = None,
        stopping_multiplier: float = 1.0,
        friction_mu: float = 0.80,
    ) -> np.ndarray:
        """
        Draw the perspective driving corridor with ADAS styling and live distance info.
        """
        frame_h, frame_w = frame.shape[:2]
        poly = self.get_lane_polygon(frame_w, frame_h, stopping_multiplier=stopping_multiplier)

        # Color based on highest severity (Apple system palette, BGR)
        if not alerts:
            color = (88, 209, 48)      # Green #30D158 - path clear
            label = "PATH CLEAR" if stopping_multiplier <= 1.15 else f"PATH CLEAR [WET ROAD mu={friction_mu:.2f}]"
        else:
            # Sort by severity
            worst = max(alerts, key=lambda a: {"LOW": 1, "MEDIUM": 2, "HIGH": 3}[a.severity])
            if worst.severity == "HIGH":
                color = (58, 69, 255)  # Red #FF453A
                label = f"!! EMERGENCY BRAKE: {worst.class_name.upper()} ({worst.distance_m:.1f}m) !!"
            elif worst.severity == "MEDIUM":
                color = (10, 214, 255)  # Yellow #FFD60A
                label = f"CAUTION: {worst.class_name.upper()} ({worst.distance_m:.1f}m)"
            else:
                color = (10, 159, 255)  # Orange #FF9F0A
                label = f"WATCH: {worst.class_name.upper()} IN DISTANCE ({worst.distance_m:.1f}m)"

            if stopping_multiplier > 1.15 and worst.severity != "LOW":
                label += f" [WET mu={friction_mu:.2f}]"

        # Draw semi-transparent lane polygon
        overlay = frame.copy()
        cv2.fillPoly(overlay, [poly], color)
        cv2.addWeighted(overlay, 0.18, frame, 0.82, 0, frame)

        # Draw lane edge lines
        cv2.polylines(frame, [poly], isClosed=True, color=color, thickness=2, lineType=cv2.LINE_AA)

        # Draw graduated lane center dashed line
        top_y = poly[0][1]
        bottom_y = poly[2][1]
        cx_top = (poly[0][0] + poly[1][0]) // 2
        cx_bot = (poly[3][0] + poly[2][0]) // 2
        
        dash_count = 10
        for i in range(dash_count):
            if i % 2 == 0:
                t1 = i / float(dash_count)
                t2 = (i + 1) / float(dash_count)
                x1 = int(cx_top + t1 * (cx_bot - cx_top))
                y1 = int(top_y + t1 * (bottom_y - top_y))
                x2 = int(cx_top + t2 * (cx_bot - cx_top))
                y2 = int(top_y + t2 * (bottom_y - top_y))
                cv2.line(frame, (x1, y1), (x2, y2), color, max(1, int(2 * t2)), lineType=cv2.LINE_AA)

        # Draw distance markers at 5m, 10m, 20m in the lane
        f = frame_w * self.focal_length_multiplier
        H_cam = 1.5 # assumed camera height
        horizon_y = int(frame_h * self.horizon_y_ratio)
        
        for d in [5, 10, 20]:
            y_m = int(horizon_y + (f * H_cam) / d)
            if top_y <= y_m <= bottom_y:
                t = (y_m - top_y) / float(bottom_y - top_y)
                x_left = int(poly[0][0] + t * (poly[3][0] - poly[0][0]))
                x_right = int(poly[1][0] + t * (poly[2][0] - poly[1][0]))
                cv2.line(frame, (x_left, y_m), (x_right, y_m), color, 1, lineType=cv2.LINE_AA)
                cv2.putText(frame, f"{d}m", (x_left + 5, y_m - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, lineType=cv2.LINE_AA)

        # Draw bounding boxes and info for tracked alerts
        if alerts:
            for alert in alerts:
                bx1, by1, bx2, by2 = alert.bbox
                if bx2 - bx1 > 0 and by2 - by1 > 0:
                    if alert.severity == "HIGH":
                        bcolor = (58, 69, 255)   # Apple Red #FF453A
                    elif alert.severity == "MEDIUM":
                        bcolor = (10, 214, 255)  # Apple Yellow #FFD60A
                    else:
                        bcolor = (10, 159, 255)  # Apple Orange #FF9F0A
                        
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), bcolor, 2)
                    
                    # Construct info string
                    info_parts = [f"Dist: {alert.distance_m:.1f}m"]
                    if alert.speed_kmh > 0:
                        info_parts.append(f"Spd: {alert.speed_kmh:.0f}km/h")
                    if alert.ttc_s < 100:
                        info_parts.append(f"TTC: {alert.ttc_s:.1f}s")
                    
                    info_str = " | ".join(info_parts)
                    
                    text_y = max(20, by1 - 5)
                    cv2.putText(frame, info_str, (bx1, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, bcolor, 2, lineType=cv2.LINE_AA)

        # Draw top HUD banner
        font_scale = 0.65 if frame_w < 1280 else 0.85
        thickness = 2
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
        
        label_x = cx_top - tw // 2
        label_y = max(th + 15, top_y - 12)

        # Dark background backing for crisp text readability
        cv2.rectangle(
            frame,
            (label_x - 10, label_y - th - 6),
            (label_x + tw + 10, label_y + 6),
            (0, 0, 0),
            -1,
        )
        cv2.putText(
            frame, label, (label_x, label_y),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness, lineType=cv2.LINE_AA
        )

        return frame
