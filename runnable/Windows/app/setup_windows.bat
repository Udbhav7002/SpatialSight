@echo off
title SpatialSight - Windows Setup
echo ========================================================
echo        SpatialSight - Windows Environment Setup
echo ========================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from python.org
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [1/3] Creating Python Virtual Environment (venv)...
python -m venv venv
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/3] Activating Virtual Environment and Upgrading Pip...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

echo [3/3] Installing Dependencies (PyTorch, Ultralytics, PyQt6, OpenCV)...
pip install -r requirements_windows.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [SUCCESS] Windows setup complete!
echo To run the dashboard, double-click "run_windows.bat"
echo ========================================================
echo.
pause
