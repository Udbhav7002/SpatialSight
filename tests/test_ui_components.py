"""Unit tests for UI components, SoundController, and screen flow."""

import os
import sys
import pytest

# Offscreen QPA platform for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mac_app")))

from PyQt6.QtWidgets import QApplication
from ui.sound_controller import SoundController
from ui.dashboard import StartScreen, DetectionScreen
from ui.connect_modal import ConnectPhoneDialog
from ui.theme import BG, SURFACE, BORDER, TEXT


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def test_sound_controller():
    controller = SoundController()
    assert controller.enabled is False

    # Should not trigger when disabled
    controller.trigger_caution_alert()
    controller.trigger_emergency_alert()

    # Enable sound
    controller.set_enabled(True)
    assert controller.enabled is True
    controller.trigger_caution_alert()
    controller.trigger_emergency_alert()


def test_start_screen(qapp):
    start_called = False

    def on_start():
        nonlocal start_called
        start_called = True

    screen = StartScreen(on_start)
    assert screen.btn_start.text() == "START"
    screen.btn_start.click()
    assert start_called is True

    screen.set_status("Custom Status")
    assert screen.lbl_status.text() == "Custom Status"


def test_detection_screen(qapp):
    stop_called = False

    def on_stop():
        nonlocal stop_called
        stop_called = True

    screen = DetectionScreen(on_stop)
    assert screen.btn_stop.text() == "STOP"
    screen.btn_stop.click()
    assert stop_called is True

    # Test phone connected indicator
    screen.set_phone_connected(True)
    screen.set_phone_connected(False)

    # Test dynamic object list with objects
    active_objs = {
        "person": {"count": 2, "closest_m": 3.4},
        "Car": {"count": 1, "closest_m": 8.1},
    }
    screen.update_objects_list(active_objs)
    assert screen.objects_layout.count() == 2
    cached_person_widget = screen._row_cache["person"][0]

    # Verify widget reuse on next frame (no churn)
    screen.update_objects_list(active_objs)
    assert screen.objects_layout.count() == 2
    assert screen._row_cache["person"][0] is cached_person_widget

    # Test dynamic object list when empty
    screen.update_objects_list({})
    assert screen.objects_layout.count() == 1
    assert cached_person_widget.isHidden()


def test_connect_modal_results(qapp):
    dialog = ConnectPhoneDialog(diagnostic_msg="Test diagnostic")
    assert dialog.action_result == ConnectPhoneDialog.RESULT_CANCEL

    dialog._on_retry()
    assert dialog.action_result == ConnectPhoneDialog.RESULT_RETRY

    dialog._on_webcam()
    assert dialog.action_result == ConnectPhoneDialog.RESULT_USE_WEBCAM


def test_dashboard_window_lifecycle(qapp, monkeypatch):
    from ui.dashboard import DashboardWindow
    from unittest.mock import MagicMock

    # Mock hardware bridge to avoid real serial / video dependencies
    passed_args = {}
    monkeypatch.setattr("core.arduino_bridge.serial", None)
    monkeypatch.setattr(
        "core.adb_bridge.get_phone_status",
        lambda: {"state": "device", "serial": "DEVICE_SERIAL_999", "adb_available": True}
    )
    monkeypatch.setattr(
        "core.adb_bridge.setup_port_forward",
        lambda *args, **kwargs: passed_args.update({"fwd_serial": kwargs.get("serial")}) or True
    )
    monkeypatch.setattr(
        "core.adb_bridge.launch_android_app",
        lambda *args, **kwargs: passed_args.update({"launch_serial": kwargs.get("serial")}) or True
    )

    win = DashboardWindow(source=0)
    assert win.stack.currentIndex() == 0  # Starts on Screen 1

    # Click START -> should transition to Screen 2 and pass serial
    win.handle_start_clicked()
    assert win.stack.currentIndex() == 1  # Screen 2
    assert passed_args.get("fwd_serial") == "DEVICE_SERIAL_999"
    assert passed_args.get("launch_serial") == "DEVICE_SERIAL_999"

    # Click STOP -> should return to Screen 1
    win.handle_stop_clicked()
    assert win.stack.currentIndex() == 0  # Screen 1

    win.close()

