"""
Sound Controller - Dual-Stage ADAS Alert Audio System.

Features:
- Dual-stage audio alert:
    Stage 1 (Caution zone < 10m): subtle chime / ping tone
    Stage 2 (Emergency zone < 5m): rapid warning tone
- Non-blocking execution in background daemon threads
- Debouncing to prevent audio overlapping
- Zero emojis
"""

import os
import sys
import time
import threading
import subprocess
import logging

logger = logging.getLogger(__name__)


class SoundController:
    """Manages audio warnings for vehicle corridor hazards."""

    def __init__(self):
        self.enabled: bool = False
        self.last_caution_time: float = 0.0
        self.last_emergency_time: float = 0.0
        self.caution_cooldown: float = 2.0
        self.emergency_cooldown: float = 0.8
        self._is_windows = sys.platform.startswith("win")
        self._is_mac = sys.platform == "darwin"

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled

    def trigger_caution_alert(self) -> None:
        """Subtle chime for caution hazard (< 10m)."""
        if not self.enabled:
            return
        now = time.time()
        if now - self.last_caution_time < self.caution_cooldown:
            return
        self.last_caution_time = now
        threading.Thread(target=self._play_caution, daemon=True).start()

    def trigger_emergency_alert(self) -> None:
        """Rapid warning tone for imminent emergency hazard (< 5m)."""
        if not self.enabled:
            return
        now = time.time()
        if now - self.last_emergency_time < self.emergency_cooldown:
            return
        self.last_emergency_time = now
        threading.Thread(target=self._play_emergency, daemon=True).start()

    def _play_caution(self) -> None:
        try:
            if self._is_mac:
                for sound in ["/System/Library/Sounds/Tink.aiff", "/System/Library/Sounds/Ping.aiff"]:
                    if os.path.exists(sound):
                        subprocess.run(["afplay", sound], timeout=1.0)
                        return
                print("\a", end="", flush=True)
            elif self._is_windows:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
            else:
                print("\a", end="", flush=True)
        except Exception as e:
            logger.debug(f"Audio playback error: {e}")

    def _play_emergency(self) -> None:
        try:
            if self._is_mac:
                for sound in ["/System/Library/Sounds/Sosumi.aiff", "/System/Library/Sounds/Basso.aiff"]:
                    if os.path.exists(sound):
                        subprocess.run(["afplay", sound], timeout=1.0)
                        return
                print("\a\a", end="", flush=True)
            elif self._is_windows:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONHAND)
            else:
                print("\a\a", end="", flush=True)
        except Exception as e:
            logger.debug(f"Audio playback error: {e}")
