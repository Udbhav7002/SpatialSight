SPATIALSIGHT - WINDOWS EDITION
==============================

HOW TO RUN
----------
1. Copy this whole "Windows" folder to your Windows PC (e.g. Desktop).
2. Install Python 3.10-3.12 from https://www.python.org/downloads/
   IMPORTANT: during install, tick "Add Python to PATH".
3. Double-click  SpatialSight.bat

The first run installs everything automatically (5-15 minutes, one time).
After that, double-clicking SpatialSight.bat starts the dashboard instantly.

WHAT IT DOES
------------
- Live Detection tab: real-time object detection with bounding boxes,
  live counts, physics-based forward collision warning corridor and an
  optional Arduino traffic-light bridge.
- Room Map tab: sensor-guided 360 degree room scanning using your Android
  phone camera + orientation sensors, with spatial deduplication.

PHONE CONNECTION (optional, for USB phone camera)
-------------------------------------------------
1. On the phone: enable USB debugging (Settings > Developer options).
2. Connect the phone with a USB data cable.
3. Install "platform-tools" (adb) and run:
       adb forward tcp:8080 tcp:8080
4. In the app, select source "usb".

OPTIONAL .EXE BUILD
-------------------
Run build_windows_exe.bat once (on Windows) to produce a standalone
SpatialSight.exe in app\dist\. Requires the first-run setup to be done.
