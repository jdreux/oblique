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

# Parse debug parameter
DEBUG_FLAG=""
if [ "$1" = "--debug" ]; then
  DEBUG_FLAG="--debug"
  shift  # Remove the debug parameter from arguments
fi

# Parse syntakt parameter
SYNTAKT_FLAG=""
AUDIO_DEVICE="0"
if [ "$1" = "--syntakt" ]; then
  SYNTAKT_FLAG="--syntakt"
  shift  # Remove the syntakt parameter from arguments
  
  echo "[INFO] Looking for Syntakt audio device..."
  
  # Create a temporary script to find syntakt device
  cat > /tmp/find_syntakt.py << 'EOF'
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    import sounddevice as sd
    
    # Get all devices
    devices = sd.query_devices()
    syntakt_device = None
    
    for i, device in enumerate(devices):
        device_name = device.get('name', '').lower()
        if 'syntakt' in device_name:
            syntakt_device = i
            print(f"FOUND:{i}:{device.get('name', 'Unknown')}")
            break
    
    if syntakt_device is None:
        print("NOT_FOUND")
        
except Exception as e:
    print(f"ERROR:{str(e)}")
EOF

  # Run the temporary script
  RESULT=$(python3 /tmp/find_syntakt.py 2>/dev/null)
  rm -f /tmp/find_syntakt.py
  
  if [[ "$RESULT" == FOUND:* ]]; then
    # Parse the result: FOUND:device_id:device_name
    IFS=':' read -r _ device_id device_name <<< "$RESULT"
    AUDIO_DEVICE="$device_id"
    echo "[INFO] Found Syntakt device: $device_name (ID: $device_id)"
  elif [[ "$RESULT" == "NOT_FOUND" ]]; then
    echo "[INFO] Syntakt device not found, using default device 0"
  else
    echo "[WARNING] Error finding audio devices: $RESULT"
    echo "[INFO] Using default device 0"
  fi
fi

# Default monitor (1 = Built-in Retina Display)
MONITOR=${MONITOR:-1}

echo "[DEBUG] Starting Oblique MVP with default settings..."
echo "[DEBUG] Using monitor: $MONITOR"
if [ -n "$DEBUG_FLAG" ]; then
  echo "[DEBUG] Debug mode enabled"
fi
if [ -n "$SYNTAKT_FLAG" ]; then
  echo "[DEBUG] Syntakt mode enabled, using audio device: $AUDIO_DEVICE"
fi
# python3 main.py --audio-file "projects/demo/audio/Just takes one try mix even shorter [master]19.06.2025.wav" --width 800 --height 800 $DEBUG_FLAG --monitor "$MONITOR" "$@" 
python3 main.py --width 800 --height 800 $DEBUG_FLAG --monitor "$MONITOR" "$@" --audio-device "$AUDIO_DEVICE" --debug