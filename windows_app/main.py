"""
SpatialSight — Main entry point for the desktop detection app.

Quick-start validation script that runs YOLOv8n on the built-in webcam
to verify the inference pipeline works on Apple Silicon MPS.

Usage:
    source venv/bin/activate
    python main.py [--source 0] [--model yolov8n.pt]

Controls:
    Q / ESC     — Quit
    C           — Capture current frame to rc_car_dataset/
    +/-         — Increase/decrease confidence threshold
    Z           — Toggle collision warning zone
    SPACE       — Pause/resume
"""

import sys
import os
import time
import argparse
import logging

import cv2
import numpy as np

# Add windows_app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.frame_buffer import FrameBuffer
from core.inference_engine import InferenceEngine, InferenceResult
from core.collision_zone import CollisionZone
from core.adb_bridge import (
    is_adb_available, is_phone_connected, setup_port_forward, get_stream_url,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("SpatialSight")


# ── Color palette for bounding boxes (BGR) ──────────────────────────────────
COLORS = [
    (255, 100, 100), (100, 255, 100), (100, 100, 255),
    (255, 255, 100), (255, 100, 255), (100, 255, 255),
    (200, 150, 50),  (50, 200, 150),  (150, 50, 200),
    (255, 200, 150), (150, 200, 255), (200, 255, 150),
]


def draw_detections(frame: np.ndarray, result: InferenceResult) -> np.ndarray:
    """Draw bounding boxes, labels, and confidence scores on the frame."""
    for det in result.detections:
        x1, y1, x2, y2 = det.bbox
        color = COLORS[det.class_id % len(COLORS)]

        # Bounding box
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # Label background
        label = f"{det.class_name} {det.confidence:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 4, y1), color, -1)

        # Label text
        cv2.putText(
            frame, label, (x1 + 2, y1 - 4),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
        )

    return frame


def draw_hud(
    frame: np.ndarray,
    result: InferenceResult,
    fps: float,
    source_name: str,
    collision_active: bool,
    paused: bool,
) -> np.ndarray:
    """Draw the heads-up display overlay (FPS, object counts, status)."""
    h, w = frame.shape[:2]

    # ── Top-left: FPS and status bar ──
    status_text = f"{fps:.0f} FPS | {result.inference_time_ms:.0f}ms | {source_name}"
    if paused:
        status_text = "PAUSED | " + status_text

    cv2.rectangle(frame, (0, 0), (w, 30), (0, 0, 0), -1)
    cv2.putText(
        frame, status_text, (10, 20),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1,
    )

    # ── Right side: Object count panel ──
    counts = result.count_by_class
    if counts:
        panel_w = 200
        panel_h = 30 + len(counts) * 22 + 10
        px = w - panel_w - 10
        py = 40

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (px, py), (px + panel_w, py + panel_h), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

        cv2.putText(
            frame, f"OBJECTS: {result.total_count}", (px + 8, py + 20),
            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1,
        )

        for i, (cls, count) in enumerate(sorted(counts.items())):
            y = py + 40 + i * 22
            color = COLORS[hash(cls) % len(COLORS)]
            cv2.putText(
                frame, f"{cls}: {count}", (px + 12, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1,
            )

    # ── Bottom: Controls hint ──
    hint = "Q:Quit  C:Capture  +/-:Confidence  Z:CollisionZone  SPACE:Pause"
    cv2.putText(
        frame, hint, (10, h - 10),
        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1,
    )

    return frame


def save_dataset_frame(frame: np.ndarray, result: InferenceResult, dataset_dir: str) -> str:
    """Save a frame and its labels to the RC car dataset directory."""
    os.makedirs(os.path.join(dataset_dir, "images"), exist_ok=True)
    os.makedirs(os.path.join(dataset_dir, "labels"), exist_ok=True)

    timestamp = int(time.time() * 1000)
    img_path = os.path.join(dataset_dir, "images", f"frame_{timestamp}.jpg")
    lbl_path = os.path.join(dataset_dir, "labels", f"frame_{timestamp}.txt")

    cv2.imwrite(img_path, frame)

    # Save YOLO format labels (class_id cx cy w h — all normalized)
    h, w = frame.shape[:2]
    with open(lbl_path, "w") as f:
        for det in result.detections:
            x1, y1, x2, y2 = det.bbox
            cx = ((x1 + x2) / 2) / w
            cy = ((y1 + y2) / 2) / h
            bw = (x2 - x1) / w
            bh = (y2 - y1) / h
            f.write(f"{det.class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}\n")

    return img_path


def resolve_source(source_arg: str) -> tuple[str | int, str]:
    """
    Resolve the video source from the command-line argument.

    Returns:
        (source, display_name) tuple.
    """
    # Check if it's a webcam index
    if source_arg.isdigit():
        idx = int(source_arg)
        return idx, f"Webcam {idx}"

    # Check if it's "usb" — auto-detect phone over ADB
    if source_arg.lower() == "usb":
        if not is_adb_available():
            logger.error("ADB not found! Install with: brew install android-platform-tools")
            sys.exit(1)

        if not is_phone_connected():
            logger.error("No Android phone detected over USB. Enable USB Debugging on the phone.")
            sys.exit(1)

        if not setup_port_forward():
            logger.error("Failed to set up ADB port forwarding")
            sys.exit(1)

        url = get_stream_url()
        return url, "USB Phone"

    # Assume it's a URL or file path
    return source_arg, source_arg


def main():
    parser = argparse.ArgumentParser(description="SpatialSight — Object Detection Engine")
    parser.add_argument(
        "--source", default="0",
        help="Video source: webcam index (0), 'usb' for phone, URL, or file path",
    )
    parser.add_argument(
        "--model", default="yolov8n.pt",
        help="Path to YOLO model weights (default: yolov8n.pt, auto-downloads)",
    )
    parser.add_argument(
        "--confidence", type=float, default=0.45,
        help="Detection confidence threshold (0.0-1.0)",
    )
    parser.add_argument(
        "--dataset-dir", default="rc_car_dataset",
        help="Directory to save captured dataset frames",
    )
    args = parser.parse_args()

    # ── Resolve video source ──
    source, source_name = resolve_source(args.source)
    logger.info(f"Video source: {source_name}")

    # ── Load YOLO model ──
    engine = InferenceEngine()
    engine.set_confidence(args.confidence)

    logger.info(f"Loading model: {args.model}")
    if not engine.load_model(args.model):
        logger.error("Failed to load model. Exiting.")
        sys.exit(1)

    logger.info(f"Model loaded — {len(engine.class_names)} classes on {engine.device}")

    # ── Start frame buffer ──
    buffer = FrameBuffer(source)
    buffer.start()

    # Wait for first frame
    logger.info("Waiting for video connection...")
    timeout = time.monotonic() + 15.0
    while buffer.read() is None and time.monotonic() < timeout:
        time.sleep(0.1)

    if buffer.read() is None:
        logger.error(f"Could not connect to video source: {source}")
        buffer.stop()
        sys.exit(1)

    logger.info("Video connected! Starting detection loop...")

    # ── Detection loop ──
    collision_zone = CollisionZone()
    show_collision_zone = False
    paused = False
    last_result = InferenceResult()
    frame_count = 0
    fps_timer = time.monotonic()
    display_fps = 0.0

    window_name = "SpatialSight — Object Detection"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    try:
        while True:
            # Handle keyboard input
            key = cv2.waitKey(1) & 0xFF

            if key in (ord("q"), ord("Q"), 27):  # Q or ESC
                break
            elif key == ord(" "):  # Space — pause/resume
                paused = not paused
                logger.info("Paused" if paused else "Resumed")
            elif key in (ord("c"), ord("C")):  # Capture dataset frame
                frame = buffer.read()
                if frame is not None:
                    path = save_dataset_frame(frame, last_result, args.dataset_dir)
                    logger.info(f"Dataset frame saved: {path}")
            elif key == ord("+") or key == ord("="):  # Increase confidence
                new_conf = min(0.95, engine._confidence + 0.05)
                engine.set_confidence(new_conf)
                logger.info(f"Confidence threshold: {new_conf:.0%}")
            elif key == ord("-"):  # Decrease confidence
                new_conf = max(0.05, engine._confidence - 0.05)
                engine.set_confidence(new_conf)
                logger.info(f"Confidence threshold: {new_conf:.0%}")
            elif key in (ord("z"), ord("Z")):  # Toggle collision zone
                show_collision_zone = not show_collision_zone
                logger.info(f"Collision zone: {'ON' if show_collision_zone else 'OFF'}")

            if paused:
                time.sleep(0.03)
                continue

            # Get latest frame
            frame = buffer.read()
            if frame is None:
                time.sleep(0.01)
                continue

            # Run inference
            result = engine.infer(frame)
            last_result = result

            # Draw detections
            display_frame = draw_detections(frame.copy(), result)

            # Collision zone
            alerts = []
            if show_collision_zone:
                alerts = collision_zone.check_hazards(result.detections, frame.shape)
                display_frame = collision_zone.draw_zone(display_frame, alerts)

            # FPS tracking
            frame_count += 1
            elapsed = time.monotonic() - fps_timer
            if elapsed >= 1.0:
                display_fps = frame_count / elapsed
                frame_count = 0
                fps_timer = time.monotonic()

            # Draw HUD
            display_frame = draw_hud(
                display_frame, result, display_fps, source_name,
                show_collision_zone, paused,
            )

            # Show frame
            cv2.imshow(window_name, display_frame)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        buffer.stop()
        cv2.destroyAllWindows()
        logger.info("SpatialSight shutdown complete")


if __name__ == "__main__":
    main()
