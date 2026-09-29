import os
import glob
import cv2
import yaml
import shutil
import random
from ultralytics import YOLO

class DatasetManager:
    def __init__(self, dataset_dir='rc_car_dataset'):
        self.dataset_dir = dataset_dir
        self.images_dir = os.path.join(dataset_dir, 'images')
        self.labels_dir = os.path.join(dataset_dir, 'labels')
        
        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(self.labels_dir, exist_ok=True)

    def capture_frame(self, frame, detections, custom_labels=None) -> str:
        existing = glob.glob(os.path.join(self.images_dir, '*.jpg'))
        idx = len(existing)
        
        img_name = f"frame_{idx:05d}.jpg"
        img_path = os.path.join(self.images_dir, img_name)
        
        # Save image
        cv2.imwrite(img_path, frame)
        
        # Create YOLO format label file
        label_name = f"frame_{idx:05d}.txt"
        label_path = os.path.join(self.labels_dir, label_name)
        
        with open(label_path, 'w') as f:
            if custom_labels:
                for lbl in custom_labels:
                    f.write(f"{lbl}\n")
            elif detections:
                for det in detections:
                    class_id = det.get('class_id', 0)
                    bbox = det.get('bbox_norm', [0.5, 0.5, 0.1, 0.1])
                    f.write(f"{class_id} {bbox[0]} {bbox[1]} {bbox[2]} {bbox[3]}\n")
                    
        return img_path

    def get_stats(self) -> dict:
        images = glob.glob(os.path.join(self.images_dir, '*.jpg'))
        labels = glob.glob(os.path.join(self.labels_dir, '*.txt'))
        
        classes = set()
        for lbl_path in labels:
            with open(lbl_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        classes.add(parts[0])
                        
        return {
            'total_images': len(images),
            'total_labels': len(labels),
            'classes': classes
        }

    def generate_yaml(self, class_names=None) -> str:
        if class_names is None:
            stats = self.get_stats()
            class_names = [f"class_{i}" for i in sorted(list(stats['classes']))]
            
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
                
                # Move files
                shutil.move(img_path, os.path.join(self.dataset_dir, split, 'images', img_name))
                if os.path.exists(label_path):
                    shutil.move(label_path, os.path.join(self.dataset_dir, split, 'labels', label_name))

    def train_model(self, base_model='yolov8n.pt', epochs=50, imgsz=640, device='mps') -> str:
        yaml_path = os.path.join(self.dataset_dir, 'dataset.yaml')
        
        model = YOLO(base_model)
        results = model.train(
            data=yaml_path,
            epochs=epochs,
            imgsz=imgsz,
            device=device,
            project=self.dataset_dir,
            name='train_results'
        )
        
        best_pt_path = os.path.join(self.dataset_dir, 'train_results', 'weights', 'best.pt')
        return best_pt_path
