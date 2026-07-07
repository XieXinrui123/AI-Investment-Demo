#!/bin/bash
# Initialize this project for local personal use.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

if [ ! -f "$BACKEND_DIR/.env" ]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "Created backend/.env"
fi

if [ ! -f "$FRONTEND_DIR/.env.local" ]; then
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env.local"
    echo "Created frontend/.env.local"
fi

python_bin="${PYTHON_BIN:-}"
if [ -z "$python_bin" ]; then
    for candidate in "$BACKEND_DIR/venv/bin/python" /usr/bin/python3 python3; do
        if [ -x "$candidate" ] || command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c "import sqlalchemy, bcrypt" >/dev/null 2>&1; then
                python_bin="$candidate"
                break
            fi
        fi
    done
fi

if [ -z "$python_bin" ]; then
    echo "No Python with backend dependencies found."
    echo "Run ./start.sh start once to install/check dependencies, then run this script again."
    exit 1
fi

cd "$BACKEND_DIR"
"$python_bin" - <<'PY'
from app.models.database import Base, engine
from app.data.seed_data import seed_all

Base.metadata.create_all(bind=engine)
seed_all()
PY

echo "Local database is ready: backend/ai_berkshire.db"
echo "Run ./start.sh start and open http://localhost:3000"
