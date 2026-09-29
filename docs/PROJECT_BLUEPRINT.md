# SpatialSight — Sensor-Guided Object Detection System

> A dual-mode object detection application that connects an Android phone (camera + sensors) to a Mac/PC (compute engine) over USB-C for real-time spatial awareness.

---

## 1. Problem Statement

### The Core Problem

There is no lightweight, offline, general-purpose tool that lets a person use their phone as a smart camera sensor connected to a powerful computer to:

1. **Map a room** by walking around it and get an accurate, deduplicated inventory of every object present — without counting the same chair 150 times from different angles.
2. **Detect objects in real-time** while driving, walking, or operating an RC car — with live bounding boxes, labels, and hazard warnings on the PC screen.

### Why Existing Solutions Fail

| Existing Tool | Why It Doesn't Work |
| :--- | :--- |
| **Google Lens / Apple Visual Look Up** | Single-image only. No room mapping. No live video stream. No object counting. |
| **Security Camera NVRs (e.g., Frigate)** | Designed for fixed, stationary cameras. Cannot handle a moving handheld phone. No spatial deduplication. |
| **AR Apps (e.g., IKEA Place, Polycam)** | Built for 3D mesh reconstruction or furniture placement — not object detection and counting. |
| **Cloud-based Vision APIs (Google Vision, AWS Rekognition)** | Require internet. Per-request pricing. Latency too high for real-time. Privacy concerns (your room footage goes to a server). |

### What We Are Building

A **fully offline, USB-C connected, dual-mode application** that runs 100% of AI processing on the local machine (MacBook Pro M5 / Windows PC), using the Android phone purely as a smart camera with orientation sensors.

---

## 2. System Overview

### The Two Modes

```
                                    ┌────────────────────────┐
                                    │    SELECT APP MODE     │
                                    └───────────┬────────────┘
                                                │
                       ┌────────────────────────┴────────────────────────┐
                       ▼                                                 ▼
        ┌──────────────────────────────┐                  ┌──────────────────────────────┐
        │  MODE 1: SPATIAL ROOM MAP    │                  │  MODE 2: LIVE DETECTION      │
        │     (Exact Inventory)        │                  │     (Real-Time Stream)       │
        ├──────────────────────────────┤                  ├──────────────────────────────┤
        │ • Sensor-triggered keyframes │                  │ • Continuous 30/60 FPS stream│
        │ • Camera frustum tracking    │                  │ • Real-time bounding boxes   │
        │ • Deduplicated object count  │                  │ • Forward Hazard Warning zone│
        │ • 2D Room Layout Map output  │                  │ • RC Car custom model toggle │
        │ • Natural language Q&A       │                  │ • Dataset capture hotkey     │
        └──────────────────────────────┘                  └──────────────────────────────┘
```

---

## 3. Architecture

### High-Level Data Flow

```
┌─────────────────────────────────┐
│        ANDROID PHONE            │
│   (Camera + IMU Sensors)        │
│                                 │
│  1. CameraX: 720p @ 30 FPS     │
│  2. Rotation Vector Sensor:     │
│     Yaw (θ), Pitch (φ), Roll   │
│  3. NanoHTTPD / Ktor Server:    │
│     Streams MJPEG + sensor JSON │
│     on localhost:8080           │
└────────────────┬────────────────┘
                 │
                 │  USB-C Cable (High-Speed Data)
                 │  Bridge: `adb forward tcp:8080 tcp:8080`
                 │  Effective Latency: ~20-35 ms
                 │  Bandwidth: 480 Mbps (USB 2.0) / 10+ Gbps (USB 3.x)
                 │
                 ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   MACBOOK PRO M5 (ALL COMPUTE HERE)                    │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐    │
│   │  Layer 1: USB Frame Ingestion Worker                         │    │
│   │  - Multi-threaded producer-consumer buffer                   │    │
│   │  - Discards stale frames (always processes the LATEST frame) │    │
│   │  - Parses interleaved sensor telemetry (yaw, pitch, roll)    │    │
│   └──────────────────────────────┬───────────────────────────────┘    │
│                                  │                                     │
│                    ┌─────────────┴─────────────┐                      │
│                    ▼                           ▼                       │
│   ┌──────────────────────────┐  ┌──────────────────────────┐         │
│   │  MODE 1 PIPELINE         │  │  MODE 2 PIPELINE         │         │
│   │  (Spatial Room Map)      │  │  (Live Detection)        │         │
│   │                          │  │                          │         │
│   │  1. Keyframe Selector    │  │  1. YOLO Inference       │         │
│   │     (sensor-triggered)   │  │     (every frame, <8ms)  │         │
│   │  2. YOLO on keyframes    │  │  2. Collision Zone Check │         │
│   │  3. Spatial Dedup Engine │  │  3. Bounding Box Overlay │         │
│   │  4. Room Map Generator   │  │  4. HUD Counter Display  │         │
│   │  5. VLM Q&A (optional)  │  │  5. Dataset Recorder     │         │
│   └──────────────────────────┘  └──────────────────────────┘         │
│                                                                        │
│   ┌──────────────────────────────────────────────────────────────┐    │
│   │  Layer 4: Desktop Dashboard (PyQt6 GUI Window)               │    │
│   │  - Mode toggle tabs (Room Map / Live Detection)              │    │
│   │  - Model switcher dropdown (YOLOv8n / Custom RC Car model)   │    │
│   │  - Confidence threshold slider                               │    │
│   │  - FPS counter & connection status                           │    │
│   └──────────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Mode 1: Spatial Room Map — Deep Dive

### The Core Innovation: Sensor-Guided Keyframe Capture

Instead of processing 900 frames from a 30-second video and counting the same chair 150 times, we use the phone's **rotation vector sensor** to snap keyframes only when the camera points at a genuinely new area of the room.

### Original Concept Sketch

![Keyframe frustum trajectory sketch](/Users/sanagariudbhav/.gemini/antigravity/brain/a6185110-3950-45bd-a887-cb90ce7c3596/keyframe_frustum_sketch.jpg)

> The sketch above shows the camera trajectory path with camera view frustums (the angled trapezoids representing the field of view) at specific keyframe positions along the path. Each frustum captures a unique slice of the room without overlap.

### Keyframe Trigger Logic

A new keyframe is captured **only** when the phone's orientation changes beyond a threshold:

```
IF  Δ_yaw   ≥ 30°   (horizontal rotation)
OR  Δ_pitch ≥ 20°   (vertical tilt)
OR  Δ_position ≥ 0.75m   (if using ARCore for position tracking)
THEN:
    → Capture current frame as Keyframe N
    → Tag it with sensor data: { yaw: θ, pitch: φ, timestamp: t }
    → Send frame + metadata to Mac over USB
```

### Spatial Deduplication Pipeline

```
Step 1: Keyframe Capture
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ KF1      │  │ KF2      │  │ KF3      │  │ KF4      │
│ Yaw: 0°  │  │ Yaw: 35° │  │ Yaw: 80° │  │ Yaw: 130°│
│ [Bed]    │  │ [Table]  │  │ [Door]   │  │ [Chair]  │
│ [Lamp]   │  │ [Chair]  │  │          │  │ [Shelf]  │
└──────────┘  └──────────┘  └──────────┘  └──────────┘

Step 2: Angular Bin Assignment
Each detected object gets a spatial coordinate based on:
  object_angle = keyframe_yaw + (bbox_center_x / image_width) × camera_FOV

Step 3: Deduplication
The "Chair" in KF2 (angle ~50°) and the "Chair" in KF4 (angle ~145°)
have Δangle = 95° → They are DIFFERENT physical chairs → Count both.

If KF2 had a "Chair" at angle ~48° and KF3 had a "Chair" at angle ~52°,
Δangle = 4° → Same physical chair seen from a slightly different angle → Merge.

Step 4: Output
┌─────────────────────────────────┐
│  ROOM INVENTORY (Deduplicated) │
│  ─────────────────────────────  │
│  • Bed .............. 1         │
│  • Table ............ 1         │
│  • Chair ............ 2         │
│  • Lamp ............. 1         │
│  • Door ............. 1         │
│  • Shelf ............ 1         │
│  ─────────────────────────────  │
│  Total Unique Objects: 7       │
└─────────────────────────────────┘
```

### 2D Room Map Visualization

The Mac app generates a top-down radar-style map showing:
- The user's sweep trajectory (the path they walked/rotated).
- Keyframe frustum cones showing where the camera was pointed.
- Object icons placed at their estimated angular positions.

```
                    North (0°)
                       │
            ┌──────────┼──────────┐
            │   [Bed]  │          │
            │          │  [Lamp]  │
   West ────┤          ●──────────┤──── East
   (270°)   │  [Chair] │  [Table] │   (90°)
            │          │          │
            │  [Shelf] │  [Door]  │
            └──────────┼──────────┘
                       │
                  South (180°)

    ● = Camera standing position
    Sweep trajectory: 0° → 360° (full room scan)
```

---

## 5. Mode 2: Live Detection — Deep Dive

### Continuous Real-Time Stream

In this mode, the phone streams full-speed video and the Mac runs YOLO inference on every single frame.

### Use Cases

#### A. Room Walk-Through (Live Object Labeling)
- Walk around with the phone pointed forward.
- Every object is labeled in real-time with bounding boxes and class names.
- A running HUD counter shows category tallies.

#### B. Driving / Forward Hazard Warning
- Phone mounted on car dashboard or held forward.
- A **Collision Warning Zone** (configurable ROI rectangle in the center/lower region of the frame).
- Any object (`person`, `car`, `truck`, `bicycle`, `dog`) whose bounding box overlaps this zone triggers a **red flash warning**.
- Proximity is estimated by tracking the rate of bounding box expansion (growing rapidly = approaching fast).

#### C. RC Car — Custom Model
- Switch the model dropdown from `yolov8n.pt` (general) to a custom-trained `rc_car_best.pt`.
- Press `C` on the keyboard at any time to capture the current frame + labels into an `rc_car_dataset/` folder for training data collection.
- Train the custom model directly on the M5 Mac:
  ```python
  model.train(data='rc_car.yaml', epochs=50, imgsz=640, device='mps')
  ```

---

## 6. Technology Stack

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Android App** | Kotlin + CameraX + NanoHTTPD | Native hardware camera access, embedded HTTP server for MJPEG streaming, sensor API for rotation vectors. |
| **USB Bridge** | ADB Port Forwarding (`adb forward tcp:8080 tcp:8080`) | Zero-config, no IP addresses, no Wi-Fi dependency, ~25ms latency, phone charges while streaming. |
| **Desktop AI Engine** | Python 3 + Ultralytics YOLOv8n/v11n | Best speed-to-accuracy ratio. Natively supports Apple Silicon Metal (`device='mps'`). Exportable to ONNX (Windows) and CoreML (Mac). |
| **Desktop GUI** | PyQt6 + OpenCV | Cross-platform (Mac + Windows), native look and feel, efficient frame rendering. |
| **Sensor Fusion** | Android `TYPE_ROTATION_VECTOR` (or ARCore for full 6-DoF) | Gyroscope + magnetometer fusion gives drift-free yaw/pitch/roll. ARCore adds positional tracking. |
| **Spatial Dedup** | Angular binning + CLIP/MobileNet feature matching | Prevents double-counting objects seen from multiple angles during room sweep. |
| **Optional VLM Q&A** | Qwen2.5-VL-7B or Moondream2 via Apple MLX | Local on-device vision-language model for natural language queries about the room ("Where did I leave my keys?"). |

---

## 7. Hardware Requirements

### Minimum

| Component | Requirement |
| :--- | :--- |
| **Mac/PC** | Any Apple Silicon Mac (M1 or later) OR Windows PC with 8GB+ RAM. Dedicated GPU optional but accelerates inference. |
| **Android Phone** | Android 8.0+ with USB Debugging enabled. Gyroscope sensor required. |
| **Cable** | USB-C to USB-C (or USB-C to USB-A) data cable. |

### Target Development Machine

| Spec | Value |
| :--- | :--- |
| **Machine** | MacBook Pro with Apple M5 chip |
| **OS** | macOS 27.0 (arm64) |
| **Expected YOLO Inference** | < 8ms per frame (~80–120 FPS capable) via Metal Performance Shaders |
| **Expected VLM Query** | 1.5–3 seconds per natural language query via MLX |

---

## 8. Implementation Phases

### Phase 1: Core Detection Pipeline Validation (Days 1–2)

**Goal:** Prove that YOLO runs at 60+ FPS on the M5 Mac with acceptable accuracy.

- [ ] Set up Python virtual environment with `ultralytics`, `opencv-python`, `torch` (MPS backend).
- [ ] Run YOLOv8n inference on the Mac's built-in webcam or a test video file.
- [ ] Benchmark: measure FPS, latency, memory usage, and thermal behavior.
- [ ] Build the multi-threaded frame buffer (producer-consumer pattern with queue size = 1).

**Success Criteria:** Sustained 60+ FPS inference with < 10ms per frame on M5 MPS.

---

### Phase 2: USB-C Bridge & Phone Streaming (Days 3–4)

**Goal:** Establish a reliable, low-latency video + sensor data stream from the Android phone to the Mac over USB-C.

- [ ] Verify ADB connection: `adb devices` detects the phone over USB.
- [ ] Set up port forwarding: `adb forward tcp:8080 tcp:8080`.
- [ ] Build minimal Android app (Kotlin):
  - CameraX preview capturing 720p @ 30 FPS.
  - NanoHTTPD embedded server streaming MJPEG on `localhost:8080/video`.
  - Sensor endpoint streaming rotation vector JSON on `localhost:8080/sensors`.
- [ ] Mac app connects to `http://127.0.0.1:8080/video` via OpenCV and displays frames.

**Success Criteria:** Live video from phone camera appears on Mac screen over USB-C with < 50ms end-to-end latency.

---

### Phase 3: Mode 2 — Live Detection Engine (Days 5–6)

**Goal:** Real-time object detection with bounding boxes, labels, counters, and collision warnings.

- [ ] Integrate YOLO inference into the USB video pipeline.
- [ ] Build the HUD overlay:
  - Colored bounding boxes with class labels and confidence scores.
  - Running object count panel (sidebar or overlay).
  - FPS counter and connection status bar.
- [ ] Build the Collision Warning Zone:
  - Configurable center/lower ROI rectangle.
  - Red flash alert when a critical object enters the zone.
  - Bounding box expansion rate tracking for proximity estimation.
- [ ] Model hot-swap dropdown (switch between `yolov8n.pt` and custom models).

**Success Criteria:** Smooth 30+ FPS live detection with accurate bounding boxes and responsive collision warnings.

---

### Phase 4: Mode 1 — Spatial Room Map Engine (Days 7–10)

**Goal:** Sensor-triggered keyframe capture with spatial deduplication and room inventory output.

- [ ] Android app: stream `TYPE_ROTATION_VECTOR` sensor data alongside video frames.
- [ ] Mac app: implement keyframe trigger logic (Δyaw ≥ 30° or Δpitch ≥ 20°).
- [ ] Run YOLO on each keyframe only (not every frame — saves 95% of compute).
- [ ] Implement angular binning for spatial deduplication:
  - Calculate each object's world-angle from keyframe yaw + bbox horizontal position.
  - Merge detections within ±15° angular tolerance as the same physical object.
- [ ] Generate the 2D top-down room map visualization.
- [ ] Generate the deduplicated inventory table.

**Success Criteria:** A 360° room sweep produces an accurate count of unique objects with ≤ 10% error rate and zero obvious duplicates.

---

### Phase 5: Desktop Dashboard & Polish (Days 11–13)

**Goal:** Unified PyQt6 desktop application with clean UI.

- [ ] Tab-based layout: **Room Map** tab and **Live Detection** tab.
- [ ] Room Map tab:
  - "Start Scan" / "Stop Scan" buttons.
  - Live keyframe counter showing how many unique angles have been captured.
  - Room map canvas (2D radar view).
  - Inventory results table.
- [ ] Live Detection tab:
  - Full-screen video feed with overlay.
  - Sidebar controls: model selector, confidence slider, class filter.
  - Collision zone toggle and sensitivity adjustment.
- [ ] Connection status bar: "Phone Connected (USB)" / "Phone Disconnected".
- [ ] Auto-detect phone via `adb devices` polling on app startup.

---

### Phase 6: Android App Polish (Days 14–15)

**Goal:** Clean, installable Android companion app.

- [ ] Material Design 3 UI with camera preview.
- [ ] Mode indicator: "Streaming to PC" / "Waiting for Connection".
- [ ] Resolution selector (480p / 720p / 1080p).
- [ ] Sensor status indicators (gyroscope active, rotation vector calibrated).
- [ ] Build signed APK for side-loading.

---

### Phase 7: RC Car Custom Model Training (Days 16–18)

**Goal:** End-to-end custom model training pipeline using the app itself.

- [ ] Dataset Collector mode: capture frames + YOLO auto-labels into `rc_car_dataset/`.
- [ ] Label review/correction tool (or use existing tool like Label Studio).
- [ ] Train custom YOLOv8n on M5 Mac using MPS acceleration.
- [ ] Export trained model and load it via the model switcher dropdown.
- [ ] Validate detection accuracy on live RC car feed.

---

### Phase 8 (Optional): VLM Natural Language Q&A (Days 19–20)

**Goal:** Ask questions about the room in plain English after a scan.

- [ ] Integrate a local Vision-Language Model (Qwen2.5-VL-7B or Moondream2) via Apple MLX.
- [ ] Feed the captured keyframes into the VLM as a multi-image context.
- [ ] Add a chat/prompt box in the Room Map tab:
  - User types: *"How many monitors are on the desk?"*
  - VLM responds: *"There is 1 monitor on the desk, along with a keyboard and a coffee mug."*

---

## 9. Risk Assessment

| Risk | Severity | Mitigation |
| :--- | :--- | :--- |
| **Python 3.14 compatibility issues** with PyTorch/Ultralytics | High | Create a dedicated virtual environment with Python 3.11 or 3.12 (install via `brew install python@3.12`). |
| **Phone sensor drift** causing incorrect keyframe angles | Medium | Use `TYPE_ROTATION_VECTOR` (hardware-fused), NOT raw accelerometer. Recalibrate magnetometer before each scan. |
| **Objects partially visible** across keyframe boundaries causing missed or split detections | Medium | Use overlapping frustums (capture at 25° intervals instead of 35°) and merge objects within ±15° tolerance. |
| **Low-light camera quality** degrading detection accuracy | Low | Add a "Low Light Mode" toggle that reduces resolution to 480p but increases exposure/gain on the phone. |
| **USB cable disconnection** during active session | Low | Implement reconnection watchdog: auto-pause inference and resume when ADB device reappears. |

---

## 10. Directory Structure (Planned)

```
Nandhini_phy_mini_project/
├── README.md                        # Project overview and setup instructions
├── requirements.txt                 # Python dependencies
│
├── android_app/                     # Android companion app (Kotlin)
│   ├── app/
│   │   └── src/main/
│   │       ├── java/.../
│   │       │   ├── MainActivity.kt          # Camera preview + mode selection
│   │       │   ├── CameraStreamService.kt   # CameraX + MJPEG server
│   │       │   └── SensorService.kt         # Rotation vector sensor publisher
│   │       └── res/layout/
│   │           └── activity_main.xml
│   ├── build.gradle.kts
│   └── settings.gradle.kts
│
├── desktop_app/                     # Mac/Windows desktop app (Python)
│   ├── main.py                      # Application entry point
│   ├── ui/
│   │   ├── dashboard.py             # PyQt6 main window with tab layout
│   │   ├── room_map_tab.py          # Mode 1: Room Map UI
│   │   └── live_detection_tab.py    # Mode 2: Live Detection UI
│   ├── core/
│   │   ├── frame_buffer.py          # Multi-threaded frame ingestion worker
│   │   ├── inference_engine.py      # YOLO model loader and inference runner
│   │   ├── adb_bridge.py            # ADB device detection and port forwarding
│   │   └── collision_zone.py        # ROI-based hazard warning logic
│   ├── spatial/
│   │   ├── keyframe_selector.py     # Sensor-triggered keyframe capture logic
│   │   ├── angular_dedup.py         # Spatial deduplication via angular binning
│   │   └── room_map_renderer.py     # 2D top-down room map visualization
│   └── models/
│       ├── yolov8n.pt               # Default general-purpose model
│       └── (custom models go here)
│
├── rc_car_dataset/                  # Auto-generated training data
│   ├── images/
│   └── labels/
│
└── docs/
    └── PROJECT_BLUEPRINT.md         # This document
```

---

## 11. Summary

**What we are building:** A dual-mode, offline, USB-C connected object detection system that uses an Android phone as a smart camera sensor and a MacBook Pro M5 as the AI compute engine.

**Mode 1 (Room Map):** Sensor-guided keyframe capture eliminates duplicate counting. Walk around the room once, get an exact deduplicated inventory and a 2D spatial map.

**Mode 2 (Live Detection):** Full-speed 60 FPS real-time object detection with collision warnings for driving, live labeling for exploration, and custom model support for RC cars.

**All processing on the Mac. Phone is just a sensor. No internet required. No cloud. No subscriptions.**
