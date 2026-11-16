SPATIALSIGHT - ANDROID APP
==========================

HOW TO INSTALL (no computer needed on the phone side)
-----------------------------------------------------
1. Copy SpatialSight.apk to your Android phone
   (USB cable, Google Drive, email - anything works).
2. On the phone, tap the APK file.
3. Android will ask for permission to install from unknown sources.
   Allow it for the app you used to open the APK (Files/Chrome/Drive).
4. Tap Install, then Open.

Requires Android 8.0 or newer.

WHAT THE APP DOES
-----------------
The phone is the SENSOR + CAMERA unit:
- Streams the camera feed over Wi-Fi/USB (MJPEG, port 8080)
- Streams orientation sensor data (yaw / pitch / roll) as JSON
- Shows a live preview with Start / Stop stream controls

HOW TO CONNECT IT TO THE MAC OR WINDOWS APP
-------------------------------------------
USB (recommended - low latency):
  1. Enable USB debugging: Settings > About phone > tap "Build number" 7x,
     then Settings > Developer options > USB debugging ON.
  2. Connect the USB-C data cable.
  3. On the computer, install Android platform-tools (adb), then run:
         adb forward tcp:8080 tcp:8080
  4. Start streaming in the phone app, then select source "usb"
     in the desktop dashboard.

Wi-Fi (both devices on the same network):
  1. Start the stream on the phone; note the IP shown in the app.
  2. In the desktop dashboard, set the source to:
         http://<phone-ip>:8080/video
