"""
Room Map Renderer - High-resolution 2D Polar Radar and Spatial Map Visualization.

Renders:
- Polar radar grid with distance rings (1m, 2m, 3m) and compass directions (N, S, E, W)
- Active camera field-of-view (FOV) cone pointing in the current phone yaw direction
- Locked keyframe capture sectors showing covered slices of the room
- Spatially deduplicated objects plotted at their estimated world azimuths with class tags
- Legend and coverage statistics banner
"""

import math
from typing import List, Optional
import cv2
import numpy as np

from spatial.keyframe_selector import Keyframe
from spatial.angular_dedup import SpatialObject


class RoomMapRenderer:
    """Renders 2D top-down polar room radar visualizations."""

    def __init__(self, size: int = 700, radius: int = 260):
        self.size = size
        self.radius = radius
        self.center = (size // 2, size // 2)

        # Distinct BGR color palette for detected classes
        self.color_map = {
            'person': (0, 80, 255),       # Orange-Red
            'chair': (255, 200, 0),       # Cyan-Blue
            'couch': (255, 120, 0),       # Deep Blue
            'sofa': (255, 120, 0),
            'bed': (180, 0, 255),         # Purple
            'dining table': (0, 220, 100), # Green
            'table': (0, 220, 100),
            'laptop': (255, 0, 200),      # Magenta
            'tv': (200, 255, 0),          # Aqua
            'bottle': (0, 255, 255),      # Yellow
            'cup': (0, 255, 255),
            'backpack': (50, 180, 255),   # Amber
            'potted plant': (80, 220, 80),# Forest Green
            'door': (100, 200, 255),
            'car': (160, 160, 160),
        }

    def _get_color(self, class_name: str) -> tuple:
        return self.color_map.get(class_name.lower(), (0, 230, 255))

    # Angular window (degrees) within which same-class sightings are merged
    # into a single radar marker.
    CLUSTER_DEG = 35.0

    def _cluster_objects(self, spatial_objects) -> list[tuple[str, float, int]]:
        """
        Group same-class sightings by angular proximity.

        Sightings are sorted on the circle and split into clusters wherever a
        gap between consecutive sightings exceeds CLUSTER_DEG. Returns a list
        of (class_name, mean_angle, count) tuples; means are circular so
        clusters are correct across the 0/360 wraparound.
        """
        by_class: dict[str, list] = {}
        for obj in spatial_objects:
            by_class.setdefault(obj.class_name, []).append(obj.world_angle)

        clusters: list[tuple[str, float, int]] = []
        for cls_name, angles in by_class.items():
            if len(angles) == 1:
                clusters.append((cls_name, angles[0] % 360.0, 1))
                continue

            sorted_angles = sorted(a % 360.0 for a in angles)
            # Split where the gap between consecutive sightings is too large
            groups: list[list[float]] = [[sorted_angles[0]]]
            for prev, cur in zip(sorted_angles, sorted_angles[1:]):
                if cur - prev > self.CLUSTER_DEG:
                    groups.append([cur])
                else:
                    groups[-1].append(cur)

            # Wraparound: merge the last group into the first if they are close
            if len(groups) > 1:
                wrap_gap = (sorted_angles[0] + 360.0) - sorted_angles[-1]
                if wrap_gap <= self.CLUSTER_DEG:
                    groups[0] = groups.pop() + groups[0]

            for group in groups:
                clusters.append((cls_name, self._circular_mean(group), len(group)))
        return clusters

    @staticmethod
    def _angle_diff(a: float, b: float) -> float:
        """Signed shortest difference between two angles in degrees."""
        d = (a - b + 180.0) % 360.0 - 180.0
        return d

    @staticmethod
    def _circular_mean(angles: list[float]) -> float:
        x = sum(math.cos(math.radians(a)) for a in angles)
        y = sum(math.sin(math.radians(a)) for a in angles)
        return math.degrees(math.atan2(y, x)) % 360.0

    def render(
        self,
        keyframes: List[Keyframe],
        spatial_objects: List[SpatialObject],
        coverage_pct: float,
        current_yaw: Optional[float] = None,
        is_scanning: bool = False
    ) -> np.ndarray:
        """
        Render the polar radar map.
        Can render both static completed maps and live scanning states with current yaw.
        """
        img = np.zeros((self.size, self.size, 3), dtype=np.uint8)
        img[:] = (23, 21, 21)  # Apple dark background (#151517)

        cx, cy = self.center

        # 1. Concentric Distance Rings
        for r_frac, label in [(0.33, "1m"), (0.66, "2m"), (1.0, "3m")]:
            r_px = int(self.radius * r_frac)
            cv2.circle(img, self.center, r_px, (60, 58, 58), 1, cv2.LINE_AA)
            cv2.putText(img, label, (cx + 5, cy - r_px + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (110, 108, 106), 1)

        # 2. Polar Axis Crosshairs & Compass Bearings
        cv2.line(img, (cx, cy - self.radius - 15), (cx, cy + self.radius + 15), (60, 58, 58), 1)
        cv2.line(img, (cx - self.radius - 15, cy), (cx + self.radius + 15, cy), (60, 58, 58), 1)

        font = cv2.FONT_HERSHEY_SIMPLEX
        compass_color = (166, 161, 161)  # #A1A1A6 secondary text
        # Compass labels drawn INSIDE the ring so they never collide with
        # the header banner or object labels.
        cv2.putText(img, "N", (cx - 5, cy - self.radius + 18), font, 0.5, compass_color, 1)
        cv2.putText(img, "S", (cx - 5, cy + self.radius - 10), font, 0.5, compass_color, 1)
        cv2.putText(img, "E", (cx + self.radius - 16, cy + 5), font, 0.5, compass_color, 1)
        cv2.putText(img, "W", (cx - self.radius + 6, cy + 5), font, 0.5, compass_color, 1)
        cv2.putText(img, "0", (cx - 18, cy - self.radius + 34), font, 0.35, (110, 108, 106), 1)
        cv2.putText(img, "180", (cx - 22, cy + self.radius - 24), font, 0.35, (110, 108, 106), 1)
        cv2.putText(img, "90", (cx + self.radius - 30, cy + 20), font, 0.35, (110, 108, 106), 1)
        cv2.putText(img, "270", (cx - self.radius + 8, cy + 20), font, 0.35, (110, 108, 106), 1)

        # 3. Captured Keyframe Frustums / Sectors
        for kf in keyframes:
            yaw = kf.sensor.yaw
            angle_rad = math.radians(yaw - 90)
            end_x = int(cx + self.radius * math.cos(angle_rad))
            end_y = int(cy + self.radius * math.sin(angle_rad))

            # Ray line
            cv2.line(img, self.center, (end_x, end_y), (40, 100, 60), 1, cv2.LINE_AA)

            # Arc wedge for keyframe FOV (approx 65 deg)
            start_angle = yaw - 90 - 32.5
            end_angle = yaw - 90 + 32.5
            cv2.ellipse(img, self.center, (self.radius, self.radius), 0,
                        start_angle, end_angle, (35, 140, 60), 2, cv2.LINE_AA)

        # 4. Live Active Camera Frustum Cone (if scanning)
        if current_yaw is not None and is_scanning:
            rad_center = math.radians(current_yaw - 90)
            rad_left = math.radians(current_yaw - 90 - 32.5)
            rad_right = math.radians(current_yaw - 90 + 32.5)

            p_left = (int(cx + self.radius * math.cos(rad_left)), int(cy + self.radius * math.sin(rad_left)))
            p_right = (int(cx + self.radius * math.cos(rad_right)), int(cy + self.radius * math.sin(rad_right)))

            # Semi-transparent cone overlay
            overlay = img.copy()
            cone_pts = np.array([self.center, p_left, p_right], dtype=np.int32)
            cv2.fillPoly(overlay, [cone_pts], (180, 120, 20))
            cv2.addWeighted(overlay, 0.35, img, 0.65, 0, img)

            # Pointer line
            tip_x = int(cx + (self.radius + 8) * math.cos(rad_center))
            tip_y = int(cy + (self.radius + 8) * math.sin(rad_center))
            cv2.line(img, self.center, (tip_x, tip_y), (255, 200, 50), 2, cv2.LINE_AA)

        # 5. Central Observer Point (Phone/Mac)
        cv2.circle(img, self.center, 7, (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(img, self.center, 3, (0, 120, 255), -1, cv2.LINE_AA)

        # 6. Spatial Objects Plotted on Radar (clustered by class and angle)
        #    Same-class sightings within CLUSTER_DEG of each other are drawn
        #    as a single marker with a count, so one physical object never
        #    appears as a ring of duplicate dots.
        clusters = self._cluster_objects(spatial_objects)
        dist_px = int(self.radius * 0.85)
        for cls_name, ang, count in clusters:
            color = self._get_color(cls_name)
            angle_rad = math.radians(ang - 90)
            ox = int(cx + dist_px * math.cos(angle_rad))
            oy = int(cy + dist_px * math.sin(angle_rad))

            dot_r = 8 if count == 1 else 10
            cv2.circle(img, (ox, oy), dot_r, color, -1, cv2.LINE_AA)
            cv2.circle(img, (ox, oy), dot_r + 2, (245, 245, 245), 1, cv2.LINE_AA)

            # Text label with background box for legibility
            if count > 1:
                label = f"{cls_name} x{count} ({ang:.0f} deg)"
            else:
                label = f"{cls_name} ({ang:.0f} deg)"
            (tw, th), _ = cv2.getTextSize(label, font, 0.42, 1)

            # Position text offset so it doesn't collide with center,
            # then clamp so it never runs off the canvas.
            tx = ox + 12 if ox >= cx else ox - tw - 12
            ty = oy + th // 2
            tx = max(6, min(self.size - tw - 6, tx))
            ty = max(70, min(self.size - 24, ty))

            cv2.rectangle(img, (tx - 3, ty - th - 3), (tx + tw + 3, ty + 4), (15, 15, 15), -1)
            cv2.putText(img, label, (tx, ty), font, 0.42, color, 1, cv2.LINE_AA)

        # 7. Header Banner: Coverage & Unique Count
        status_str = "SCANNING..." if is_scanning else "SCAN COMPLETE"
        status_color = (10, 214, 255) if is_scanning else (88, 209, 48)  # Apple yellow / green
        cv2.putText(img, f"SPATIAL RADAR - {status_str}", (20, 32), font, 0.6, status_color, 2, cv2.LINE_AA)

        stats_str = f"Coverage: {coverage_pct:.1f}% | Unique Items: {len(spatial_objects)} | Keyframes: {len(keyframes)}"
        cv2.putText(img, stats_str, (20, 56), font, 0.45, (166, 161, 161), 1, cv2.LINE_AA)

        # 8. Compact Legend at Bottom-Left
        active_classes = sorted(list(set(o.class_name for o in spatial_objects)))
        if active_classes:
            legend_y = self.size - 18 - (len(active_classes) * 18)
            cv2.putText(img, "Detected Objects:", (20, legend_y), font, 0.45, (166, 161, 161), 1)
            for i, cls_name in enumerate(active_classes):
                col = self._get_color(cls_name)
                y_pos = legend_y + 18 + (i * 18)
                cv2.circle(img, (26, y_pos - 4), 4, col, -1)
                cv2.putText(img, cls_name.capitalize(), (36, y_pos), font, 0.4, (245, 245, 245), 1)

        return img
