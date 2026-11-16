"""
Generate Demo Driving Asset Video - Synthesizes a clean driving lane simulation video
for classroom presentations and automated ADAS corridor verification.
"""

import os
import cv2
import numpy as np


def generate_driving_demo_video(output_path: str = "assets/demo_driving.mp4", duration_sec: int = 12, fps: int = 30):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    w, h = 1280, 720
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, float(fps), (w, h))

    total_frames = duration_sec * fps

    # Horizon line
    horizon_y = int(h * 0.42)

    for f in range(total_frames):
        frame = np.zeros((h, w, 3), dtype=np.uint8)

        # 1. Sky & Horizon
        frame[0:horizon_y, :] = (60, 50, 45)  # Dark muted evening sky
        # 2. Road Asphalt
        frame[horizon_y:h, :] = (40, 42, 45)

        # 3. Road Side Grass / Shoulders
        cv2.fillPoly(frame, [np.array([(0, horizon_y), (int(w * 0.22), horizon_y), (0, h)], dtype=np.int32)], (30, 55, 30))
        cv2.fillPoly(frame, [np.array([(int(w * 0.78), horizon_y), (w, horizon_y), (w, h)], dtype=np.int32)], (30, 55, 30))

        # 4. Animated Center Dashed Line
        dash_offset = (f * 12) % 60
        for y_dash in range(horizon_y + 10 + dash_offset, h, 60):
            t = (y_dash - horizon_y) / float(h - horizon_y)
            dash_w = int(2 + t * 8)
            dash_len = int(8 + t * 25)
            cx = w // 2
            cv2.line(frame, (cx, y_dash), (cx, min(h, y_dash + dash_len)), (255, 255, 255), dash_w)

        # 5. Lane Boundary Lines (Solid White / Yellow)
        cv2.line(frame, (int(w * 0.36), horizon_y), (int(w * 0.18), h), (200, 200, 200), 3, cv2.LINE_AA)
        cv2.line(frame, (int(w * 0.64), horizon_y), (int(w * 0.82), h), (200, 200, 200), 3, cv2.LINE_AA)

        # 6. Approaching Simulated Vehicle Ahead (Cycles every 6 seconds)
        cycle_t = (f % (fps * 6)) / float(fps * 6)  # 0.0 (far) to 1.0 (close)
        
        # Vehicle scales from horizon down to bumper
        car_y = int(horizon_y + (h * 0.45) * (cycle_t ** 1.3))
        car_w = int(40 + 260 * (cycle_t ** 1.3))
        car_h = int(30 + 170 * (cycle_t ** 1.3))
        car_x = (w // 2) - (car_w // 2)

        # Draw vehicle body (Car silhouette)
        car_color = (180, 50, 40)  # Red car
        cv2.rectangle(frame, (car_x, car_y), (car_x + car_w, car_y + car_h), car_color, -1)
        # Windshield
        win_w = int(car_w * 0.75)
        win_h = int(car_h * 0.35)
        win_x = car_x + (car_w - win_w) // 2
        win_y = car_y + int(car_h * 0.15)
        cv2.rectangle(frame, (win_x, win_y), (win_x + win_w, win_y + win_h), (80, 90, 100), -1)
        # Taillights
        light_w = max(4, int(car_w * 0.15))
        light_h = max(3, int(car_h * 0.12))
        cv2.rectangle(frame, (car_x + 5, car_y + car_h - light_h - 4), (car_x + 5 + light_w, car_y + car_h - 4), (0, 0, 255), -1)
        cv2.rectangle(frame, (car_x + car_w - 5 - light_w, car_y + car_h - light_h - 4), (car_x + car_w - 5, car_y + car_h - 4), (0, 0, 255), -1)

        # 7. Speedometer / HUD Watermark
        cv2.putText(frame, "SPATIALSIGHT SYNTHETIC ADAS ROAD SIMULATOR", (20, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2)

        out.write(frame)

    out.release()
    print(f"Generated demo video: {output_path} ({total_frames} frames)")


if __name__ == "__main__":
    generate_driving_demo_video("mac_app/assets/demo_driving.mp4")
