"""
Categories - Standardized 10-Target Perception Classes & Mappings for SpatialSight.

Target Classes as specified in design specification (Page 2):
1. person (COCO person)
2. Box (backpack, handbag, suitcase, box)
3. Rock (rock, stone, boulder, obstacle)
4. Table (dining table, desk)
5. Object (chair, couch, bed, bench, general furniture/indoor obstacle)
6. Animal (dog, cat, horse, sheep, cow, elephant, bear, zebra, giraffe, bird)
7. Car (car)
8. Truck (truck, bus, train)
9. Bike (bicycle, motorcycle)
10. Sign (traffic light, stop sign, fire hydrant, parking meter)
"""

from typing import Dict, List, Optional

# The canonical ordered list of target categories
TARGET_CATEGORIES: List[str] = [
    "person",
    "Box",
    "Rock",
    "Table",
    "Object",
    "Animal",
    "Car",
    "Truck",
    "Bike",
    "Sign",
]

# Physical height in meters for pinhole optical distance estimation
CATEGORY_REAL_HEIGHTS: Dict[str, float] = {
    "person": 1.70,
    "Box": 0.50,
    "Rock": 0.40,
    "Table": 0.75,
    "Object": 0.70,
    "Animal": 0.80,
    "Car": 1.50,
    "Truck": 2.80,
    "Bike": 1.25,
    "Sign": 1.00,
}

# Complete standard 80 COCO classes mapped into the 10 canonical categories
COCO_TO_TARGET_MAP: Dict[str, str] = {
    # 1. person
    "person": "person",
    "pedestrian": "person",
    "human": "person",

    # 2. Box (backpack, handbag, suitcase, box)
    "backpack": "Box",
    "handbag": "Box",
    "suitcase": "Box",
    "box": "Box",
    "cardboard box": "Box",
    "package": "Box",
    "crate": "Box",
    "carton": "Box",

    # 3. Rock / Obstacle
    "rock": "Rock",
    "stone": "Rock",
    "boulder": "Rock",
    "debris": "Rock",

    # 4. Table
    "dining table": "Table",
    "table": "Table",
    "desk": "Table",
    "coffee table": "Table",

    # 5. Object (furniture, appliances, indoor/outdoor items, general obstacles)
    "chair": "Object",
    "couch": "Object",
    "sofa": "Object",
    "bed": "Object",
    "bench": "Object",
    "potted plant": "Object",
    "bottle": "Object",
    "wine glass": "Object",
    "cup": "Object",
    "fork": "Object",
    "knife": "Object",
    "spoon": "Object",
    "bowl": "Object",
    "banana": "Object",
    "apple": "Object",
    "sandwich": "Object",
    "orange": "Object",
    "broccoli": "Object",
    "carrot": "Object",
    "hot dog": "Object",
    "pizza": "Object",
    "donut": "Object",
    "cake": "Object",
    "tv": "Object",
    "laptop": "Object",
    "mouse": "Object",
    "remote": "Object",
    "keyboard": "Object",
    "cell phone": "Object",
    "microwave": "Object",
    "oven": "Object",
    "toaster": "Object",
    "sink": "Object",
    "refrigerator": "Object",
    "book": "Object",
    "clock": "Object",
    "vase": "Object",
    "scissors": "Object",
    "teddy bear": "Object",
    "hair drier": "Object",
    "toothbrush": "Object",
    "toilet": "Object",
    "umbrella": "Object",
    "tie": "Object",
    "frisbee": "Object",
    "skis": "Object",
    "snowboard": "Object",
    "sports ball": "Object",
    "kite": "Object",
    "baseball bat": "Object",
    "baseball glove": "Object",
    "skateboard": "Object",
    "surfboard": "Object",
    "tennis racket": "Object",
    "airplane": "Object",
    "boat": "Object",
    "obstacle": "Object",

    # 6. Animal
    "bird": "Animal",
    "cat": "Animal",
    "dog": "Animal",
    "horse": "Animal",
    "sheep": "Animal",
    "cow": "Animal",
    "elephant": "Animal",
    "bear": "Animal",
    "zebra": "Animal",
    "giraffe": "Animal",

    # 7. Car
    "car": "Car",
    "automobile": "Car",
    "sedan": "Car",
    "suv": "Car",

    # 8. Truck
    "truck": "Truck",
    "bus": "Truck",
    "train": "Truck",
    "lorry": "Truck",
    "trailer": "Truck",

    # 9. Bike
    "bicycle": "Bike",
    "motorcycle": "Bike",
    "scooter": "Bike",
    "motorbike": "Bike",

    # 10. Sign
    "traffic light": "Sign",
    "stop sign": "Sign",
    "fire hydrant": "Sign",
    "parking meter": "Sign",
    "street sign": "Sign",
}

import re

# Fallback regex patterns with word boundaries to avoid false positives (e.g. 'carrot' -> 'car')
_PATTERNS = [
    (re.compile(r"\b(person|pedestrian|human|man|woman|child|boy|girl)\b", re.IGNORECASE), "person"),
    (re.compile(r"\b(backpack|handbag|suitcase|box|boxes|package|carton|crate)\b", re.IGNORECASE), "Box"),
    (re.compile(r"\b(rock|stone|boulder|debris|gravel)\b", re.IGNORECASE), "Rock"),
    (re.compile(r"\b(table|desk|countertop)\b", re.IGNORECASE), "Table"),
    (re.compile(r"\b(car|cars|automobile|sedan|suv|minivan|van)\b", re.IGNORECASE), "Car"),
    (re.compile(r"\b(truck|bus|train|lorry|trailer)\b", re.IGNORECASE), "Truck"),
    (re.compile(r"\b(bike|bicycle|motorcycle|scooter|motorbike|cycle)\b", re.IGNORECASE), "Bike"),
    (re.compile(r"\b(traffic light|stop sign|fire hydrant|parking meter|sign|billboard)\b", re.IGNORECASE), "Sign"),
    (re.compile(r"\b(dog|cat|horse|sheep|cow|elephant|bear|zebra|giraffe|bird|animals?|pet|pets)\b", re.IGNORECASE), "Animal"),
]


def map_to_target_category(class_name: str) -> str:
    """
    Map any raw YOLO class name into one of the 10 target categories.
    Defaults to 'Object' if unclassified.
    """
    cleaned = class_name.strip().lower()
    if cleaned in COCO_TO_TARGET_MAP:
        return COCO_TO_TARGET_MAP[cleaned]

    # Check regex word boundaries
    for pattern, target in _PATTERNS:
        if pattern.search(cleaned):
            return target

    # Fallback to general Object
    return "Object"


def get_target_real_height(category: str) -> float:
    """Return the real-world height in meters for distance math."""
    return CATEGORY_REAL_HEIGHTS.get(category, 0.70)
