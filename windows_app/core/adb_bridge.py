"""
ADB Bridge — Handles USB device detection and port forwarding.

Responsibilities:
- Detect connected Android phones via `adb devices`
- Set up TCP port forwarding over USB-C: `adb forward tcp:8080 tcp:8080`
- Monitor connection status and handle reconnection
"""

import os
import shutil
import subprocess
import logging

logger = logging.getLogger(__name__)

def _find_adb() -> str:
    """Find adb executable on Windows or system PATH."""
    if shutil.which("adb"):
        return "adb"
    if shutil.which("adb.exe"):
        return "adb.exe"
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    candidates = [
        os.path.join(local_app_data, "Android", "Sdk", "platform-tools", "adb.exe"),
        r"C:\platform-tools\adb.exe",
        r"C:\Program Files\Android\platform-tools\adb.exe",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return "adb"

ADB_CMD = _find_adb()
DEFAULT_LOCAL_PORT = 8080
DEFAULT_REMOTE_PORT = 8080


def is_adb_available() -> bool:
    """Check if adb binary is on PATH."""
    try:
        result = subprocess.run(
            [ADB_CMD, "version"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_connected_devices() -> list[dict]:
    """
    List connected Android devices via USB.

    Returns:
        List of dicts with 'serial' and 'state' keys.
        Example: [{'serial': 'ABCD1234', 'state': 'device'}]
    """
    try:
        result = subprocess.run(
            [ADB_CMD, "devices"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            logger.error(f"adb devices failed: {result.stderr}")
            return []

        devices = []
        for line in result.stdout.strip().split("\n")[1:]:  # Skip header
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) == 2:
                devices.append({"serial": parts[0], "state": parts[1]})

        return devices
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"Failed to list devices: {e}")
        return []


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

    This tunnels the phone's internal HTTP server over the USB-C cable,
    making it accessible at http://127.0.0.1:{local_port} on the Mac.

    Args:
        local_port: Port on the Mac to listen on.
        remote_port: Port on the phone where the camera stream server runs.
        serial: Specific device serial (optional, uses first device if None).

    Returns:
        True if forwarding was set up successfully.
    """
    cmd = [ADB_CMD]
    if serial:
        cmd.extend(["-s", serial])
    cmd.extend(["forward", f"tcp:{local_port}", f"tcp:{remote_port}"])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            logger.info(
                f"Port forwarding active: localhost:{local_port} -> phone:{remote_port}"
            )
            return True
        else:
            logger.error(f"Port forwarding failed: {result.stderr}")
            return False
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        logger.error(f"Failed to set up port forwarding: {e}")
        return False


def remove_port_forward(local_port: int = DEFAULT_LOCAL_PORT) -> bool:
    """Remove a previously set up port forwarding rule."""
    try:
        result = subprocess.run(
            [ADB_CMD, "forward", "--remove", f"tcp:{local_port}"],
            capture_output=True, text=True, timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_stream_url(local_port: int = DEFAULT_LOCAL_PORT) -> str:
    """Get the local URL for the phone's MJPEG camera stream."""
    return f"http://127.0.0.1:{local_port}/video"


def get_sensor_url(local_port: int = DEFAULT_LOCAL_PORT) -> str:
    """Get the local URL for the phone's sensor telemetry endpoint."""
    return f"http://127.0.0.1:{local_port}/sensors"
