#!/bin/bash
# Minimal start script for Oblique MVP

if [ ! -d "venv" ]; then
  echo "[ERROR] venv not found. Please run ./install.sh first."
  exit 1
fi

source venv/bin/activate

# Check if listing audio devices was requested
if [ "$1" = "--list-audio-devices" ]; then
  echo "[INFO] Listing available audio input devices..."
  python3 main.py --list-audio-devices
  exit 0
fi

# Default monitor (1 = Built-in Retina Display)
MONITOR=${MONITOR:-1}

echo "[DEBUG] Starting Oblique MVP with default settings..."
echo "[DEBUG] Using monitor: $MONITOR"
# python3 main.py --audio "projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav" --width 800 --height 800 --debug --monitor "$MONITOR" "$@" 
python3 main.py --width 800 --height 800 --debug --monitor "$MONITOR" "$@" --audio-device 2 --audio-channels 0