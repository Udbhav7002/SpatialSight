"""Unit tests for Angular Deduplication and Spatial Object Merging."""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from spatial.angular_dedup import AngularDeduplicator, SpatialObject


def test_dedup_merges_same_object():
    dedup = AngularDeduplicator(merge_threshold=15.0)

    # Keyframe 1: detects chair at angle 40°
    obj1 = dedup.add_detection("chair", world_angle=40.0, confidence=0.85, keyframe_index=0)
    assert obj1.object_id == 0
    assert obj1.sighting_count == 1

    # Keyframe 2: detects chair at angle 44° (delta = 4° <= 15°) -> SAME chair!
    obj2 = dedup.add_detection("chair", world_angle=44.0, confidence=0.90, keyframe_index=1)
    assert obj2.object_id == 0  # Same physical object merged
    assert obj2.sighting_count == 2
    assert obj2.confidence == 0.90  # Keeps best confidence

    inventory = dedup.get_inventory()
    assert inventory["chair"] == 1


def test_dedup_separates_different_objects():
    dedup = AngularDeduplicator(merge_threshold=15.0)

    # Chair 1 at 30°
    dedup.add_detection("chair", world_angle=30.0, confidence=0.85, keyframe_index=0)
    # Chair 2 across room at 180° (delta = 150° > 15°) -> Different physical chair!
    dedup.add_detection("chair", world_angle=180.0, confidence=0.88, keyframe_index=2)

    inventory = dedup.get_inventory()
    assert inventory["chair"] == 2
    assert dedup.get_total_unique_count() == 2


def test_dedup_wraparound_difference():
    dedup = AngularDeduplicator(merge_threshold=15.0)

    # Object at 355° (near North from West)
    obj1 = dedup.add_detection("table", world_angle=355.0, confidence=0.80, keyframe_index=0)

    # Object at 5° (near North from East)
    # Angular difference across 0° is 10° <= 15° -> Should be MERGED!
    obj2 = dedup.add_detection("table", world_angle=5.0, confidence=0.92, keyframe_index=1)

    assert obj2.object_id == obj1.object_id
    assert dedup.get_inventory()["table"] == 1


def test_dedup_multiple_classes():
    dedup = AngularDeduplicator(merge_threshold=15.0)

    # Chair at 45°
    dedup.add_detection("chair", world_angle=45.0, confidence=0.80, keyframe_index=0)
    # Table at 46° (same angle, but different class -> distinct objects!)
    dedup.add_detection("table", world_angle=46.0, confidence=0.85, keyframe_index=0)

    inventory = dedup.get_inventory()
    assert inventory["chair"] == 1
    assert inventory["table"] == 1
    assert dedup.get_total_unique_count() == 2
