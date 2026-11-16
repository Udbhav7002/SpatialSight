"""Unit tests for the 10 Target Categories and perception mappings."""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from core.categories import (
    TARGET_CATEGORIES,
    COCO_TO_TARGET_MAP,
    map_to_target_category,
    get_target_real_height,
)


def test_target_categories_count():
    assert len(TARGET_CATEGORIES) == 10
    expected = ["person", "Box", "Rock", "Table", "Object", "Animal", "Car", "Truck", "Bike", "Sign"]
    assert TARGET_CATEGORIES == expected


def test_category_mapping_person():
    assert map_to_target_category("person") == "person"
    assert map_to_target_category("Pedestrian") == "person"


def test_category_mapping_box():
    assert map_to_target_category("backpack") == "Box"
    assert map_to_target_category("handbag") == "Box"
    assert map_to_target_category("suitcase") == "Box"
    assert map_to_target_category("box") == "Box"


def test_category_mapping_rock():
    assert map_to_target_category("rock") == "Rock"
    assert map_to_target_category("stone") == "Rock"
    assert map_to_target_category("boulder") == "Rock"


def test_category_mapping_table():
    assert map_to_target_category("dining table") == "Table"
    assert map_to_target_category("desk") == "Table"


def test_category_mapping_object():
    assert map_to_target_category("chair") == "Object"
    assert map_to_target_category("couch") == "Object"
    assert map_to_target_category("bed") == "Object"
    assert map_to_target_category("unknown_obstacle_xyz") == "Object"


def test_category_mapping_animal():
    for animal in ["dog", "cat", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "bird"]:
        assert map_to_target_category(animal) == "Animal"


def test_category_mapping_vehicles():
    assert map_to_target_category("car") == "Car"
    assert map_to_target_category("truck") == "Truck"
    assert map_to_target_category("bus") == "Truck"
    assert map_to_target_category("train") == "Truck"
    assert map_to_target_category("bicycle") == "Bike"
    assert map_to_target_category("motorcycle") == "Bike"


def test_category_mapping_signs():
    assert map_to_target_category("traffic light") == "Sign"
    assert map_to_target_category("stop sign") == "Sign"
    assert map_to_target_category("fire hydrant") == "Sign"
    assert map_to_target_category("parking meter") == "Sign"


def test_category_real_heights():
    for cat in TARGET_CATEGORIES:
        height = get_target_real_height(cat)
        assert height > 0.1
        assert height < 5.0


def test_category_edge_cases_no_false_matches():
    # Verify food items and compound words don't misclassify as vehicles or animals
    assert map_to_target_category("carrot") == "Object"
    assert map_to_target_category("hot dog") == "Object"
    assert map_to_target_category("carpet") == "Object"
    assert map_to_target_category("scarf") == "Object"
    assert map_to_target_category("carbon") == "Object"


def test_all_80_coco_classes_mapped_properly():
    coco_classes = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
        "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat",
        "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack",
        "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball",
        "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket",
        "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
        "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake",
        "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop",
        "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
        "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"
    ]
    assert len(coco_classes) == 80
    for c in coco_classes:
        target = map_to_target_category(c)
        assert target in TARGET_CATEGORIES, f"Class {c} mapped to invalid category: {target}"
