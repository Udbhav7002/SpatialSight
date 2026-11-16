#!/bin/bash
# Upload sketch to Arduino Uno automatically

echo "========================================="
echo "   SpatialSight Arduino Upload Utility   "
echo "========================================="

# 1. Compile sketch
echo "[1/3] Compiling sketch..."
arduino-cli compile --fqbn arduino:avr:uno arduino/traffic_weather_controller

if [ $? -ne 0 ]; then
    echo "[ERROR] Compilation failed. Check Arduino code."
    exit 1
fi
echo "[OK] Compilation successful!"

# 2. Detect port
echo "[2/3] Looking for connected Arduino Uno..."
PORT=$(arduino-cli board list | grep -E "usbserial|usbmodem|wchusbserial" | awk '{print $1}' | head -n 1)

if [ -z "$PORT" ]; then
    # Try finding any USB serial port on macOS
    PORT=$(ls /dev/cu.usbserial* /dev/cu.usbmodem* /dev/cu.wchusbserial* 2>/dev/null | head -n 1)
fi

if [ -z "$PORT" ]; then
    echo ""
    echo "[WARNING] No Arduino detected!"
    echo "Please plug the blue USB cable into your Mac."
    echo "   Available ports right now:"
    ls /dev/cu.*
    echo ""
    echo "Once plugged in, run this script again: ./upload_arduino.sh"
    exit 1
fi

echo "[3/3] Found Arduino on port: $PORT"
echo "Uploading to Arduino Uno..."
arduino-cli upload -p "$PORT" --fqbn arduino:avr:uno arduino/traffic_weather_controller

if [ $? -eq 0 ]; then
    echo ""
    echo "SUCCESS! The code has been loaded onto your Arduino Uno!"
    echo "   The lights should flash Green -> Yellow -> Red on power-up."
else
    echo "[ERROR] Upload failed. Please make sure the cable is firmly connected."
fi
