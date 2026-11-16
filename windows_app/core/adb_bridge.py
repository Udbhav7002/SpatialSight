"""
ADB Bridge - Handles USB device detection, port forwarding, and orientation sensor streaming.

Responsibilities:
- Detect connected Android phones via `adb devices`
- Detect authorization and connection status
- Set up TCP port forwarding over USB-C: `adb forward tcp:8080 tcp:8080`
- Query real-time phone orientation sensor telemetry (yaw, pitch, roll) from /sensors
- Background sensor polling thread for zero-latency retrieval
"""

import os
import shutil
import subprocess
import threading
import time
import logging
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

DEFAULT_LOCAL_PORT = 8080
DEFAULT_REMOTE_PORT = 8080


def get_adb_binary() -> str:
    """Find the best available adb executable path on macOS / Linux / Windows."""
    which_adb = shutil.which("adb")
    if which_adb:
        return which_adb

    common_paths = [
        "/opt/homebrew/bin/adb",
        "/usr/local/bin/adb",
        os.path.expanduser("~/Library/Android/sdk/platform-tools/adb"),
        os.path.expanduser("~/Android/Sdk/platform-tools/adb"),
        r"C:\Program Files\Android\platform-tools\adb.exe",
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return "adb"


ADB_CMD = get_adb_binary()


def is_adb_available() -> bool:
    """Check if adb binary is available and functional."""
    adb_bin = get_adb_binary()
    try:
        result = subprocess.run(
            [adb_bin, "version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_connected_devices() -> list[dict]:
    """List connected Android devices via USB."""
    adb_bin = get_adb_binary()
    try:
        result = subprocess.run(
            [adb_bin, "devices"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return []

        devices = []
        for line in result.stdout.strip().split("\n")[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                devices.append({"serial": parts[0], "state": parts[1]})

        return devices
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []


def get_phone_status() -> dict:
    """
    Get detailed diagnostic status of the Android phone connection.
    Returns:
      {
         "adb_available": bool,
         "state": "device" | "unauthorized" | "offline" | "disconnected" | "no_adb",
         "serial": str,
         "message": str
      }
    """
    if not is_adb_available():
        return {
            "adb_available": False,
            "state": "no_adb",
            "serial": "",
            "message": "ADB not found. Install Android Platform Tools."
        }

    devices = get_connected_devices()
    if not devices:
        return {
            "adb_available": True,
            "state": "disconnected",
            "serial": "",
            "message": "No Android device detected over USB."
        }

    for d in devices:
        if d["state"] == "device":
            return {
                "adb_available": True,
                "state": "device",
                "serial": d["serial"],
                "message": f"Connected & Authorized ({d['serial']})"
            }
        elif d["state"] == "unauthorized":
            return {
                "adb_available": True,
                "state": "unauthorized",
                "serial": d["serial"],
                "message": "Device unauthorized. Tap 'Allow USB debugging' on phone screen."
            }
        elif d["state"] == "offline":
            return {
                "adb_available": True,
                "state": "offline",
                "serial": d["serial"],
                "message": "Device offline. Reconnect USB-C cable."
            }

    return {
        "adb_available": True,
        "state": "disconnected",
        "serial": "",
        "message": "No active device"
    }


def is_phone_connected() -> bool:
    """Check if at least one Android device is connected and authorized."""
    devices = get_connected_devices()
    return any(d["state"] == "device" for d in devices)


def setup_port_forward(
    local_port: int = DEFAULT_LOCAL_PORT,
    remote_port: int = DEFAULT_REMOTE_PORT,
    serial: str | None = None,
) -> bool:
    """
    Set up ADB TCP port forwarding: localhost:local_port -> phone:remote_port.
    """
    adb_bin = get_adb_binary()
    cmd = [adb_bin]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["forward", f"tcp:{local_port}", f"tcp:{remote_port}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info(f"Port forwarding active: localhost:{local_port} -> phone:{remote_port}")
            return True
        else:
            logger.warning(f"Port forwarding failed: {result.stderr}")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.warning(f"Failed to set up port forwarding: {e}")
        return False


def remove_port_forward(local_port: int = DEFAULT_LOCAL_PORT) -> bool:
    """Remove a previously set up port forwarding rule."""
    adb_bin = get_adb_binary()
    try:
        result = subprocess.run(
            [adb_bin, "forward", "--remove", f"tcp:{local_port}"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def launch_android_app(serial: Optional[str] = None, auto_stream: bool = True) -> bool:
    """
    Auto-launch the SpatialSight Android application via ADB:
    adb shell am start -n com.spatialsight.app/.MainActivity [--ez auto_stream true]
    """
    adb_bin = get_adb_binary()
    cmd = [adb_bin]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["shell", "am", "start", "-n", "com.spatialsight.app/.MainActivity"])
    if auto_stream:
        cmd.extend(["--ez", "auto_stream", "true"])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info("Successfully launched Android app via ADB")
            return True
        else:
            logger.warning(f"ADB launch command failed: {result.stderr}")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.warning(f"Failed to execute ADB launch command: {e}")
        return False


def is_stream_active(url: str = "http://127.0.0.1:8080/video", timeout: float = 1.0) -> bool:
    """Check if the MJPEG camera stream endpoint is active and answering HTTP requests."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SpatialSight-Probe"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status in (200, 204)
    except Exception:
        import socket
        try:
            with socket.create_connection(("127.0.0.1", DEFAULT_LOCAL_PORT), timeout=timeout):
                return True
        except Exception:
            return False


def get_stream_url(local_port: int = DEFAULT_LOCAL_PORT) -> str:
    """Get the local URL for the phone's MJPEG camera stream."""
    return f"http://127.0.0.1:{local_port}/video"


def get_sensor_url(local_port: int = DEFAULT_LOCAL_PORT, host: str = "127.0.0.1") -> str:
    """Get the local URL for the phone's sensor telemetry endpoint."""
    return f"http://{host}:{local_port}/sensors"


def fetch_sensor_data(
    local_port: int = DEFAULT_LOCAL_PORT,
    host: str = "127.0.0.1",
    timeout: float = 0.15
) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest rotation vector telemetry from the Android phone.
    Returns dict: {"yaw": float, "pitch": float, "roll": float, "timestamp": float} or None.
    """
    url = get_sensor_url(local_port, host=host)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SpatialSight-Client"})
        with urllib.request.urlopen(req, timeout=timeout) as response:
            if response.status == 200:
                body = response.read().decode("utf-8")
                return json.loads(body)
    except Exception:
        pass
    return None


class SensorStreamWorker:
    """
    Background worker that continuously fetches sensor data from the Android phone.
    Stores the latest sensor readings thread-safely for instant GUI access.
    """

    def __init__(self, local_port: int = DEFAULT_LOCAL_PORT, host: str = "127.0.0.1", poll_hz: float = 30.0):
        self.local_port = local_port
        self.host = host
        self.poll_interval = 1.0 / max(1.0, poll_hz)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        self._latest_sensor: Optional[Dict[str, Any]] = None
        self._is_active = False

    @property
    def is_active(self) -> bool:
        return self._is_active

    def set_host(self, host: str):
        with self._lock:
            self.host = host

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="SensorWorker")
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
            self._thread = None
        self._is_active = False

    def get_latest_sensor(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._latest_sensor.copy() if self._latest_sensor is not None else None

    def _poll_loop(self):
        while self._running:
            data = fetch_sensor_data(self.local_port, host=self.host, timeout=0.15)
            with self._lock:
                if data is not None and "yaw" in data:
                    self._latest_sensor = data
                    self._is_active = True
                else:
                    self._is_active = False
            time.sleep(self.poll_interval)
