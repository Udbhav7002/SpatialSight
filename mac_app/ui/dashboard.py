import sys
import argparse
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QComboBox, QSlider, QLabel, QMenuBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction

from core.frame_buffer import FrameBuffer
from core.inference_engine import InferenceEngine
from core.collision_zone import CollisionZone
from core import adb_bridge

from ui.live_detection_tab import LiveDetectionTab
from ui.room_map_tab import RoomMapTab

logging.basicConfig(level=logging.INFO)

DARK_STYLESHEET = """
QMainWindow {
    background-color: #2b2b2b;
    color: #ffffff;
}
QWidget {
    background-color: #2b2b2b;
    color: #ffffff;
}
QToolBar {
    background-color: #333333;
    border: none;
}
QStatusBar {
    background-color: #333333;
    color: #aaaaaa;
}
QGroupBox {
    border: 1px solid #555555;
    border-radius: 5px;
    margin-top: 10px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px 0 3px;
}
QTableWidget {
    background-color: #1e1e1e;
    color: #ffffff;
    gridline-color: #555555;
}
QHeaderView::section {
    background-color: #333333;
    color: #ffffff;
    padding: 4px;
    border: 1px solid #555555;
}
QPushButton {
    background-color: #444444;
    color: #ffffff;
    border: 1px solid #555555;
    padding: 5px;
    border-radius: 3px;
}
QPushButton:hover {
    background-color: #555555;
}
QPushButton:pressed {
    background-color: #666666;
}
QSlider::groove:horizontal {
    border: 1px solid #999999;
    height: 8px;
    background: #333333;
    margin: 2px 0;
}
QSlider::handle:horizontal {
    background: #4CAF50;
    border: 1px solid #5c5c5c;
    width: 18px;
    margin: -2px 0;
    border-radius: 3px;
}
"""

class DashboardWindow(QMainWindow):
    def __init__(self, source, model):
        super().__init__()
        self.setWindowTitle("SpatialSight — Object Detection Dashboard")
        self.resize(1400, 900)
        self.setStyleSheet(DARK_STYLESHEET)
        
        self.source = source
        self.model = model
        
        # Core components
        self.engine = InferenceEngine()
        self.buffer = FrameBuffer(source=self.source)
        self.collision_zone = CollisionZone()
        
        self.setup_ui()
        self.setup_actions()
        
        # Load initial model
        self.engine.load_model(self.model)
        
        # Start frame buffer
        self.buffer.start()
        
        # Main loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.main_loop)
        self.timer.start(30) # ~33fps
        
        self.check_adb()

    def setup_ui(self):
        # Tabs
        self.tabs = QTabWidget()
        self.live_tab = LiveDetectionTab(self.engine)
        self.room_tab = RoomMapTab(self.engine)
        
        self.tabs.addTab(self.live_tab, "Live Detection")
        self.tabs.addTab(self.room_tab, "Room Map")
        self.setCentralWidget(self.tabs)
        
        # Toolbar
        toolbar = QToolBar("Main Toolbar")
        self.addToolBar(toolbar)
        
        self.conn_label = QLabel("🔴 Disconnected")
        self.conn_label.setStyleSheet("padding: 0 10px;")
        toolbar.addWidget(self.conn_label)
        
        toolbar.addWidget(QLabel(" Model: "))
        self.model_combo = QComboBox()
        models = self.engine.list_available_models()
        if not models:
            self.model_combo.addItem(self.model)
        else:
            self.model_combo.addItems([m.split('/')[-1] for m in models])
            # Select the arg model if present
            for i in range(self.model_combo.count()):
                if self.model in self.model_combo.itemText(i):
                    self.model_combo.setCurrentIndex(i)
                    break
                    
        self.model_combo.currentTextChanged.connect(self.on_model_changed)
        toolbar.addWidget(self.model_combo)
        
        toolbar.addWidget(QLabel(" Conf: "))
        self.conf_slider = QSlider(Qt.Orientation.Horizontal)
        self.conf_slider.setRange(5, 95)
        self.conf_slider.setValue(int(self.engine.DEFAULT_CONFIDENCE * 100))
        self.conf_slider.setFixedWidth(100)
        self.conf_slider.valueChanged.connect(self.on_conf_changed)
        toolbar.addWidget(self.conf_slider)
        
        self.conf_label = QLabel(f" {self.conf_slider.value()}% ")
        toolbar.addWidget(self.conf_label)
        
        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(spacer.sizePolicy().Policy.Expanding, spacer.sizePolicy().Policy.Preferred)
        toolbar.addWidget(spacer)
        
        self.fps_label = QLabel("FPS: 0.0")
        self.fps_label.setStyleSheet("padding: 0 10px; color: #4CAF50; font-weight: bold;")
        toolbar.addWidget(self.fps_label)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(f"Device: {self.engine.device}")
        
    def setup_actions(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        view_menu = menubar.addMenu("View")
        fullscreen_action = QAction("Toggle Fullscreen", self)
        fullscreen_action.triggered.connect(self.toggle_fullscreen)
        view_menu.addAction(fullscreen_action)
        
        help_menu = menubar.addMenu("Help")
        about_action = QAction("About", self)
        help_menu.addAction(about_action)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def check_adb(self):
        if adb_bridge.is_phone_connected():
            self.conn_label.setText("🟢 Phone Connected")
        else:
            self.conn_label.setText("🔴 Disconnected (Using WebCam/Video)")
            
    def on_model_changed(self, model_name):
        # find full path if needed, we'll just assume models/ dir or root
        self.engine.load_model(model_name)
        
    def on_conf_changed(self, value):
        self.conf_label.setText(f" {value}% ")
        self.engine.set_confidence(value / 100.0)

    def main_loop(self):
        frame = self.buffer.read()
        if frame is None:
            return
            
        self.fps_label.setText(f"FPS: {self.buffer.fps:.1f}")
        
        current_tab_index = self.tabs.currentIndex()
        
        if current_tab_index == 0:
            # Live Detection
            result = self.engine.infer(frame)
            self.live_tab.update_display(frame, result, self.collision_zone)
        else:
            # Room Map
            # Check if adb is connected to fetch real sensor data, otherwise use fake
            # For simplicity, if not fetching from adb, use fake
            sensor_data = self.room_tab.generate_fake_sensor_data()
            self.room_tab.update_display(frame, sensor_data)
            
    def closeEvent(self, event):
        self.buffer.stop()
        super().closeEvent(event)

def main():
    parser = argparse.ArgumentParser(description="SpatialSight Dashboard")
    parser.add_argument("--source", type=str, default="0", help="Video source (0 for webcam, or URL)")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Path to model weights")
    args, unknown = parser.parse_known_args()
    
    source = int(args.source) if args.source.isdigit() else args.source
    
    app = QApplication(sys.argv)
    window = DashboardWindow(source=source, model=args.model)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
