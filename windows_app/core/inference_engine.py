"""
Inference Engine - YOLO model loader and real-time inference runner.

Supports:
- Apple Silicon MPS (Metal Performance Shaders) acceleration
- CUDA (for Windows/Linux with Nvidia GPUs)
- CPU fallback
- Hot-swapping between different model weights
"""

import time
import logging
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
import torch

logger = logging.getLogger(__name__)


@dataclass
class Detection:
    """A single detected object."""
    class_id: int
    class_name: str
    confidence: float
    bbox: tuple[int, int, int, int]  # (x1, y1, x2, y2) in pixels
    center: tuple[int, int]  # (cx, cy) center point


@dataclass
class InferenceResult:
    """Result of running inference on a single frame."""
    detections: list[Detection] = field(default_factory=list)
    inference_time_ms: float = 0.0
    frame_shape: tuple[int, int, int] = (0, 0, 0)  # (H, W, C)

    @property
    def count_by_class(self) -> dict[str, int]:
        """Count detections grouped by class name."""
        counts: dict[str, int] = {}
        for d in self.detections:
            counts[d.class_name] = counts.get(d.class_name, 0) + 1
        return counts

    @property
    def total_count(self) -> int:
        return len(self.detections)


def get_best_device() -> str:
    """Auto-detect the best available compute device."""
    if torch.backends.mps.is_available():
        logger.info("Using Apple Silicon MPS (Metal) acceleration")
        return "mps"
    elif torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        logger.info(f"Using CUDA GPU: {gpu_name}")
        return "cuda"
    else:
        logger.info("Using CPU (no GPU acceleration available)")
        return "cpu"


class InferenceEngine:
    """
    YOLO-based object detection inference engine.

    Manages model loading, device selection, inference execution,
    and model hot-swapping.

    Usage:
        engine = InferenceEngine()
        engine.load_model("yolov8n.pt")

        result = engine.infer(frame)
        for det in result.detections:
            print(f"{det.class_name}: {det.confidence:.2f} at {det.bbox}")
    """

    # Default confidence and IoU thresholds
    DEFAULT_CONFIDENCE = 0.45
    DEFAULT_IOU = 0.50

    def __init__(self):
        self._model = None
        self._model_path: str | None = None
        self._device: str = get_best_device()
        self._confidence: float = self.DEFAULT_CONFIDENCE
        self._iou_threshold: float = self.DEFAULT_IOU
        self._class_filter: list[int] | None = None  # None = detect all classes
        self._class_names: dict[int, str] = {}

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    @property
    def model_path(self) -> str | None:
        return self._model_path

    @property
    def device(self) -> str:
        return self._device

    @property
    def class_names(self) -> dict[int, str]:
        return self._class_names

    def load_model(self, model_path: str = "yolov8n.pt") -> bool:
        """
        Load a YOLO model from a .pt weights file.

        Args:
            model_path: Path to model weights. Can be:
                - "yolov8n.pt" (auto-downloads if not present)
                - "yolov8s.pt", "yolov8m.pt" (larger, more accurate)
                - "/path/to/custom_best.pt" (your trained model)

        Returns:
            True if model loaded successfully.
        """
        try:
            from ultralytics import YOLO

            logger.info(f"Loading model: {model_path} on device: {self._device}")
            start = time.monotonic()

            self._model = YOLO(model_path)

            # Warm up the model with a dummy inference
            dummy = np.zeros((640, 640, 3), dtype=np.uint8)
            self._model.predict(
                dummy, device=self._device, verbose=False, imgsz=640
            )

            elapsed = (time.monotonic() - start) * 1000
            self._model_path = model_path
            self._class_names = self._model.names
            logger.info(
                f"Model loaded in {elapsed:.0f}ms - "
                f"{len(self._class_names)} classes on {self._device}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to load model '{model_path}': {e}")
            self._model = None
            self._model_path = None
            return False

    def set_confidence(self, confidence: float) -> None:
        """Set the minimum detection confidence threshold (0.0 - 1.0)."""
        self._confidence = max(0.0, min(1.0, confidence))

    def set_iou_threshold(self, iou: float) -> None:
        """Set the IoU threshold for Non-Maximum Suppression."""
        self._iou_threshold = max(0.0, min(1.0, iou))

    def set_class_filter(self, class_ids: list[int] | None) -> None:
        """
        Filter detections to specific classes only.

        Args:
            class_ids: List of COCO class IDs to detect, or None for all.
                       Example: [0] for person-only, [0, 2, 5, 7] for
                       person + car + bus + truck.
        """
        self._class_filter = class_ids

    def infer(self, frame: np.ndarray) -> InferenceResult:
        """
        Run object detection on a single frame.

        Args:
            frame: BGR image as numpy array (from OpenCV).

        Returns:
            InferenceResult with all detections and timing info.
        """
        if self._model is None:
            logger.warning("No model loaded - call load_model() first")
            return InferenceResult(frame_shape=frame.shape)

        start = time.monotonic()

        results = self._model.predict(
            frame,
            device=self._device,
            conf=self._confidence,
            iou=self._iou_threshold,
            classes=self._class_filter,
            verbose=False,
            imgsz=640,
        )

        elapsed_ms = (time.monotonic() - start) * 1000

        detections: list[Detection] = []
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes

            if boxes is not None and len(boxes) > 0:
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                    conf = float(box.conf[0].cpu())
                    cls_id = int(box.cls[0].cpu())
                    cls_name = self._class_names.get(cls_id, f"class_{cls_id}")

                    cx = (x1 + x2) // 2
                    cy = (y1 + y2) // 2

                    detections.append(Detection(
                        class_id=cls_id,
                        class_name=cls_name,
                        confidence=conf,
                        bbox=(x1, y1, x2, y2),
                        center=(cx, cy),
                    ))

        return InferenceResult(
            detections=detections,
            inference_time_ms=elapsed_ms,
            frame_shape=frame.shape,
        )

    def list_available_models(self, models_dir: str = "models") -> list[str]:
        """List all .pt model files in the models directory and local application root."""
        models: set[str] = set()
        
        # Check models directory
        models_path = Path(models_dir)
        if models_path.exists():
            for p in models_path.glob("*.pt"):
                models.add(str(p))
                
        # Check local directory
        local_dir = Path(__file__).resolve().parent.parent
        for p in local_dir.glob("*.pt"):
            models.add(str(p))

        # Always include yolov8n.pt as baseline
        if not models:
            models.add("yolov8n.pt")

        return sorted(list(models))
