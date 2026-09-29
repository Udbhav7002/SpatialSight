#!/usr/bin/env bash
set -e

echo "========================================================"
echo "        SpatialSight - macOS Apple Silicon Setup"
echo "========================================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check for Python 3.10-3.12 (preferred on Apple Silicon for PyTorch MPS)
PYTHON_BIN=""
if command -v python3.12 &>/dev/null; then
    PYTHON_BIN="python3.12"
elif command -v python3.11 &>/dev/null; then
    PYTHON_BIN="python3.11"
elif command -v python3.10 &>/dev/null; then
    PYTHON_BIN="python3.10"
elif command -v python3 &>/dev/null; then
    PYTHON_BIN="python3"
else
    echo "[ERROR] Python 3 not found! Install Python 3.12 via: brew install python@3.12"
    exit 1
fi

echo "[1/3] Using Python: $($PYTHON_BIN --version)"
echo "[2/3] Creating virtual environment (venv)..."
$PYTHON_BIN -m venv venv

echo "[3/3] Installing dependencies..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements_mac.txt

echo ""
echo "========================================================"
echo "[SUCCESS] macOS setup complete!"
echo "To run the dashboard: ./run_mac.sh"
echo "========================================================"
