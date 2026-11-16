"""
Dataset Manager - Automated frame capture, YOLO labeling, and training pipeline.

Allows capturing live video frames + YOLO detections directly into rc_car_dataset/
with bounding boxes converted to normalized YOLO format:
<class_id> <x_center> <y_center> <width> <height>
"""

import os
import glob
import cv2
import yaml
import shutil
import random
from typing import List, Any, Optional

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None


class DatasetManager:
    """Manages training dataset collection, YOLO format exports, and fine-tuning."""

    def __init__(self, dataset_dir: str = 'rc_car_dataset'):
        self.dataset_dir = dataset_dir
        self.images_dir = os.path.join(dataset_dir, 'images')
        self.labels_dir = os.path.join(dataset_dir, 'labels')

        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)

    def capture_frame(self, frame, detections=None, custom_labels=None) -> str:
        """
        Capture current frame and write corresponding YOLO format label file.
        Seamlessly handles Detection dataclasses, dictionaries, or raw labels.
        """
        existing = glob.glob(os.path.join(self.images_dir, '*.jpg'))
        idx = len(existing)

        img_name = f"frame_{idx:05d}.jpg"
        img_path = os.path.join(self.images_dir, img_name)

        # Save image
        cv2.imwrite(img_path, frame)

        # Create YOLO format label file
        label_name = f"frame_{idx:05d}.txt"
        label_path = os.path.join(self.labels_dir, label_name)

        h, w = frame.shape[:2]

        with open(label_path, 'w') as f:
            if custom_labels:
                for lbl in custom_labels:
                    f.write(f"{lbl}\n")
            elif detections:
                for det in detections:
                    # Support Detection dataclass or dict
                    if hasattr(det, 'class_id') and hasattr(det, 'bbox'):
                        class_id = det.class_id
                        x1, y1, x2, y2 = det.bbox
                    elif isinstance(det, dict):
                        class_id = det.get('class_id', 0)
                        bbox = det.get('bbox', [0, 0, w, h])
                        x1, y1, x2, y2 = bbox
                    else:
                        continue

                    # Convert pixel coords to normalized YOLO format
                    bw = max(1, x2 - x1)
                    bh = max(1, y2 - y1)
                    xc = x1 + (bw / 2.0)
                    yc = y1 + (bh / 2.0)

                    norm_xc = max(0.0, min(1.0, xc / float(w)))
                    norm_yc = max(0.0, min(1.0, yc / float(h)))
                    norm_w = max(0.0, min(1.0, bw / float(w)))
                    norm_h = max(0.0, min(1.0, bh / float(h)))

                    f.write(f"{class_id} {norm_xc:.6f} {norm_yc:.6f} {norm_w:.6f} {norm_h:.6f}\n")

        return img_path

    def get_stats(self) -> dict:
        images = glob.glob(os.path.join(self.images_dir, '*.jpg'))
        labels = glob.glob(os.path.join(self.labels_dir, '*.txt'))

        classes = set()
        for lbl_path in labels:
            try:
                with open(lbl_path, 'r') as f:
                    for line in f:
                        parts = line.strip().split()
                        if parts:
                            classes.add(parts[0])
            except Exception:
                pass

        return {
            'total_images': len(images),
            'total_labels': len(labels),
            'classes': sorted(list(classes))
        }

    def generate_yaml(self, class_names=None) -> str:
        if class_names is None:
            stats = self.get_stats()
            class_names = [f"class_{i}" for i in stats['classes']] if stats['classes'] else ["object"]

        yaml_data = {
            'path': os.path.abspath(self.dataset_dir),
            'train': 'train/images',
            'val': 'val/images',
            'nc': len(class_names),
            'names': class_names
        }

        yaml_path = os.path.join(self.dataset_dir, 'dataset.yaml')
        with open(yaml_path, 'w') as f:
            yaml.dump(yaml_data, f, sort_keys=False)

        return yaml_path

    def split_dataset(self, val_ratio=0.2):
        images = glob.glob(os.path.join(self.images_dir, '*.jpg'))
        random.shuffle(images)

        val_count = int(len(images) * val_ratio)
        val_images = images[:val_count]
        train_images = images[val_count:]

        for split, split_imgs in [('train', train_images), ('val', val_images)]:
            os.makedirs(os.path.join(self.dataset_dir, split, 'images'), exist_ok=True)
            os.makedirs(os.path.join(self.dataset_dir, split, 'labels'), exist_ok=True)

            for img_path in split_imgs:
                img_name = os.path.basename(img_path)
                label_name = img_name.replace('.jpg', '.txt')
                label_path = os.path.join(self.labels_dir, label_name)

                shutil.copy(img_path, os.path.join(self.dataset_dir, split, 'images', img_name))
                if os.path.exists(label_path):
                    shutil.copy(label_path, os.path.join(self.dataset_dir, split, 'labels', label_name))

    def train_model(self, base_model='yolov8n.pt', epochs=50, imgsz=640, device='mps') -> Optional[str]:
        if YOLO is None:
            return None
        yaml_path = os.path.join(self.dataset_dir, 'dataset.yaml')
        model = YOLO(base_model)
        model.train(
            data=yaml_path,
            epochs=epochs,
            imgsz=imgsz,
            device=device,
            project=self.dataset_dir,
            name='train_results'
        )
        best_pt_path = os.path.join(self.dataset_dir, 'train_results', 'weights', 'best.pt')
        return best_pt_path if os.path.exists(best_pt_path) else None
