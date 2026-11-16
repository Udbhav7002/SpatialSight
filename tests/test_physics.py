"""Unit tests for Environmental Physics, Kinematics, and Arduino Bridge."""

import pytest
import math
import sys
import os

# Ensure mac_app is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from core.arduino_bridge import ArduinoBridge


def test_dry_road_physics():
    bridge = ArduinoBridge()
    # Baseline dry road state
    summary = bridge.get_physics_summary(speed_kmh=50.0)
    assert summary["friction_mu"] == pytest.approx(0.80, abs=0.02)
    assert summary["stopping_dist_multiplier"] == pytest.approx(1.0, abs=0.05)
    assert "DRY" in summary["road_condition"]

    # Kinematics: s = v^2 / (2 * mu * g), v = 50 km/h = 13.889 m/s
    v_ms = 50.0 / 3.6
    expected_s = (v_ms ** 2) / (2.0 * 0.80 * 9.81)
    assert summary["stopping_distance_m"] == pytest.approx(expected_s, abs=0.5)

    # Kinetic Energy: KE = 0.5 * m * v^2 for 1500 kg
    expected_ke_kj = 0.5 * 1500.0 * (v_ms ** 2) / 1000.0
    assert summary["kinetic_energy_kj"] == pytest.approx(expected_ke_kj, abs=1.0)


def test_wet_road_simulation_override():
    bridge = ArduinoBridge()
    # Simulate heavy rain / aquaplaning (100% wetness)
    bridge.set_simulation_override(enabled=True, wetness_percent=100.0)

    summary = bridge.get_physics_summary(speed_kmh=50.0)
    assert summary["simulation_mode"] is True
    assert summary["wetness_percent"] == 100.0
    # Friction drops to ~0.35 on wet/flooded road
    assert summary["friction_mu"] == pytest.approx(0.35, abs=0.02)
    # Stopping distance multiplier rises to ~2.29x
    assert summary["stopping_dist_multiplier"] == pytest.approx(0.80 / 0.35, abs=0.05)
    assert "AQUAPLANING" in summary["road_condition"] or "FLOOD" in summary["road_condition"]

    # Stopping distance should be ~2.3x longer than dry road
    dry_s = ( (50.0 / 3.6) ** 2 ) / (2.0 * 0.80 * 9.81)
    wet_s = summary["stopping_distance_m"]
    assert wet_s > dry_s * 2.0


def test_damp_road_simulation():
    bridge = ArduinoBridge()
    # 50% wetness
    bridge.set_simulation_override(enabled=True, wetness_percent=50.0)
    summary = bridge.get_physics_summary(speed_kmh=60.0)

    expected_mu = 0.80 - (0.80 - 0.35) * 0.5
    assert summary["friction_mu"] == pytest.approx(expected_mu, abs=0.02)
    assert "WET" in summary["road_condition"] or "DAMP" in summary["road_condition"]


def test_virtual_signal_transmission():
    bridge = ArduinoBridge()
    # When Arduino is not physically connected, sending signal updates state safely
    bridge.send_signal("RED")
    assert bridge.current_signal == "RED"
    bridge.send_signal("YELLOW")
    assert bridge.current_signal == "YELLOW"
    bridge.send_signal("GREEN")
    assert bridge.current_signal == "GREEN"


def test_water_detection_rule_logic():
    """Rule 1: Water detected -> is_water_detected is True, wet road caution."""
    bridge = ArduinoBridge()
    assert bridge.is_water_detected is False

    # Simulate water detected
    bridge.set_simulation_override(enabled=True, wetness_percent=25.0)
    assert bridge.is_water_detected is True

    # High wetness
    bridge.set_simulation_override(enabled=True, wetness_percent=80.0)
    assert bridge.is_water_detected is True

    # Back to dry
    bridge.set_simulation_override(enabled=True, wetness_percent=0.0)
    assert bridge.is_water_detected is False
