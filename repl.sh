#!/bin/bash
# REPL start script for Oblique
# Starts the interactive REPL with patch hot-reloading capabilities
# Creates a temporary patch file with scaffolding for VSCode integration

if [ ! -d "venv" ]; then
  echo "[ERROR] venv not found. Please run ./install.sh first."
  exit 1
fi

source venv/bin/activate

# Default values
PATCH_PATH=""
PATCH_FUNCTION=""
WIDTH="800"
HEIGHT="600"
FPS="60"
HOT_RELOAD_FLAG=""
LOG_LEVEL="INFO"
CREATE_TEMP_PATCH=true

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --patch-path)
      PATCH_PATH="$2"
      CREATE_TEMP_PATCH=false
      shift 2
      ;;
    --function)
      FUNCTION="$2"
      shift 2
      ;;
    --width)
      WIDTH="$2"
      shift 2
      ;;
    --height)
      HEIGHT="$2"
      shift 2
      ;;
    --fps)
      FPS="$2"
      shift 2
      ;;
    --hot-reload-shaders)
      HOT_RELOAD_FLAG="--hot-reload-shaders"
      shift
      ;;
    --log-level)
      LOG_LEVEL="$2"
      shift 2
      ;;
    --no-temp-patch)
      CREATE_TEMP_PATCH=false
      shift
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Start Oblique in REPL mode for interactive patch development"
      echo ""
      echo "Options:"
      echo "  --patch-path PATCH_PATH         Use existing patch module path (disables temp patch creation)"
      echo "  --patch-function PATCH_FUNCTION     Patch factory function name (required with --patch-path)"
      echo "  --width WIDTH           Window width (default: 800)"
      echo "  --height HEIGHT         Window height (default: 600)"
      echo "  --fps FPS               Target frame rate (default: 60)"
      echo "  --hot-reload-shaders    Enable shader hot-reloading"
      echo "  --log-level LEVEL       Logging level: FATAL, ERROR, WARNING, INFO, DEBUG, TRACE (default: INFO)"

      echo "  --no-temp-patch         Disable temporary patch creation (requires --module)"
      echo "  --help, -h              Show this help message"
      echo ""
      echo "Examples:"
      echo "  $0                                           # Create basic temp patch"
      echo "  $0 --patch-path projects.demo.shader_test        # Use existing patch"
      echo "  $0 --patch-function shader_test"
      echo "  $0 --hot-reload-shaders                      # Enable shader hot-reloading"

      echo ""
      echo "In the REPL:"
      echo "  - Edit your patch file and call reload_patch() or r() to apply changes"
      echo "  - The running engine is available as 'engine'"
      echo "  - Use Ctrl+C or exit() to quit"
      exit 0
      ;;
    *)
      echo "[ERROR] Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Create temporary patch if needed
if [ "$CREATE_TEMP_PATCH" = true ]; then
  TEMP_DIR="/tmp/oblique_repl_$$"
  mkdir -p "$TEMP_DIR"
  TEMP_PATCH_FILE="$TEMP_DIR/temp_patch.py"
  
  echo "[INFO] Creating temporary patch with basic template"
  
  # Copy the default template
  if [ -f "core/default_repl_template.py" ]; then
    cp "core/default_repl_template.py" "$TEMP_PATCH_FILE"
  else
    echo "[ERROR] Template file core/default_repl_template.py not found"
    exit 1
  fi
  
  PATCH_PATH="temp_patch"
  PATCH_FUNCTION="temp_patch"
  
  # Add the temp directory to Python path
  export PYTHONPATH="$TEMP_DIR:$PYTHONPATH"
  
  echo "[INFO] Temporary patch created at: $TEMP_PATCH_FILE"
  echo "[INFO] Open this file in your editor of choice to start editing"
else
  # Validate required parameters for existing module
  if [ -z "$PATCH_PATH" ] || [ -z "$PATCH_FUNCTION" ]; then
    echo "[ERROR] --patch-path and --patch-function are required when --no-temp-patch is used"
    exit 1
  fi
fi

echo "[INFO] Starting Oblique REPL..."
echo "[INFO] Patch Path: $PATCH_PATH"
echo "[INFO] Patch Function: $PATCH_FUNCTION"
echo "[INFO] Resolution: ${WIDTH}x${HEIGHT}"
echo "[INFO] FPS: $FPS"
echo "[INFO] Log Level: $LOG_LEVEL"
if [ -n "$HOT_RELOAD_FLAG" ]; then
  echo "[INFO] Shader hot-reload enabled"
fi
echo ""

python3 repl.py "$PATCH_PATH" "$PATCH_FUNCTION" \
  --width "$WIDTH" \
  --height "$HEIGHT" \
  --fps "$FPS" \
  --log-level "$LOG_LEVEL" \
  $HOT_RELOAD_FLAG 