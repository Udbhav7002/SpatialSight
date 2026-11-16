@echo off
title SpatialSight Launcher
cd /d "%~dp0app"

echo ========================================
echo    SpatialSight - Windows Launcher
echo ========================================
echo.

REM --- Check Python ---
python --version >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python was not found on this PC.
    echo.
    echo Install Python 3.10 - 3.12 from https://www.python.org/downloads/
    echo IMPORTANT: tick "Add Python to PATH" during installation.
    echo Then double-click this file again.
    echo.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo [OK] Python %PYVER% found.

REM --- First run: create virtual environment and install dependencies ---
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [SETUP] First run detected - setting up the environment.
    echo         Downloading PyTorch, OpenCV, PyQt6... (5-15 minutes, one time only)
    echo.
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements_windows.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Dependency installation failed. Check your internet connection.
        pause
        exit /b 1
    )
    echo.
    echo [OK] Setup complete! Starting SpatialSight...
) else (
    call venv\Scripts\activate.bat
)

REM --- Launch the dashboard ---
echo [RUN] Starting SpatialSight Desktop Dashboard...
python main_gui.py --source 0 --model yolov8n.pt
if errorlevel 1 (
    echo.
    echo [ERROR] The app exited with an error. See messages above.
    echo         Tip: run setup_windows.bat or check that a webcam is available.
    pause
)
