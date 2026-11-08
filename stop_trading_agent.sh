#!/usr/bin/env bash
# ==============================================================================
# Vietnam Stock Trading Agent - Graceful Shutdown Script (V2.0.0 Packaging)
# Dừng an toàn tiến trình Trading Agent, giải phóng cổng mạng 8502.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CLI_BIN="$VENV_DIR/bin/trading-agent"

if [ -f "$CLI_BIN" ]; then
    exec "$CLI_BIN" stop "$@"
else
    # Fallback thuần shell nếu không có CLI binary
    PID_FILE="$SCRIPT_DIR/trading_agent.pid"
    PORT="${PORT:-8502}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null
            sleep 1
            kill -9 "$PID" 2>/dev/null
        fi
        rm -f "$PID_FILE"
    fi
    
    PORT_PIDS=$(lsof -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null)
    if [ -n "$PORT_PIDS" ]; then
        kill -9 $PORT_PIDS 2>/dev/null
    fi
    echo "✅ Đã dừng Trading Agent thành công!"
fi
