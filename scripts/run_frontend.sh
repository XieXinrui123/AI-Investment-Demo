#!/bin/bash
# Run the frontend service for local LaunchAgent deployment.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

cd "$FRONTEND_DIR"

NODE_BIN="${NODE_BIN:-$(command -v node || true)}"
if [ -z "$NODE_BIN" ] && [ -x "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node" ]; then
    NODE_BIN="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node"
fi

if [ -z "$NODE_BIN" ]; then
    echo "Node.js not found. Set NODE_BIN=/path/to/node."
    exit 1
fi

if [ ! -d "$FRONTEND_DIR/.next" ]; then
    "$NODE_BIN" ./node_modules/next/dist/bin/next build
fi

exec "$NODE_BIN" ./node_modules/next/dist/bin/next start -p 3000
