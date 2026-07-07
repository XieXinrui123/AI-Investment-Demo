#!/bin/bash
# Manage macOS LaunchAgent services for the local personal workspace.

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPLOY_ROOT="${AI_BERKSHIRE_DEPLOY_ROOT:-$HOME/.ai-berkshire-web}"
LAUNCH_DIR="$HOME/Library/LaunchAgents"
LOG_DIR="$DEPLOY_ROOT/logs"
BACKEND_LABEL="com.xiexr.ai-berkshire.backend"
FRONTEND_LABEL="com.xiexr.ai-berkshire.frontend"
BACKEND_PLIST="$LAUNCH_DIR/$BACKEND_LABEL.plist"
FRONTEND_PLIST="$LAUNCH_DIR/$FRONTEND_LABEL.plist"
GUI_DOMAIN="gui/$(id -u)"

mkdir -p "$LAUNCH_DIR" "$LOG_DIR"

sync_deploy_root() {
    mkdir -p "$DEPLOY_ROOT"
    rsync -a --delete \
        --exclude ".git/" \
        --exclude "backend/venv/" \
        --exclude "backend/venv.*/" \
        --exclude "logs/" \
        --exclude "backups/" \
        "$PROJECT_ROOT/" "$DEPLOY_ROOT/"

    chmod +x "$DEPLOY_ROOT"/scripts/*.sh
}

write_plists() {
    cat > "$BACKEND_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$BACKEND_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DEPLOY_ROOT/scripts/run_backend.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$DEPLOY_ROOT/backend</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/backend.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/backend.launchd.err.log</string>
</dict>
</plist>
EOF

    cat > "$FRONTEND_PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$FRONTEND_LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$DEPLOY_ROOT/scripts/run_frontend.sh</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$DEPLOY_ROOT/frontend</string>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$LOG_DIR/frontend.launchd.log</string>
  <key>StandardErrorPath</key>
  <string>$LOG_DIR/frontend.launchd.err.log</string>
</dict>
</plist>
EOF
}

unload_one() {
    local label="$1"
    local plist="$2"
    launchctl bootout "$GUI_DOMAIN" "$plist" >/dev/null 2>&1 || true
    launchctl remove "$label" >/dev/null 2>&1 || true
}

load_one() {
    local plist="$1"
    launchctl bootstrap "$GUI_DOMAIN" "$plist" 2>/dev/null || launchctl load -w "$plist"
}

install_services() {
    chmod +x "$PROJECT_ROOT"/scripts/*.sh
    sync_deploy_root
    write_plists
    unload_one "$BACKEND_LABEL" "$BACKEND_PLIST"
    unload_one "$FRONTEND_LABEL" "$FRONTEND_PLIST"
    load_one "$BACKEND_PLIST"
    load_one "$FRONTEND_PLIST"
}

stop_services() {
    unload_one "$BACKEND_LABEL" "$BACKEND_PLIST"
    unload_one "$FRONTEND_LABEL" "$FRONTEND_PLIST"
}

status_services() {
    echo "=== LaunchAgent ==="
    launchctl print "$GUI_DOMAIN/$BACKEND_LABEL" >/dev/null 2>&1 && echo "backend: loaded" || echo "backend: not loaded"
    launchctl print "$GUI_DOMAIN/$FRONTEND_LABEL" >/dev/null 2>&1 && echo "frontend: loaded" || echo "frontend: not loaded"
    echo "=== Ports ==="
    "$PROJECT_ROOT/start.sh" status
    echo "=== Deploy Root ==="
    echo "$DEPLOY_ROOT"
}

case "${1:-status}" in
    install|start)
        install_services
        sleep 5
        status_services
        ;;
    stop)
        stop_services
        sleep 2
        status_services
        ;;
    sync)
        sync_deploy_root
        echo "Synced to $DEPLOY_ROOT"
        ;;
    restart)
        stop_services
        install_services
        sleep 5
        status_services
        ;;
    status)
        status_services
        ;;
    logs)
        tail -80 "$LOG_DIR"/*.log 2>/dev/null || true
        ;;
    *)
        echo "Usage: ./scripts/local_services.sh [install|start|stop|restart|status|logs|sync]"
        exit 1
        ;;
esac
