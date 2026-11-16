# SpatialSight — Windows Edition

Self-contained Windows desktop application for real-time object detection and spatial room mapping.

---

## Quick Start on Windows

### 1. One-Click Setup
Double-click `setup_windows.bat`. It will:
- Check for Python (3.10–3.12 recommended).
- Create a local `venv`.
- Install PyTorch, Ultralytics YOLO, OpenCV, and PyQt6.

### 2. Launch the Application
Double-click `run_windows.bat` or run from Command Prompt / PowerShell:
```cmd
venv\Scripts\activate
python main_gui.py --source 0
```

### 3. Connect Android Phone via USB-C
1. Enable **USB Debugging** on the Android phone.
2. Connect phone via USB-C.
3. Open Command Prompt and forward ports:
   ```cmd
   adb forward tcp:8080 tcp:8080
   ```
4. Start SpatialSight connected to the phone:
   ```cmd
   python main_gui.py --source usb
   ```

---

## Directory Layout
* `main_gui.py` — PyQt6 Dashboard launcher.
* `main.py` — Lightweight OpenCV console runner.
* `core/` — ADB bridge, frame buffer, YOLO inference engine, collision zone.
* `spatial/` — Sensor keyframe selector, angular deduplicator, 2D radar room renderer.
* `ui/` — PyQt6 dashboard tabs (Live Detection + Room Map).
* `models/` — Directory for YOLO weights (`.pt`).
