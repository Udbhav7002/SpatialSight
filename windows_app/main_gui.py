import sys
import os
import argparse
from pathlib import Path

# Add windows_app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.dashboard import DashboardWindow

def main():
    parser = argparse.ArgumentParser(description="SpatialSight Object Detection Dashboard")
    parser.add_argument('--source', default='0', help='Camera source (e.g. 0, 1, or video file)')
    parser.add_argument('--model', default='yolov8n.pt', help='YOLO model weights path')
    args = parser.parse_args()
    
    app = QApplication(sys.argv)
    
    source = int(args.source) if args.source.isdigit() else args.source
    
    dashboard = DashboardWindow(source=source, model=args.model)
    dashboard.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
