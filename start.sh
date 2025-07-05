#!/bin/bash
# Minimal start script for Oblique MVP

if [ ! -d "venv" ]; then
  echo "[ERROR] venv not found. Please run ./install.sh first."
  exit 1
fi

source venv/bin/activate

# Default monitor (1 = Built-in Retina Display)
MONITOR=${MONITOR:-1}

echo "[DEBUG] Starting Oblique MVP with default settings..."
echo "[DEBUG] Using monitor: $MONITOR"
python3 main.py --audio "projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav" --width 800 --height 800 --debug --monitor "$MONITOR" "$@" 