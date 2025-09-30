#!/bin/bash
# Deprecated wrapper around the Python CLI.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_PYTHON=${PYTHON:-python3}
if ! command -v "$DEFAULT_PYTHON" >/dev/null 2>&1; then
  DEFAULT_PYTHON=python
fi

echo "[WARN] repl.sh is deprecated. Use 'python cli.py repl start' instead."
exec "$DEFAULT_PYTHON" "$SCRIPT_DIR/cli.py" repl start "$@"
