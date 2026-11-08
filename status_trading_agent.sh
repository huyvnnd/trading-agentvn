#!/usr/bin/env bash
# ==============================================================================
# Vietnam Stock Trading Agent - Status Monitor Script (V2.0.0 Packaging)
# Kiểm tra trạng thái hoạt động, HTTP Health Check, CPU, RAM và nhật ký.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CLI_BIN="$VENV_DIR/bin/trading-agent"

if [ -f "$CLI_BIN" ]; then
    exec "$CLI_BIN" status "$@"
else
    # Fallback thuần shell nếu không có CLI binary
    PID_FILE="$SCRIPT_DIR/trading_agent.pid"
    PORT="${PORT:-8502}"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 "$PID" 2>/dev/null; then
            echo "🟢 Trạng thái: ĐANG HOẠT ĐỘNG (PID: $PID)"
            echo "🌐 Dashboard: http://localhost:$PORT"
            ps -p "$PID" -o pid,%cpu,%mem,etime,cmd
            exit 0
        fi
    fi
    echo "🔴 Trạng thái: ĐÃ DỪNG (INACTIVE)"
fi
