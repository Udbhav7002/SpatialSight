# SpatialSight

<div align="center">

**Sensor-Guided Object Detection & Adaptive Collision Avoidance System**

[![Platform](https://img.shields.io/badge/Platforms-macOS%20%7C%20Windows%20%7C%20Android-blue.svg)](#ready-to-run-releases)
[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-green.svg)](https://www.python.org/)
[![AI Engine](https://img.shields.io/badge/YOLO-v8%20(Ultralytics)-orange.svg)](https://docs.ultralytics.com/)
[![Tests](https://img.shields.io/badge/Tests-40%20Passed-brightgreen.svg)](#test-suite)
[![Release](https://img.shields.io/badge/Release-v1.1.0-blueviolet.svg)](https://github.com/Udbhav7002/SpatialSight/releases)

*A distributed, dual-mode computer vision and ADAS system pairing an Android camera/sensor unit with a high-performance desktop compute dashboard over USB-C or Wi-Fi.*

</div>

---

## Overview

**SpatialSight** is an end-to-end intelligent vision system that bridges mobile sensor hardware, desktop neural network inference, and physical microcontrollers. It operates in two specialized modes:

1. **Live Detection & ADAS Corridor (Automotive Driving Assistance):** Real-time YOLOv8 object detection with vector bounding boxes, dynamic object tracking, stopping-distance physics calculations, friction-adjusted collision corridors, dual-stage audio warnings, and real-time physical Arduino traffic-light signaling (0ms hazard response).
2. **Spatial Room Mapping:** Real-time 2D polar radar room scanning. Utilizes mobile gyroscope/accelerometer sensor fusion to capture keyframes only when panning into novel visual space, deduplicating detected objects by spatial angle to produce an exact physical inventory count.

---

## Ready-to-Run Releases

Download pre-packaged releases directly from [GitHub Releases](https://github.com/Udbhav7002/SpatialSight/releases/latest):

| Target Platform | Package | How to Run |
|---|---|---|
| **macOS** (Apple Silicon M1–M5) | [`SpatialSight-macOS.zip`](https://github.com/Udbhav7002/SpatialSight/releases/latest) | Extract and double-click `SpatialSight.app` (or run `./run_mac.sh`) |
| **Windows** (10 / 11) | [`SpatialSight-Windows.zip`](https://github.com/Udbhav7002/SpatialSight/releases/latest) | Extract and double-click `SpatialSight.bat` (auto-installs dependencies on first run) |
| **Android** (8.0+ Oreo or higher) | [`SpatialSight.apk`](https://github.com/Udbhav7002/SpatialSight/releases/latest) | Transfer to phone and tap to install (enable *Install unknown apps*) |

> [!TIP]
> **No Phone Needed for Quick Testing:** The desktop application defaults to `--source 0` (your laptop's built-in webcam), allowing instant testing of object detection, the collision corridor, and UI controls without connecting external hardware.

---

## System Architecture

```
┌─────────────────────────────────┐
│       Android Phone Client      │
│  - CameraX Video Stream (MJPEG) │
│  - Sensor Fusion (Yaw/Pitch/Roll│
└────────────────┬────────────────┘
                 │ USB (ADB) or Wi-Fi (HTTP:8080)
                 ▼
┌─────────────────────────────────┐
│     Desktop Compute Engine      │
│  (macOS MPS Metal / Windows GPU)│
│  - YOLOv8 Neural Inference      │
│  - Adaptive Collision Physics   │
│  - Spatial Angular Dedup        │
│  - PyQt6 Unified Dashboard      │
└────────┬───────────────┬────────┘
         │               │
         ▼ Serial USB    ▼ Audio Engine
┌─────────────────┐  ┌──────────────────┐
│  Arduino Uno    │  │ Dual-Stage Sound │
│  Traffic Lights │  │ Caution (<10m)   │
│  & Rain Sensor  │  │ Emergency (<5m)  │
└─────────────────┘  └──────────────────┘
```

---

## Key Features

### 1. Tesla-Style Detection & Collision Warning Corridor
- **Color Scheme & Typography:** Custom automotive dark palette (`#15370D` deep pine, `#1E4714` surface panels, `#E5CD82` brass vector bounding boxes, and `#FFF2B4` high-contrast headers).
- **Physics-Based Stopping Distance:**
  $$\text{Stopping Distance} = (v \cdot t_{\text{reaction}}) + \frac{v^2}{2 \cdot \mu \cdot g}$$
  Adjusts dynamically based on weather/road friction conditions (Dry $\mu=0.7$, Wet $\mu=0.4$, Icy $\mu=0.2$).
- **Dual-Stage Alert System:**
  - *Caution Alert:* Target inside corridor under 10m (pulsing amber indicator, yellow LED, caution chime).
  - *Imminent Hazard:* Target inside corridor under 5m (crimson bounding corridor, red LED at 0ms latency, high-frequency alarm tone).

### 2. Spatial Room Mapping & Polar Radar
- **Keyframe Triggering:** Captures frames only when phone orientation changes beyond an adaptive angular threshold ($\Delta\theta \ge 15^\circ$), eliminating redundant blur frames.
- **Angular Deduplication:** Identifies and groups detections by physical world azimuth to prevent double-counting as the user scans a space.
- **Polar Radar UI:** Renders a 360-degree top-down radar view with color-coded distance concentric rings.

### 3. Physical Hardware Integration (Arduino Uno)
- **Universal Multi-Pin Traffic Controller:** Supports digital pins for Red, Yellow, and Green LED signals with automatic hardware heartbeat monitoring.
- **Waiting Cycle:** Gracefully steps Red &rarr; Yellow &rarr; Green sequentially when waiting for phone/camera stream connection.
- **Weather Telemetry:** Reads analog rain/water sensor on pin `A0` at 10Hz and dynamically lowers road friction parameters in the compute engine.

---

## Project Structure

```
SpatialSight/
├── android_app/               # Native Android app (Kotlin, CameraX, NanoHTTPD)
├── mac_app/                   # macOS Apple Silicon dashboard (PyQt6, Metal MPS)
│   ├── core/                  # Inference, ADB bridge, collision physics, Arduino
│   ├── spatial/               # Angular deduplication, polar radar rendering
│   ├── ui/                    # Dark theme, sound controller, detection views
│   ├── setup_mac.sh           # One-time automated environment setup
│   └── run_mac.sh             # Launch script
├── windows_app/               # Windows dashboard (CUDA, DirectML, or CPU)
│   ├── setup_windows.bat      # One-time automated environment setup
│   └── run_windows.bat        # Launch script
├── runnable/                  # Double-clickable ready-to-run desktop & mobile bundles
│   ├── Android/               # SpatialSight.apk distribution
│   ├── macOS/                 # Standalone SpatialSight.app bundle
│   └── Windows/               # SpatialSight.bat launcher
├── arduino/                   # Arduino Uno traffic light & weather firmware (.ino)
├── assets/                    # Shared media, audio warning chimes, icons
├── docs/                      # Technical documentation
│   ├── hardware/              # Arduino wiring photos and sensor pinout references
│   ├── specs/                 # System design sheets and engineering specifications
│   ├── reports/               # Research abstracts and academic presentation slide decks
│   └── PROJECT_BLUEPRINT.md   # Complete system architecture and implementation blueprint
├── tests/                     # Automated test suite (spatial math, collision corridor)
├── tools/                     # Automation scripts (presentation builders, Arduino uploader)
└── requirements.txt           # Unified Python dependency specification
```

---

## Hardware Pinout (Arduino Uno)

| Component | Pin | Purpose |
|---|---|---|
| **Red LED** | Digital `13` (or `10`, `7`, `4`) | Imminent Collision Hazard / Stop |
| **Yellow LED** | Digital `12` (or `9`, `6`, `3`) | Caution Hazard Warning |
| **Green LED** | Digital `11` (or `8`, `5`, `2`) | Path Clear |
| **Water / Rain Sensor** | Analog `A0` | Dynamic road friction coefficient adjustment |
| **Ground** | `GND` | Common ground rail |

*Wiring photos and hardware references can be found in [`docs/hardware/`](docs/hardware).*

---

## Developer Quick Start

### Prerequisites
- **Python:** 3.10, 3.11, or 3.12
- **Webcam:** Built-in laptop camera (or connected Android phone)
- **Git**

### macOS (Apple Silicon M1/M2/M3/M4)
```bash
git clone https://github.com/Udbhav7002/SpatialSight.git
cd SpatialSight/mac_app

# 1. One-time setup (creates virtual environment and installs PyTorch with MPS support)
./setup_mac.sh

# 2. Launch dashboard with laptop webcam
./run_mac.sh --source 0

# (Optional) Launch with connected Android phone
./run_mac.sh --source usb
```

### Windows (10/11)
```cmd
git clone https://github.com/Udbhav7002/SpatialSight.git
cd SpatialSight\windows_app

:: 1. One-time setup
setup_windows.bat

:: 2. Launch dashboard
run_windows.bat
```

### Android Companion Setup
1. Sideload `runnable/Android/SpatialSight.apk` onto an Android phone.
2. **USB Mode (Lowest Latency):** Enable **USB Debugging** under *Settings > Developer options*. Connect the phone via USB-C cable and run:
   ```bash
   adb forward tcp:8080 tcp:8080
   ```
3. **Wi-Fi Mode:** Connect phone and laptop to the same local network. Start the stream in the mobile app and specify the stream URL in the dashboard (e.g. `http://192.168.1.100:8080/video`).

---

## Test Suite

The test suite validates spatial deduplication math, keyframe selection logic, collision corridor projection, and frame buffering:

```bash
# Run all unit tests
pytest tests/ -v
```

All 40 unit tests run synchronously and pass without external hardware requirements.

---

## Technical Documentation & Research

- [PROJECT_BLUEPRINT.md](docs/PROJECT_BLUEPRINT.md): Full architectural specifications, mathematical formulations, and engineering design.
- [System Design Specs](docs/specs/system_design_specs.pdf): Original system engineering design and state-machine flow.
- [Hardware Documentation](docs/hardware/): Sensor wiring photographs and board layout.
- [Academic Reports & Slides](docs/reports/): Presentation slide decks and research abstracts.

---

## License

This project is licensed under the [MIT License](LICENSE).
