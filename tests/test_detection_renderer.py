"""Unit tests for DetectionRenderer, Tesla Vector Bounding Boxes, and Active Objects."""

import pytest
import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from core.inference_engine import InferenceResult, Detection
from ui.detection_renderer import DetectionRenderer, draw_tesla_corners


def test_draw_tesla_corners_bounds():
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    # Drawing within frame bounds should not crash
    draw_tesla_corners(img, 50, 50, 200, 200, (130, 205, 229), corner_len=14, thickness=2)
    # Drawing edge-case coordinates should clamp and not crash
    draw_tesla_corners(img, -10, -10, 700, 500, (130, 205, 229), corner_len=14, thickness=2)


def test_detection_renderer_empty_frame():
    renderer = DetectionRenderer()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    empty_result = InferenceResult()

    out_frame, active_objects, severity = renderer.process_and_render(frame, empty_result)
    assert out_frame.shape == frame.shape
    assert len(active_objects) == 0
    assert severity == "SAFE"


def test_detection_renderer_dynamic_active_objects():
    renderer = DetectionRenderer()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # 2 pedestrians + 1 car
    det_person1 = Detection(class_id=0, class_name="person", confidence=0.88, bbox=(100, 100, 150, 260), center=(125, 180))
    det_person2 = Detection(class_id=0, class_name="person", confidence=0.91, bbox=(200, 120, 250, 280), center=(225, 200))
    det_car = Detection(class_id=2, class_name="car", confidence=0.95, bbox=(800, 400, 1050, 600), center=(925, 500))

    result = InferenceResult(detections=[det_person1, det_person2, det_car])
    out_frame, active_objects, severity = renderer.process_and_render(frame, result)

    # Page 2 Rule: Only display objects that are currently in front of camera
    assert "person" in active_objects
    assert active_objects["person"]["count"] == 2
    assert "Car" in active_objects
    assert active_objects["Car"]["count"] == 1
    # Other categories should NOT be present
    assert "Bike" not in active_objects
    assert "Truck" not in active_objects


def test_detection_renderer_hazard_corridor_severity():
    renderer = DetectionRenderer()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cx = 1280 // 2

    # Obstacle directly in forward corridor at bumper (<5m -> EMERGENCY)
    det_close = Detection(
        class_id=2, class_name="car", confidence=0.90,
        bbox=(cx - 150, 350, cx + 150, 700),
        center=(cx, 525)
    )

    result = InferenceResult(detections=[det_close])
    out_frame, active_objects, severity = renderer.process_and_render(frame, result)
    assert severity == "EMERGENCY"
    assert "Car" in active_objects


def test_detection_renderer_near_corridor_caution():
    """Rule 2: Object near the driving corridor box triggers CAUTION (Yellow)."""
    renderer = DetectionRenderer()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    cx = 1280 // 2

    # Place an object adjacent to the corridor (near the lane, dist < 12m)
    # Corridor top is around y=316 (w=460 -> x=410..870), bottom is y=691 (w=793 -> x=243..1036)
    # Place object at x=190..310, y=450..650 (near left edge of corridor)
    det_near = Detection(
        class_id=0, class_name="person", confidence=0.85,
        bbox=(200, 420, 270, 620),
        center=(235, 520)
    )

    result = InferenceResult(detections=[det_near])
    out_frame, active_objects, severity = renderer.process_and_render(frame, result)
    assert severity == "CAUTION"
    assert "person" in active_objects


def test_detection_renderer_anti_jitter_ema_smoothing():
    """Anti-Jitter: Coordinates and distances are smoothly filtered across frames."""
    renderer = DetectionRenderer()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # Frame 1: Detection at (100, 100, 200, 300)
    det1 = Detection(class_id=28, class_name="suitcase", confidence=0.90, bbox=(100, 100, 200, 300), center=(150, 200))
    renderer.process_and_render(frame, InferenceResult(detections=[det1]))
    track1 = list(renderer._tracks.values())[0]
    initial_bbox = list(track1["smooth_bbox"])

    # Frame 2: Jitter jump by 20px to (120, 110, 220, 310)
    det2 = Detection(class_id=28, class_name="suitcase", confidence=0.90, bbox=(120, 110, 220, 310), center=(170, 210))
    renderer.process_and_render(frame, InferenceResult(detections=[det2]))
    track2 = list(renderer._tracks.values())[0]

    # Smoothed x1 should be between initial (100) and new (120), specifically 0.7*120 + 0.3*100 = 114
    assert 100 < track2["smooth_bbox"][0] < 120
    assert abs(track2["smooth_bbox"][0] - 114.0) < 1.0


def test_detection_renderer_dropout_hysteresis():
    """Anti-Jitter: 1-frame dropout does not abruptly erase active objects."""
    renderer = DetectionRenderer()
    frame = np.zeros((720, 1280, 3), dtype=np.uint8)

    # Frame 1: Detected
    det = Detection(class_id=0, class_name="person", confidence=0.88, bbox=(100, 100, 160, 280), center=(130, 190))
    _, active_1, _ = renderer.process_and_render(frame, InferenceResult(detections=[det]))
    assert "person" in active_1

    # Frame 2: Momentary 1-frame network/detector dropout (empty detections)
    _, active_2, _ = renderer.process_and_render(frame, InferenceResult(detections=[]))
    # Track persists through single frame dropout
    assert "person" in active_2
