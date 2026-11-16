"""Unit tests for Keyframe Selector, Sensor Triggers, and World Angle Estimation."""

import pytest
import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from spatial.keyframe_selector import KeyframeSelector, SensorData


def test_keyframe_trigger_logic():
    selector = KeyframeSelector(yaw_threshold=30.0, pitch_threshold=20.0, min_interval=0.0)
    selector.start_scan()

    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # 1. First frame should always trigger
    s0 = SensorData(yaw=0.0, pitch=0.0, roll=0.0)
    assert selector.should_capture(s0) is True
    kf0 = selector.capture(dummy_frame, s0)
    assert kf0.index == 0

    # 2. Minor rotation (10°) should NOT trigger (threshold is 30°)
    s1 = SensorData(yaw=10.0, pitch=0.0, roll=0.0)
    assert selector.should_capture(s1) is False

    # 3. Rotation of 35° >= 30° SHOULD trigger
    s2 = SensorData(yaw=35.0, pitch=0.0, roll=0.0)
    assert selector.should_capture(s2) is True
    kf1 = selector.capture(dummy_frame, s2)
    assert kf1.index == 1

    # 4. Vertical pitch tilt of 25° >= 20° SHOULD trigger even if yaw is unchanged
    s3 = SensorData(yaw=35.0, pitch=25.0, roll=0.0)
    assert selector.should_capture(s3) is True


def test_object_world_angle_estimation():
    selector = KeyframeSelector(camera_hfov=60.0)
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Keyframe pointing North (yaw = 0°)
    kf = selector.capture(dummy_frame, SensorData(yaw=0.0, pitch=0.0, roll=0.0))

    # Object in exact center of frame (320 px out of 640 px) -> world angle = 0°
    angle_center = selector.estimate_object_world_angle(kf, bbox_center_x=320, frame_width=640)
    assert angle_center == pytest.approx(0.0, abs=0.5)

    # Object at right edge of frame (640 px) -> offset = +30° -> world angle = 30°
    angle_right = selector.estimate_object_world_angle(kf, bbox_center_x=640, frame_width=640)
    assert angle_right == pytest.approx(30.0, abs=0.5)

    # Object at left edge of frame (0 px) -> offset = -30° -> world angle = 330°
    angle_left = selector.estimate_object_world_angle(kf, bbox_center_x=0, frame_width=640)
    assert angle_left == pytest.approx(330.0, abs=0.5)


def test_coverage_percentage():
    selector = KeyframeSelector(camera_hfov=60.0, yaw_threshold=30.0, min_interval=0.0)
    selector.start_scan()
    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    assert selector.get_coverage_percentage() == 0.0

    # Capture 1 keyframe at 0° (covers -30° to +30° = 61 angles)
    selector.capture(dummy_frame, SensorData(yaw=0.0, pitch=0.0, roll=0.0))
    cov1 = selector.get_coverage_percentage()
    assert 15.0 < cov1 < 20.0

    # Capture full sweep every 30°
    for angle in range(30, 360, 30):
        selector.capture(dummy_frame, SensorData(yaw=float(angle), pitch=0.0, roll=0.0))

    cov_full = selector.get_coverage_percentage()
    assert cov_full == pytest.approx(100.0, abs=0.5)
