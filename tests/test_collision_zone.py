"""Unit tests for ADAS Collision Zone, Corridor Geometry, and Pinhole Distance Estimation."""

import pytest
import sys
import os
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from core.collision_zone import CollisionZone
from core.inference_engine import Detection


def test_pinhole_distance_estimation():
    zone = CollisionZone()
    frame_w = 1280

    # Person (real height 1.70m)
    # Focal length px = 1280 * 0.75 = 960 px
    # At 10m away: bbox_h = (960 * 1.70) / 10 = 163.2 px
    dist = zone.estimate_distance("person", 163, frame_w)
    assert dist == pytest.approx(10.0, abs=0.5)

    # Car (real height 1.50m)
    # At 20m away: bbox_h = (960 * 1.50) / 20 = 72 px
    dist_car = zone.estimate_distance("car", 72, frame_w)
    assert dist_car == pytest.approx(20.0, abs=0.8)

    # Clamping test: should not go below 0.5m or above 60.0m
    dist_near = zone.estimate_distance("car", 2000, frame_w)
    assert dist_near >= 0.5

    dist_far = zone.estimate_distance("car", 2, frame_w)
    assert dist_far <= 60.0


def test_driving_corridor_filtering():
    zone = CollisionZone()
    frame_w = 1280
    frame_h = 720

    # 1. Obstacle directly in lane center near bottom
    cx = frame_w // 2
    in_lane, overlap = zone.is_in_driving_corridor(cx - 50, int(frame_h * 0.7), cx + 50, int(frame_h * 0.85), frame_w, frame_h)
    assert in_lane is True
    assert overlap > 0.5

    # 2. Parked vehicle on extreme left side (should be filtered out)
    in_lane_left, overlap_left = zone.is_in_driving_corridor(20, int(frame_h * 0.6), 180, int(frame_h * 0.8), frame_w, frame_h)
    assert in_lane_left is False
    assert overlap_left < 0.2

    # 3. Parked vehicle on extreme right side (should be filtered out)
    in_lane_right, overlap_right = zone.is_in_driving_corridor(frame_w - 180, int(frame_h * 0.6), frame_w - 20, int(frame_h * 0.8), frame_w, frame_h)
    assert in_lane_right is False
    assert overlap_right < 0.2


def test_hazard_severity_levels():
    zone = CollisionZone()
    frame_shape = (720, 1280, 3)

    # Close obstacle directly in lane (<5m)
    # bbox height ~350px -> close
    cx = 1280 // 2
    det_close = Detection(
        class_id=2, class_name="car", confidence=0.92,
        bbox=(cx - 150, 350, cx + 150, 700),
        center=(cx, 525)
    )

    alerts = zone.check_hazards([det_close], frame_shape, stopping_multiplier=1.0)
    assert len(alerts) >= 1
    # Very close obstacle in lane should trigger HIGH severity
    assert alerts[0].severity == "HIGH"
    assert alerts[0].distance_m < 6.0
