# SpatialSight

**Sensor-Guided Object Detection System**

A dual-mode object detection application that connects an Android phone (camera + sensors) to a Mac/PC (compute engine) over USB-C.

## Modes

### Mode 1: Spatial Room Map
Scan a room by panning your phone around. The app uses phone orientation sensors to capture smart keyframes — only snapping frames when the camera points at a genuinely new area. Objects are deduplicated spatially, giving you an exact inventory count and a 2D room map.

### Mode 2: Live Detection
Real-time 60 FPS object detection with bounding boxes, labels, live object counts, and forward collision warnings. Supports custom model loading for specialized use cases like RC cars.

## Requirements

- **Mac:** Apple Silicon (M1 or later) — M5 recommended
- **Phone:** Android 8.0+ with USB Debugging enabled
- **Cable:** USB-C data cable
- **Python:** 3.12 (managed via virtual environment)

## Quick Start

### On macOS (Apple Silicon M-Series)
```bash
cd mac_app
./run_mac.sh --source 0
```

### On Windows
```cmd
cd windows_app
run_windows.bat
```

### On Android
Open `android_app/` in Android Studio, build and install the APK.

## Project Structure

```
├── android_app/          # Native Android companion app (Kotlin + CameraX + NanoHTTPD)
├── mac_app/              # Standalone macOS app (PyQt6 + Apple Silicon MPS Metal)
├── windows_app/          # Standalone Windows app (PyQt6 + CUDA/DirectML/CPU + batch launchers)
├── rc_car_dataset/       # Auto-generated training data & captures
└── docs/                 # Project documentation & blueprint
```

## Documentation

See [docs/PROJECT_BLUEPRINT.md](docs/PROJECT_BLUEPRINT.md) for the full architecture and implementation plan.
