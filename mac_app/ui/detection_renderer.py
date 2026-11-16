"""
Detection Renderer - Minimalist Tesla Vector Visualizer & Anti-Jitter ADAS Corridor Engine.

Features:
- Tesla vector bounding boxes with crisp brass-gold corner brackets (#E5CD82)
- Anti-Jitter Temporal Filter: Exponential Moving Average (EMA) box smoothing + IoU tracking
- Multi-frame hysteresis (prevents single-frame dropouts from causing box/sidebar jitter)
- Category mapping to canonical 10 perception categories
- Optical distance estimation with EMA smoothing (Z = f * H / h)
- Dynamic hazard evaluation in and near the forward driving corridor (User Rules 1 & 2):
    - Emergency: Red (< 5m in corridor, 0ms instant assertion)
    - Caution: Yellow (< 15m in corridor, OR near corridor box within 12m)
    - Safe: Brass gold / Green (only if path clear and dry)
- Zero emojis
"""

from typing import List, Dict, Tuple, Any, Optional
import time
import cv2
import numpy as np

from core.categories import map_to_target_category, get_target_real_height
from core.collision_zone import CollisionZone
from core.inference_engine import InferenceResult, Detection

# Colors in BGR (OpenCV format)
COLOR_BG_DARK_GREEN = (13, 55, 21)    # #15370D
COLOR_SURFACE_GREEN = (20, 71, 30)    # #1E4714
COLOR_BRASS_GOLD    = (130, 205, 229) # #E5CD82
COLOR_CREAM_YELLOW  = (180, 242, 255) # #FFF2B4
COLOR_CAUTION_YEL   = (10, 214, 255)  # #FFD60A
COLOR_EMERGENCY_RED = (58, 69, 255)   # #FF453A
COLOR_CORRIDOR_LINE = (80, 140, 160)  # Hairline corridor accent


def draw_tesla_corners(
    img: np.ndarray,
    x1: int, y1: int, x2: int, y2: int,
    color: Tuple[int, int, int],
    corner_len: int = 14,
    thickness: int = 2
) -> None:
    """Draw crisp Tesla Autopilot style corner brackets around an object."""
    h, w = img.shape[:2]
    x1 = max(0, min(w - 1, x1))
    x2 = max(0, min(w - 1, x2))
    y1 = max(0, min(h - 1, y1))
    y2 = max(0, min(h - 1, y2))

    bw = x2 - x1
    bh = y2 - y1
    clen = max(6, min(corner_len, bw // 3, bh // 3))

    # Top-Left corner
    cv2.line(img, (x1, y1), (x1 + clen, y1), color, thickness)
    cv2.line(img, (x1, y1), (x1, y1 + clen), color, thickness)

    # Top-Right corner
    cv2.line(img, (x2, y1), (x2 - clen, y1), color, thickness)
    cv2.line(img, (x2, y1), (x2, y1 + clen), color, thickness)

    # Bottom-Left corner
    cv2.line(img, (x1, y2), (x1 + clen, y2), color, thickness)
    cv2.line(img, (x1, y2), (x1, y2 - clen), color, thickness)

    # Bottom-Right corner
    cv2.line(img, (x2, y2), (x2 - clen, y2), color, thickness)
    cv2.line(img, (x2, y2), (x2, y2 - clen), color, thickness)


def compute_box_iou(boxA: List[float], boxB: Tuple[int, int, int, int]) -> float:
    """Calculate IoU between smoothed float box and integer raw detection."""
    xA = max(boxA[0], float(boxB[0]))
    yA = max(boxA[1], float(boxB[1]))
    xB = min(boxA[2], float(boxB[2]))
    yB = min(boxA[3], float(boxB[3]))

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = max(1.0, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1.0, float((boxB[2] - boxB[0]) * (boxB[3] - boxB[1])))

    return interArea / float(boxAArea + boxBArea - interArea)


class DetectionRenderer:
    """
    Renders Tesla vector HUD overlays and aggregates dynamic active objects.
    Includes temporal smoothing and multi-frame tracking to eliminate HUD jitter.
    """

    def __init__(self):
        self.collision_zone = CollisionZone()
        self._tracks: Dict[int, Dict[str, Any]] = {}
        self._next_track_id: int = 1

    def reset(self):
        """Clear temporal tracking memory."""
        self._tracks.clear()
        self._next_track_id = 1

    def process_and_render(
        self,
        frame: np.ndarray,
        inference_result: InferenceResult,
        stopping_multiplier: float = 1.0,
    ) -> Tuple[np.ndarray, Dict[str, Dict[str, Any]], str]:
        """
        Process raw frame and inference detections with anti-jitter smoothing.

        Returns:
            annotated_frame: Frame with smooth Tesla HUD vector overlays.
            active_objects: Dict of {category_name: {"count": int, "closest_m": float}}
                           for objects currently in front of camera.
            overall_severity: "SAFE" | "CAUTION" | "EMERGENCY"
        """
        if frame is None or frame.size == 0:
            return frame, {}, "SAFE"

        out_frame = frame.copy()
        frame_h, frame_w = out_frame.shape[:2]

        # Draw subtle forward driving corridor
        poly = self.collision_zone.get_lane_polygon(frame_w, frame_h, stopping_multiplier=stopping_multiplier)
        cv2.polylines(out_frame, [poly], isClosed=True, color=COLOR_CORRIDOR_LINE, thickness=1, lineType=cv2.LINE_AA)

        # 1. Parse incoming raw detections and compute corridor relations
        raw_candidates = []
        for det in inference_result.detections:
            bx1, by1, bx2, by2 = det.bbox
            bw = max(1, bx2 - bx1)
            bh = max(1, by2 - by1)

            category = map_to_target_category(det.class_name)
            real_h = get_target_real_height(category)
            focal_length_px = frame_w * 0.75
            raw_dist = round(float(np.clip((focal_length_px * real_h) / max(8, bh), 0.5, 60.0)), 1)

            in_corr, _ = self.collision_zone.is_in_driving_corridor(
                bx1, by1, bx2, by2, frame_w, frame_h, stopping_multiplier=stopping_multiplier
            )
            near_corr, _ = self.collision_zone.is_near_driving_corridor(
                bx1, by1, bx2, by2, frame_w, frame_h, stopping_multiplier=stopping_multiplier
            )

            raw_candidates.append({
                "det": det,
                "category": category,
                "raw_dist": raw_dist,
                "in_corridor": in_corr,
                "near_corridor": near_corr,
            })

        # 2. Match raw detections to existing tracked objects using IoU
        matched_track_ids = set()
        matched_cand_indices = set()

        for track_id, track in list(self._tracks.items()):
            best_iou = 0.28
            best_idx = -1
            for i, cand in enumerate(raw_candidates):
                if i in matched_cand_indices:
                    continue
                if cand["category"] != track["category"]:
                    continue
                iou = compute_box_iou(track["smooth_bbox"], cand["det"].bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_idx = i

            if best_idx != -1:
                cand = raw_candidates[best_idx]
                matched_cand_indices.add(best_idx)
                matched_track_ids.add(track_id)

                # Exponential Moving Average (EMA) Coordinate Smoothing (Alpha = 0.70)
                # Eliminates pixel jitter while keeping HUD responsive
                alpha_coord = 0.70
                rb = cand["det"].bbox
                sb = track["smooth_bbox"]
                track["smooth_bbox"] = [
                    alpha_coord * rb[0] + (1.0 - alpha_coord) * sb[0],
                    alpha_coord * rb[1] + (1.0 - alpha_coord) * sb[1],
                    alpha_coord * rb[2] + (1.0 - alpha_coord) * sb[2],
                    alpha_coord * rb[3] + (1.0 - alpha_coord) * sb[3],
                ]

                # Distance EMA Smoothing
                track["smooth_dist"] = round(0.65 * cand["raw_dist"] + 0.35 * track["smooth_dist"], 1)
                track["confidence"] = cand["det"].confidence
                track["hits"] += 1
                track["missed_frames"] = 0
                track["in_corridor"] = cand["in_corridor"]
                track["near_corridor"] = cand["near_corridor"]
            else:
                track["missed_frames"] += 1

        # 3. Retire tracks missing for more than 3 consecutive frames
        for track_id in list(self._tracks.keys()):
            if self._tracks[track_id]["missed_frames"] > 3:
                del self._tracks[track_id]

        # 4. Initialize new tracks for unmatched detections
        for i, cand in enumerate(raw_candidates):
            if i not in matched_cand_indices:
                tid = self._next_track_id
                self._next_track_id += 1
                self._tracks[tid] = {
                    "track_id": tid,
                    "category": cand["category"],
                    "smooth_bbox": [float(c) for c in cand["det"].bbox],
                    "smooth_dist": cand["raw_dist"],
                    "confidence": cand["det"].confidence,
                    "hits": 1,
                    "missed_frames": 0,
                    "in_corridor": cand["in_corridor"],
                    "near_corridor": cand["near_corridor"],
                }

        # 5. Render smoothed tracks and aggregate hazard severity
        active_objects: Dict[str, Dict[str, Any]] = {}
        highest_severity = "SAFE"

        for track_id, track in self._tracks.items():
            sb = track["smooth_bbox"]
            x1 = int(round(sb[0]))
            y1 = int(round(sb[1]))
            x2 = int(round(sb[2]))
            y2 = int(round(sb[3]))
            dist_m = track["smooth_dist"]
            category = track["category"]

            # User Logic Rules 1 & 2:
            # - In corridor < 5m: EMERGENCY (Red, 0ms)
            # - In corridor < 15m: CAUTION (Yellow)
            # - Near corridor box < 12m: CAUTION (Yellow - "If camera can see any object near box keep light to yellow")
            # - Close obstacle in front < 8m: CAUTION (Yellow)
            # - Otherwise: SAFE (Brass gold / Green)
            if track["in_corridor"] and dist_m < (5.0 * stopping_multiplier):
                box_color = COLOR_EMERGENCY_RED
                severity = "EMERGENCY"
                if highest_severity != "EMERGENCY":
                    highest_severity = "EMERGENCY"
            elif track["in_corridor"] and dist_m < 15.0:
                box_color = COLOR_CAUTION_YEL
                severity = "CAUTION"
                if highest_severity == "SAFE":
                    highest_severity = "CAUTION"
            elif track["near_corridor"] and dist_m < 12.0:
                box_color = COLOR_CAUTION_YEL
                severity = "CAUTION"
                if highest_severity == "SAFE":
                    highest_severity = "CAUTION"
            elif dist_m < 8.0:
                box_color = COLOR_CAUTION_YEL
                severity = "CAUTION"
                if highest_severity == "SAFE":
                    highest_severity = "CAUTION"
            else:
                box_color = COLOR_BRASS_GOLD
                severity = "SAFE"

            # 1. Subtle hairline thin bounding box
            cv2.rectangle(out_frame, (x1, y1), (x2, y2), box_color, 1, lineType=cv2.LINE_AA)

            # 2. Bold Tesla vector corner brackets
            draw_tesla_corners(out_frame, x1, y1, x2, y2, box_color, corner_len=14, thickness=2)

            # 3. Clean Tesla-style label badge: "<Category> <Distance>m"
            label = f"{category} {dist_m:.1f}m"
            font_scale = 0.48
            font_thickness = 1
            font_face = cv2.FONT_HERSHEY_SIMPLEX

            (tw, th), _ = cv2.getTextSize(label, font_face, font_scale, font_thickness)
            tag_y1 = max(0, y1 - th - 8)
            tag_y2 = y1
            tag_x1 = x1
            tag_x2 = min(frame_w - 1, x1 + tw + 10)

            # Pill badge background: Yellow/Brass gold (Safe/Caution) or Red (Emergency)
            if severity == "EMERGENCY":
                cv2.rectangle(out_frame, (tag_x1, tag_y1), (tag_x2, tag_y2), COLOR_EMERGENCY_RED, -1)
                text_color = COLOR_CREAM_YELLOW
            elif severity == "CAUTION":
                cv2.rectangle(out_frame, (tag_x1, tag_y1), (tag_x2, tag_y2), COLOR_CAUTION_YEL, -1)
                text_color = COLOR_BG_DARK_GREEN
            else:
                cv2.rectangle(out_frame, (tag_x1, tag_y1), (tag_x2, tag_y2), COLOR_BRASS_GOLD, -1)
                cv2.rectangle(out_frame, (tag_x1, tag_y1), (tag_x2, tag_y2), COLOR_CREAM_YELLOW, 1, lineType=cv2.LINE_AA)
                text_color = COLOR_BG_DARK_GREEN

            text_pos = (tag_x1 + 5, tag_y2 - 4)
            cv2.putText(out_frame, label, text_pos, font_face, font_scale, text_color, font_thickness, cv2.LINE_AA)

            # Aggregate stable dynamic active objects currently in front of camera
            if category not in active_objects:
                active_objects[category] = {"count": 1, "closest_m": dist_m}
            else:
                active_objects[category]["count"] += 1
                if dist_m < active_objects[category]["closest_m"]:
                    active_objects[category]["closest_m"] = dist_m

        return out_frame, active_objects, highest_severity
