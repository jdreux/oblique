#!/bin/bash

echo "🎵 Starting Oblique..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Run ./install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# If arguments are provided, pass them through
if [ "$#" -gt 0 ]; then
    python main.py "$@"
else
    # Try to find an audio file in project/demo/audio/
    AUDIO_FILE=$(find projects/demo/audio/ -type f \( -iname "*.wav" -o -iname "*.flac" -o -iname "*.mp3" -o -iname "*.ogg" -o -iname "*.aiff" \) | head -n 1)
    if [ -n "$AUDIO_FILE" ]; then
        echo "Using demo audio: $AUDIO_FILE"
        python main.py --audio "$AUDIO_FILE"
    else
        python main.py
    fi
fi 