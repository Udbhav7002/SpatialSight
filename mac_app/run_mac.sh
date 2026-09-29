#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Auto-detect venv inside mac_app, or root venv if shared
if [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
elif [ -f "$SCRIPT_DIR/../venv/bin/activate" ]; then
    source "$SCRIPT_DIR/../venv/bin/activate"
else
    echo "[WARNING] No venv found! Running setup_mac.sh..."
    bash "$SCRIPT_DIR/setup_mac.sh"
    source "$SCRIPT_DIR/venv/bin/activate"
fi

echo "Starting SpatialSight Desktop Dashboard on Apple Silicon..."
python "$SCRIPT_DIR/main_gui.py" "$@"
