# SpatialSight — Android Companion App

Native Android application built in Kotlin that acts as an ultra-low latency camera sensor with drift-free orientation telemetry over USB-C.

---

## What It Does
* **CameraX Video Capture:** Captures 720p @ 30 FPS back camera video.
* **Embedded MJPEG Server (NanoHTTPD):** Streams compressed video on `localhost:8080/video`.
* **Sensor Telemetry (Rotation Vector):** Fuses gyroscope + magnetometer (`TYPE_ROTATION_VECTOR`) to provide continuous yaw, pitch, and roll on `localhost:8080/sensors`.
* **Zero Cloud / Zero Network:** Functions entirely offline over the USB-C cable.

---

## How to Build & Install

### Option A: Using Android Studio (Recommended)
1. Open Android Studio.
2. Select **Open** and choose this `android_app` directory.
3. Let Gradle sync dependencies.
4. Connect your Android phone with **USB Debugging** enabled.
5. Click **Run** (`Shift + F10`) or go to **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
6. Install the generated `.apk` on your phone.

### Option B: Using Command Line (Gradle)
```bash
./gradlew assembleDebug
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

---

## How to Connect to PC/Mac
1. Connect phone to PC or Mac via USB-C cable.
2. On PC/Mac terminal, forward the internal port:
   ```bash
   adb forward tcp:8080 tcp:8080
   ```
3. Open the SpatialSight app on the phone and tap **Start Streaming**.
4. Launch the desktop app on your Mac (`./run_mac.sh --source usb`) or Windows (`run_windows.bat`).
