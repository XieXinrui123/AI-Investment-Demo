#!/bin/bash
# Run the backend service for local LaunchAgent deployment.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

cd "$BACKEND_DIR"

if [ -x "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON_BIN="$BACKEND_DIR/venv/bin/python"
else
    PYTHON_BIN="${PYTHON_BIN:-/usr/bin/python3}"
fi

exec "$PYTHON_BIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
