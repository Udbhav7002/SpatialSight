# SpatialSight - Runnable Apps

Double-click launchers for every platform. No build steps, no commands to type.

```
runnable/
├── macOS/          Double-click SpatialSight.app
├── Windows/        Double-click SpatialSight.bat (on a Windows PC)
└── Android/        Install SpatialSight.apk on the phone
```

## macOS (Apple Silicon M1-M5)

1. Open the `macOS` folder.
2. Double-click **SpatialSight.app**.

- Uses the project's existing Python environment when available (instant start).
- On a fresh Mac it sets everything up automatically on first run (5-15 min, one time).
- If nothing seems to happen, double-click `run_in_terminal.command` to see the logs.

## Windows 10/11

1. Copy the whole `Windows` folder to the Windows PC.
2. Install Python 3.10-3.12 (python.org) - tick **"Add Python to PATH"**.
3. Double-click **SpatialSight.bat**.

First run installs PyTorch/OpenCV/PyQt6 automatically (5-15 min, one time).
Optional: run `build_windows_exe.bat` once to get a standalone `SpatialSight.exe`.

## Android 8.0+

1. Copy `Android/SpatialSight.apk` to the phone and tap it.
2. Allow "install from unknown sources" when prompted.

The phone acts as the camera + sensor unit; the desktop app renders the
detections, room map and collision warnings. Connect over USB (`adb forward
tcp:8080 tcp:8080`, then source `usb`) or Wi-Fi (`http://<phone-ip>:8080/video`).

## The full system

| Piece | Role |
|---|---|
| Android app | Camera + orientation sensor streaming (phone) |
| macOS / Windows app | YOLO detection, room map, ADAS collision corridor (compute) |
| Arduino bridge | Tri-color traffic-light signal output (optional) |

See the project `README.md` and `docs/PROJECT_BLUEPRINT.md` for architecture details.
