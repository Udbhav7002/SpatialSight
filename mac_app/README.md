# SpatialSight — macOS Edition (Apple Silicon M-Series)

Self-contained macOS desktop application leveraging Apple Silicon Metal Performance Shaders (MPS) and unified memory for 60+ FPS real-time object detection and spatial room mapping.

---

## Quick Start on macOS

### 1. One-Time Setup
Run the setup script:
```bash
./setup_mac.sh
```
This automatically sets up Python 3.12 with PyTorch (Apple MPS accelerated), Ultralytics YOLO, OpenCV, and PyQt6.

### 2. Launch the Application
Run the launcher script:
```bash
./run_mac.sh
```
Or specify options:
```bash
./run_mac.sh --source 0 --model yolov8n.pt
```

### 3. Connect Android Phone via USB-C
1. Enable **USB Debugging** on the Android phone.
2. Connect phone to your Mac via USB-C.
3. Forward port over ADB:
   ```bash
   adb forward tcp:8080 tcp:8080
   ```
4. Start SpatialSight connected to the phone:
   ```bash
   ./run_mac.sh --source usb
   ```

---

## Directory Layout
* `run_mac.sh` — One-click launcher script.
* `setup_mac.sh` — Automated virtualenv & dependency installer.
* `main_gui.py` — PyQt6 Dashboard launcher.
* `main.py` — Lightweight OpenCV console runner.
* `core/` — ADB bridge, frame buffer, YOLO inference engine, collision zone.
* `spatial/` — Sensor keyframe selector, angular deduplicator, 2D radar room renderer.
* `ui/` — PyQt6 dashboard tabs (Live Detection + Room Map).
* `models/` — Directory for YOLO weights (`.pt`).
