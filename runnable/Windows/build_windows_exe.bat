@echo off
REM Optional: build a single-file SpatialSight.exe with PyInstaller.
REM Run this ON a Windows PC after the first-run setup has completed.
cd /d "%~dp0app"
call venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --noconfirm --windowed --name SpatialSight ^
    --add-data "yolov8n.pt;." ^
    main_gui.py
echo.
echo Done! The exe is at: app\dist\SpatialSight.exe
pause
