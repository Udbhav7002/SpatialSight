import math
import cv2
import numpy as np
from typing import List

from spatial.keyframe_selector import Keyframe
from spatial.angular_dedup import SpatialObject

class RoomMapRenderer:
    def __init__(self, size=800, radius=300):
        self.size = size
        self.radius = radius
        self.center = (size // 2, size // 2)
        
        # Color map for common classes
        self.color_map = {
            'person': (0, 0, 255),    # Red
            'chair': (255, 0, 0),     # Blue
            'table': (0, 255, 0),     # Green
            'door': (0, 255, 255),    # Yellow
            'bottle': (255, 255, 0),  # Cyan
            'laptop': (255, 0, 255),  # Magenta
            'car': (128, 128, 128),
        }

    def _get_color(self, class_name: str):
        return self.color_map.get(class_name.lower(), (200, 200, 200)) # Default light gray

    def render(self, keyframes: List[Keyframe], spatial_objects: List[SpatialObject], coverage_pct: float) -> np.ndarray:
        # Create a black image
        img = np.zeros((self.size, self.size, 3), dtype=np.uint8)

        # Draw room boundary
        cv2.circle(img, self.center, self.radius, (100, 100, 100), 2)
        
        # Draw camera center
        cv2.circle(img, self.center, 5, (255, 255, 255), -1)

        # Calculate coverage arcs and draw them
        for kf in keyframes:
            yaw = kf.sensor.yaw
            # convert yaw (0-360) where 0 is up, clockwise
            angle_rad = math.radians(yaw - 90)
            
            end_x = int(self.center[0] + self.radius * math.cos(angle_rad))
            end_y = int(self.center[1] + self.radius * math.sin(angle_rad))
            
            cv2.line(img, self.center, (end_x, end_y), (50, 50, 50), 1)

            # Draw FOV arc (assume 65 degree FOV)
            start_angle = yaw - 90 - 32.5
            end_angle = yaw - 90 + 32.5
            cv2.ellipse(img, self.center, (self.radius, self.radius), 0, start_angle, end_angle, (80, 80, 80), 2)

        # Draw Spatial Objects
        for obj in spatial_objects:
            color = self._get_color(obj.class_name)
            angle_rad = math.radians(obj.world_angle - 90)
            
            obj_x = int(self.center[0] + self.radius * math.cos(angle_rad))
            obj_y = int(self.center[1] + self.radius * math.sin(angle_rad))
            
            cv2.circle(img, (obj_x, obj_y), 10, color, -1)
            
            # Label
            cv2.putText(img, obj.class_name, (obj_x + 15, obj_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Add title
        title = f'Room Map - {len(spatial_objects)} unique objects ({coverage_pct:.1f}% coverage)'
        cv2.putText(img, title, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        # Draw Legend
        legend_y = self.size - 20 - len(self.color_map) * 20
        cv2.putText(img, "Legend:", (20, legend_y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        for i, (cls_name, color) in enumerate(self.color_map.items()):
            y_pos = legend_y + 20 + i * 20
            cv2.circle(img, (30, y_pos - 5), 5, color, -1)
            cv2.putText(img, cls_name, (45, y_pos), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        return img
