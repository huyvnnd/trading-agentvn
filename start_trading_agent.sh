#!/usr/bin/env bash
# ==============================================================================
# Vietnam Stock Trading Agent - Standalone Daemon Launcher (V2.0.0 Packaging)
# Tự động đồng bộ PID, giải quyết xung đột cổng, mở trình duyệt và thông báo GUI.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
CLI_BIN="$VENV_DIR/bin/trading-agent"
ICON_FILE="$SCRIPT_DIR/vnstock/assets/images/vnstock_rgb_logo_trans_sqr.png"

# Đảm bảo biến môi trường hiển thị đồ họa
export DISPLAY="${DISPLAY:-:0}"
if [ -z "$WAYLAND_DISPLAY" ] && [ -e "/run/user/$(id -u)/wayland-0" ]; then
    export WAYLAND_DISPLAY="wayland-0"
fi

if [ ! -f "$CLI_BIN" ]; then
    echo "❌ Lỗi: Không tìm thấy executable trading-agent tại $CLI_BIN!"
    echo "💡 Vui lòng kích hoạt venv và cài đặt: pip install -e ."
    exit 1
fi

# Gửi thông báo trên màn hình Desktop
if command -v notify-send >/dev/null 2>&1 && [ -n "$DISPLAY" ]; then
    notify-send -i "$ICON_FILE" "Trading Agent Vnstock" "Đang khởi chạy hệ thống & chuẩn bị mở dashboard..." 2>/dev/null || true
fi

# Chuyển tiếp tới CLI chuyên dụng
if [ "$1" == "restart" ]; then
    shift
    "$CLI_BIN" restart "$@"
elif [ "$1" == "status" ]; then
    shift
    "$CLI_BIN" status "$@"
elif [ "$1" == "stop" ]; then
    shift
    "$CLI_BIN" stop "$@"
else
    "$CLI_BIN" start "$@"
fi

# Đảm bảo mở trình duyệt trong phiên làm việc đồ họa
PORT="${PORT:-8502}"
URL="http://localhost:$PORT"

if [ -n "$DISPLAY" ]; then
    # Thử mở bằng xdg-open
    if command -v xdg-open >/dev/null 2>&1; then
        nohup xdg-open "$URL" >/dev/null 2>&1 &
    elif command -v firefox >/dev/null 2>&1; then
        nohup firefox "$URL" >/dev/null 2>&1 &
    fi
fi
