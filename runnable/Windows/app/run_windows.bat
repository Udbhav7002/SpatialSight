@echo off
title SpatialSight - Windows Dashboard
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo [WARNING] Virtual environment not found! Running setup first...
    call setup_windows.bat
)

call venv\Scripts\activate.bat

echo Starting SpatialSight Desktop Dashboard...
python main_gui.py --source 0 --model yolov8n.pt

if %errorlevel% neq 0 (
    echo.
    echo Application exited with error code %errorlevel%.
    pause
)
