#!/bin/bash
# Minimal start script for Oblique MVP

if [ ! -d "venv" ]; then
  echo "[ERROR] venv not found. Please run ./install.sh first."
  exit 1
fi

source venv/bin/activate

echo "[DEBUG] Starting Oblique MVP with default settings..."
python3 main.py --width 800 --height 800 