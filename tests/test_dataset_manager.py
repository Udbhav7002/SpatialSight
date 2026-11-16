"""Unit tests for Dataset Manager and YOLO Label Normalization."""

import pytest
import sys
import os
import shutil
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from core.dataset_manager import DatasetManager
from core.inference_engine import Detection


def test_capture_frame_with_dataclasses(tmp_path):
    test_dir = str(tmp_path / "test_dataset")
    mgr = DatasetManager(dataset_dir=test_dir)

    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    # Create Detection dataclasses
    # Object 1: class 2 (car), centered at (320, 240), width 160, height 120
    det1 = Detection(
        class_id=2, class_name="car", confidence=0.88,
        bbox=(240, 180, 400, 300), center=(320, 240)
    )

    img_path = mgr.capture_frame(dummy_frame, detections=[det1])
    assert os.path.exists(img_path)

    # Check label file
    lbl_path = img_path.replace("images", "labels").replace(".jpg", ".txt")
    assert os.path.exists(lbl_path)

    with open(lbl_path, "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        parts = lines[0].strip().split()
        assert parts[0] == "2"  # class_id
        # x_center_norm: 320 / 640 = 0.50
        assert float(parts[1]) == pytest.approx(0.50, abs=0.01)
        # y_center_norm: 240 / 480 = 0.50
        assert float(parts[2]) == pytest.approx(0.50, abs=0.01)
        # width_norm: 160 / 640 = 0.25
        assert float(parts[3]) == pytest.approx(0.25, abs=0.01)
        # height_norm: 120 / 480 = 0.25
        assert float(parts[4]) == pytest.approx(0.25, abs=0.01)
