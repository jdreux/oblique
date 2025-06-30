#!/bin/bash
# Minimal install script for Oblique MVP
set -e

if [ ! -d "venv" ]; then
  echo "[DEBUG] Creating Python virtual environment in ./venv..."
  python3 -m venv venv
else
  echo "[DEBUG] venv already exists."
fi

source venv/bin/activate

if [ -f requirements.txt ]; then
  echo "[DEBUG] Installing Python dependencies from requirements.txt..."
  pip install --upgrade pip
  pip install -r requirements.txt
else
  echo "[DEBUG] No requirements.txt found, skipping pip install."
fi 