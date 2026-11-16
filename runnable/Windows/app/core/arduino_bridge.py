"""
Arduino Bridge - Serial communication, Environmental Physics, and Simulation Engine.

Communicates with the Arduino Uno:
- Sends traffic signal commands ('GREEN', 'YELLOW', 'RED', 'BLINK_RED')
- Receives rain/water level sensor readings from analog pin A0
- Computes real-time road friction (mu) and stopping distance physics multiplier
- Includes interactive Simulation Mode to demonstrate wet road physics live in class!
"""

import time
import threading
import logging
from typing import Optional, Tuple, Dict, Any

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

logger = logging.getLogger(__name__)


class ArduinoBridge:
    """Manages USB-Serial communication with Arduino Uno and environmental physics."""

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_connected = False
        self.last_heartbeat: float = 0.0

        # Telemetry & Physics State
        self.raw_rain_adc: int = 0
        self.filtered_adc: Optional[float] = None
        self.wetness_percent: float = 0.0          # 0.0% (dry) to 100.0% (flooded)
        self.friction_mu: float = 0.80             # Dry asphalt mu ~ 0.80, Wet mu ~ 0.35
        self.stopping_dist_multiplier: float = 1.0  # 1.0x (dry) up to 2.3x (wet)
        self.current_signal: str = "GREEN"

        # Simulation Mode Override (for classroom demos)
        self.simulation_mode: bool = False
        self.simulated_wetness: float = 0.0

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    @staticmethod
    def find_arduino_port() -> Optional[str]:
        """Auto-detect connected Arduino Uno / CH340 / USB serial device."""
        if serial is None:
            return None
        try:
            import glob
            # Direct check for macOS serial devices first
            mac_ports = sorted(
                glob.glob("/dev/cu.usbmodem*") +
                glob.glob("/dev/cu.usbserial*") +
                glob.glob("/dev/cu.wchusbserial*")
            )
            if mac_ports:
                return mac_ports[0]

            ports = list(serial.tools.list_ports.comports())
            for p in ports:
                desc = (p.description or "").lower()
                hwid = (p.hwid or "").lower()
                dev = (p.device or "").lower()
                if any(k in desc or k in hwid or k in dev for k in ["ch340", "ch341", "arduino", "usbmodem", "usbserial", "wchusbserial", "ftdi", "cp210"]):
                    return p.device
            for p in ports:
                dev = (p.device or "").lower()
                if "usb" in dev and "bluetooth" not in dev and "debug" not in dev:
                    return p.device
        except Exception as e:
            logger.warning(f"Error enumerating serial ports: {e}")
        return None

    def connect(self) -> bool:
        """Attempt connection to Arduino Uno."""
        if serial is None:
            self.is_connected = False
            return False

        if self.serial_conn is not None:
            try:
                self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None

        detected_port = self.port or self.find_arduino_port()
        if not detected_port:
            self.is_connected = False
            return False

        try:
            self.serial_conn = serial.Serial(detected_port, self.baudrate, timeout=0.1)
            time.sleep(1.8)  # Wait for Arduino bootloader reset
            self.port = detected_port
            self.is_connected = True
            self.last_heartbeat = time.time()
            logger.info(f"Connected to Arduino on {self.port}")
            self.send_signal(self.current_signal or "GREEN")
            return True
        except Exception as e:
            logger.debug(f"Could not open Arduino port {detected_port}: {e}")
            if self.serial_conn is not None:
                try:
                    self.serial_conn.close()
                except Exception:
                    pass
                self.serial_conn = None
            self.port = None
            self.is_connected = False
            return False

    def start(self):
        """Start background polling thread."""
        self.connect()
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True, name="ArduinoThread")
        self._thread.start()

    def stop(self):
        """Stop background worker and close serial port."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self.serial_conn:
            try:
                # Revert to safe Green state when closing
                self.send_signal("GREEN")
                time.sleep(0.08)
                self.serial_conn.close()
            except Exception:
                pass
            self.serial_conn = None
        self.is_connected = False

    def send_waiting_cycle(self):
        """Send command to cycle Red -> Yellow -> Green sequentially when waiting for phone/camera."""
        self.send_signal("WAITING")

    def send_signal(self, signal: str):
        """
        Send traffic light signal command: 'GREEN', 'YELLOW', 'RED', 'BLINK_RED'.
        Always updates the current_signal state so GUI virtual lights work even without hardware.
        """
        with self._lock:
            self.current_signal = signal
            if self.is_connected and self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.write(f"{signal}\n".encode("utf-8"))
                    self.serial_conn.flush()
                except Exception as e:
                    logger.warning(f"Error sending signal to Arduino: {e}")
                    self.is_connected = False
                    try:
                        self.serial_conn.close()
                    except Exception:
                        pass
                    self.serial_conn = None

    def set_inverted_polarity(self, inverted: bool):
        """Toggle active-low vs active-high LED polarity on Arduino hardware."""
        with self._lock:
            cmd = "INVERT_ON" if inverted else "INVERT_OFF"
            if self.is_connected and self.serial_conn and self.serial_conn.is_open:
                try:
                    self.serial_conn.write(f"{cmd}\n".encode("utf-8"))
                    self.serial_conn.flush()
                except Exception as e:
                    logger.warning(f"Error setting polarity: {e}")

    def set_simulation_override(self, enabled: bool, wetness_percent: float = 0.0):
        """
        Enable/disable interactive simulation override.
        Allows the presenter to drag a slider and demonstrate wet road physics live!
        """
        with self._lock:
            self.simulation_mode = enabled
            self.simulated_wetness = max(0.0, min(100.0, wetness_percent))
            if enabled:
                # Map 0-100% to simulated ADC 0-350
                simulated_adc = int((self.simulated_wetness / 100.0) * 350.0)
                self._update_physics_state(simulated_adc, is_simulated=True)

    def _read_loop(self):
        """Continuously reads sensor telemetry lines from Arduino and sends keep-alives."""
        last_keepalive = time.time()
        while self._running:
            now = time.time()
            if self.is_connected and (now - last_keepalive >= 1.5):
                last_keepalive = now
                self.send_signal(self.current_signal)
            if not self.is_connected or not self.serial_conn or not self.serial_conn.is_open:
                time.sleep(1.5)
                self.connect()
                continue

            try:
                raw_bytes = self.serial_conn.readline()
                if raw_bytes:
                    line = raw_bytes.decode("utf-8", errors="ignore").strip()
                    if line.startswith("RAIN:"):
                        self.last_heartbeat = time.time()
                        val_str = line.split(":", 1)[1]
                        if val_str.isdigit():
                            self.raw_rain_adc = int(val_str)
                            if not self.simulation_mode:
                                self._update_physics_state(int(val_str), is_simulated=False)
                    elif line.startswith("STATUS:"):
                        self.last_heartbeat = time.time()
            except Exception as e:
                logger.debug(f"Arduino read loop warning: {e}")
                self.is_connected = False
                if self.serial_conn:
                    try:
                        self.serial_conn.close()
                    except Exception:
                        pass
                    self.serial_conn = None
                time.sleep(1.0)

            # Heartbeat watchdog
            if self.is_connected and (time.time() - self.last_heartbeat) > 4.0:
                logger.warning("Arduino heartbeat timeout. Reconnecting...")
                self.is_connected = False
                if self.serial_conn:
                    try:
                        self.serial_conn.close()
                    except Exception:
                        pass
                    self.serial_conn = None

            time.sleep(0.02)

    @property
    def is_water_detected(self) -> bool:
        """
        User Requirement 1: True when water sensor detects water/rain.
        Raw rain ADC >= 25 or wetness_percent >= 10.0%.
        """
        if self.simulation_mode:
            return self.simulated_wetness >= 10.0
        return (self.wetness_percent >= 10.0) or (self.raw_rain_adc >= 25)

    def _update_physics_state(self, raw_adc: int, is_simulated: bool = False):
        """
        Calculates road surface physics based on rain sensor ADC.
        Dry asphalt: mu ~ 0.80
        Wet / Aquaplaning: mu drops to ~ 0.35
        Stopping Multiplier = 0.80 / mu
        """
        if not is_simulated:
            alpha = 0.3
            if self.filtered_adc is None:
                self.filtered_adc = float(raw_adc)
            else:
                self.filtered_adc = (alpha * raw_adc) + ((1.0 - alpha) * self.filtered_adc)
            self.raw_rain_adc = int(self.filtered_adc)

            dry_thresh = 15
            wet_thresh = 280

            if self.raw_rain_adc <= dry_thresh:
                self.wetness_percent = 0.0
            elif self.raw_rain_adc >= wet_thresh:
                self.wetness_percent = 100.0
            else:
                self.wetness_percent = round((self.raw_rain_adc - dry_thresh) / (wet_thresh - dry_thresh) * 100.0, 1)
        else:
            self.raw_rain_adc = raw_adc
            self.wetness_percent = self.simulated_wetness

        # Physics: Friction coefficient mu
        fraction_wet = self.wetness_percent / 100.0
        self.friction_mu = round(0.80 - (0.80 - 0.35) * fraction_wet, 2)

        # Stopping distance multiplier
        self.stopping_dist_multiplier = round(0.80 / max(0.35, self.friction_mu), 2)

    def get_stopping_distance_m(self, speed_kmh: float) -> float:
        """Kinematic stopping distance formula: s = v^2 / (2 * mu * g) where g=9.81"""
        v_ms = speed_kmh / 3.6
        return (v_ms ** 2) / (2.0 * max(0.1, self.friction_mu) * 9.81)

    def get_kinetic_energy_j(self, speed_kmh: float, mass_kg: float = 1500.0) -> float:
        """Kinetic energy: KE = 0.5 * m * v^2"""
        v_ms = speed_kmh / 3.6
        return 0.5 * mass_kg * (v_ms ** 2)

    def _get_road_condition_info(self) -> Tuple[str, str]:
        """Returns (condition_label, icon_text)."""
        if self.wetness_percent <= 10:
            return "DRY", ""
        elif self.wetness_percent <= 35:
            return "DAMP", ""
        elif self.wetness_percent <= 65:
            return "WET", ""
        elif self.wetness_percent <= 85:
            return "HEAVY RAIN", ""
        else:
            return "AQUAPLANING / FLOOD", ""

    def get_physics_summary(self, speed_kmh: float = 50.0) -> Dict[str, Any]:
        """Returns environmental physics state and kinematic calculations."""
        road_condition, emoji = self._get_road_condition_info()
        v_ms = speed_kmh / 3.6
        s_dist = self.get_stopping_distance_m(speed_kmh)
        ke_kj = self.get_kinetic_energy_j(speed_kmh) / 1000.0

        return {
            "is_connected": self.is_connected,
            "simulation_mode": self.simulation_mode,
            "port": self.port if self.is_connected else ("Virtual Simulator" if self.simulation_mode else "Disconnected"),
            "raw_adc": self.raw_rain_adc,
            "wetness_percent": self.wetness_percent,
            "friction_mu": self.friction_mu,
            "stopping_dist_multiplier": self.stopping_dist_multiplier,
            "road_condition": road_condition,
            "road_emoji": emoji,
            "speed_kmh": speed_kmh,
            "stopping_distance_m": round(s_dist, 1),
            "kinetic_energy_kj": round(ke_kj, 1),
            "formula_text": f"s = ({v_ms:.1f})^2 / (2 * {self.friction_mu:.2f} * 9.81) = {s_dist:.1f}m",
            "signal": self.current_signal,
        }
