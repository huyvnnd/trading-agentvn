"""
Command Line Interface (CLI) for Vietnam Quantitative Multi-Agent Hedge Fund & Trading Platform.
Tích hợp điều khiển tiến trình daemon, kiểm toán trạng thái, quét cổ phiếu và họp Hội đồng CIO trực tiếp từ Terminal.
"""

import os
import sys
import time
import socket
import argparse
import subprocess
import urllib.request
import urllib.error

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PID_FILE = os.path.join(PROJECT_ROOT, "trading_agent.pid")
LOG_FILE = os.path.join(PROJECT_ROOT, "trading_agent.log")
DEFAULT_PORT = 8502


def _get_python_executable():
    venv_py = os.path.join(PROJECT_ROOT, "venv", "bin", "python3")
    if os.path.exists(venv_py):
        return venv_py
    return sys.executable


def _get_streamlit_executable():
    venv_st = os.path.join(PROJECT_ROOT, "venv", "bin", "streamlit")
    if os.path.exists(venv_st):
        return venv_st
    return "streamlit"


def check_health(port=DEFAULT_PORT):
    """Kiểm tra phản hồi HTTP health check từ Streamlit server."""
    url = f"http://localhost:{port}/_stcore/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "TradingAgentCLI"})
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_process_on_port(port=DEFAULT_PORT):
    """Tìm PID của tiến trình server đang lắng nghe tại cổng port (chỉ lọc trạng thái LISTEN)."""
    try:
        out = subprocess.check_output(["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"], stderr=subprocess.DEVNULL)
        pids = [int(p) for p in out.decode().strip().split() if p.isdigit()]
        return pids[0] if pids else None
    except Exception:
        # Dự phòng bằng fuser hoặc lsof thông thường
        try:
            out = subprocess.check_output(["lsof", "-t", "-i", f":{port}"], stderr=subprocess.DEVNULL)
            pids = [int(p) for p in out.decode().strip().split() if p.isdigit()]
            return pids[-1] if pids else None
        except Exception:
            return None


def get_lan_ip():
    """Lấy địa chỉ IP mạng nội bộ (LAN IP) khả dụng nhất của máy chủ để truy cập từ điện thoại/máy tính khác."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def cmd_status(args):
    port = args.port or DEFAULT_PORT
    print("=" * 60)
    print("      TRẠNG THÁI HỆ THỐNG TRADING AGENT VNSTOCK")
    print("=" * 60)

    port_pid = get_process_on_port(port)
    is_healthy = check_health(port)

    pid_from_file = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid_from_file = int(f.read().strip())
        except Exception:
            pid_from_file = None

    active_pid = port_pid or pid_from_file

    if active_pid and is_healthy:
        lan_ip = get_lan_ip()
        print(f"🟢 Trạng thái: ĐANG HOẠT ĐỘNG ỔN ĐỊNH (ACTIVE - HEALTHY)")
        print(f"🆔 Tiến trình PID: {active_pid} (Cổng mạng: {port})")
        print(f"💻 Truy cập cục bộ (Máy tính này): http://localhost:{port}")
        print(f"📱 Truy cập từ ĐIỆN THOẠI / MÁY TÍNH KHÁC: http://{lan_ip}:{port}")
        print(f"🩺 HTTP Health Check: 200 OK (/_stcore/health)")

        # Đồng bộ PID file nếu bị lệch
        if pid_from_file != active_pid:
            try:
                with open(PID_FILE, "w") as f:
                    f.write(str(active_pid))
            except Exception:
                pass

        try:
            import psutil
            p = psutil.Process(active_pid)
            mem_mb = p.memory_info().rss / (1024 * 1024)
            cpu = p.cpu_percent(interval=0.1)
            uptime_s = time.time() - p.create_time()
            uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime_s))
            print(f"📊 Mức chiếm dụng tài nguyên: CPU {cpu:.1f}% | RAM {mem_mb:.1f} MB | Thời gian chạy: {uptime_str}")
        except Exception:
            pass

    elif active_pid and not is_healthy:
        print(f"🟡 Trạng thái: TIẾN TRÌNH ĐANG CHẠY NHƯNG CHƯA SẴN SÀNG (STARTING / UNHEALTHY)")
        print(f"🆔 Tiến trình PID: {active_pid} (Cổng mạng: {port})")
        print(f"⚠️ Health check chưa phản hồi. Vui lòng kiểm tra log tại: {LOG_FILE}")
    else:
        print(f"🔴 Trạng thái: ĐÃ DỪNG HOÀN TOÀN (INACTIVE)")
        print(f"👉 Khởi động hệ thống bằng lệnh: trading-agent start")

    print("-" * 60)
    if os.path.exists(LOG_FILE):
        print(f"📝 5 dòng nhật ký mới nhất ({LOG_FILE}):")
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                for line in lines[-5:]:
                    print("  " + line.rstrip())
        except Exception:
            pass
    print("=" * 60)


def cmd_stop(args):
    port = args.port or DEFAULT_PORT
    print("=" * 60)
    print("          DỪNG HỆ THỐNG TRADING AGENT")
    print("=" * 60)

    stopped = False
    port_pid = get_process_on_port(port)

    pid_from_file = None
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid_from_file = int(f.read().strip())
        except Exception:
            pid_from_file = None

    pids_to_kill = set()
    if port_pid:
        pids_to_kill.add(port_pid)
    if pid_from_file:
        pids_to_kill.add(pid_from_file)

    for pid in pids_to_kill:
        print(f"🛑 Đang gửi tín hiệu dừng tới tiến trình PID {pid}...")
        try:
            os.kill(pid, 15)  # SIGTERM
            for _ in range(5):
                time.sleep(0.5)
                try:
                    os.kill(pid, 0)
                except OSError:
                    stopped = True
                    break
            else:
                print(f"⚠️ Buộc dừng tiến trình PID {pid} (SIGKILL)...")
                os.kill(pid, 9)
                stopped = True
        except OSError:
            stopped = True

    if os.path.exists(PID_FILE):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass

    if stopped or check_health(port) is False:
        print("✅ Đã dừng Trading Agent thành công và giải phóng cổng mạng!")
    else:
        print("ℹ️ Trading Agent hiện không chạy.")


def open_dashboard_browser(port: int = DEFAULT_PORT):
    """Mở trình duyệt Web hiển thị Dashboard với cơ chế đa dự phòng (notify-send, xdg-open, firefox, webbrowser)."""
    url = f"http://localhost:{port}"
    env = os.environ.copy()
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"
    if "WAYLAND_DISPLAY" not in env and os.path.exists(f"/run/user/{os.getuid()}/wayland-0"):
        env["WAYLAND_DISPLAY"] = "wayland-0"

    icon_path = os.path.join(PROJECT_ROOT, "vnstock", "assets", "images", "vnstock_rgb_logo_trans_sqr.png")
    try:
        subprocess.Popen(
            ["notify-send", "-i", icon_path, "Trading Agent Vnstock", f"Đang mở dashboard tại {url}"],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass

    # 1. Thử xdg-open
    opened = False
    try:
        subprocess.Popen(["xdg-open", url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        opened = True
    except Exception:
        pass

    # 2. Thử firefox trực tiếp nếu xdg-open không khả dụng
    if not opened:
        try:
            subprocess.Popen(["firefox", url], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            opened = True
        except Exception:
            pass

    # 3. Python webbrowser fallback
    if not opened:
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            pass


def cmd_start(args):
    port = args.port or DEFAULT_PORT
    no_browser = getattr(args, "no_browser", False)
    print("=" * 60)
    print("   HỆ THỐNG TRADING AGENT CHỨNG KHOÁN VIỆT NAM (VNSTOCK)")
    print("=" * 60)

    # 1. Kiểm tra xem port đã có tiến trình chạy chưa
    port_pid = get_process_on_port(port)
    if port_pid and check_health(port):
        lan_ip = get_lan_ip()
        print(f"ℹ️ Trading Agent ĐANG CHẠY với PID: {port_pid}")
        print(f"💻 Truy cập cục bộ (Máy tính này): http://localhost:{port}")
        print(f"📱 Truy cập từ ĐIỆN THOẠI & MÁY TÍNH KHÁC (Cùng Wi-Fi/LAN): http://{lan_ip}:{port}")
        # Cập nhật PID file
        with open(PID_FILE, "w") as f:
            f.write(str(port_pid))
        if not no_browser:
            print("🌐 Đang kích hoạt mở trình duyệt Web Dashboard...")
            open_dashboard_browser(port)
        return

    # Nếu port bị kẹt bởi tiến trình chết hoặc stale, dọn dẹp trước
    if port_pid:
        print(f"🧹 Dọn dẹp tiến trình cũ chiếm dụng cổng {port} (PID: {port_pid})...")
        try:
            os.kill(port_pid, 9)
            time.sleep(1)
        except Exception:
            pass

    st_exec = _get_streamlit_executable()
    app_path = os.path.join(PROJECT_ROOT, "trading_agent", "app.py")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{PROJECT_ROOT}:{os.path.join(PROJECT_ROOT, 'vnstock')}:{env.get('PYTHONPATH', '')}"

    st_cmd_args = [
        st_exec,
        "run",
        app_path,
        "--server.port",
        str(port),
        "--server.address",
        "0.0.0.0",
        "--server.headless",
        "true",
        "--server.enableCORS",
        "false",
        "--server.enableXsrfProtection",
        "false",
        "--browser.gatherUsageStats",
        "false",
    ]

    if getattr(args, "foreground", False):
        print("🚀 Khởi chạy ở chế độ trực tiếp (Foreground Mode)...")
        os.chdir(PROJECT_ROOT)
        os.execve(st_exec, st_cmd_args, env)
    else:
        print("🚀 Khởi chạy độc lập dưới nền (Daemon Mode)...")
        print(f"📁 Thư mục làm việc: {PROJECT_ROOT}")
        print(f"📝 Tệp nhật ký log: {LOG_FILE}")
        print(f"🌐 Cổng dịch vụ: {port}")

        log_fd = open(LOG_FILE, "a", encoding="utf-8")
        proc = subprocess.Popen(
            st_cmd_args,
            cwd=PROJECT_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_fd,
            stderr=log_fd,
            start_new_session=True,
        )

        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))

        # Đợi tối đa 6 giây để health check xác nhận
        print("⏳ Đang kiểm tra trạng thái khởi động...")
        for _ in range(12):
            time.sleep(0.5)
            if check_health(port):
                break

        if check_health(port):
            actual_pid = get_process_on_port(port) or proc.pid
            lan_ip = get_lan_ip()
            with open(PID_FILE, "w") as f:
                f.write(str(actual_pid))
            print(f"✅ Khởi động thành công! Tiến trình PID: {actual_pid}")
            print(f"💻 Truy cập cục bộ (Máy tính này): http://localhost:{port}")
            print(f"📱 Truy cập từ ĐIỆN THOẠI & MÁY TÍNH KHÁC (Cùng Wi-Fi/LAN): http://{lan_ip}:{port}")
            print("💡 Hệ thống chạy độc lập 24/7, không bị ảnh hưởng khi tắt Terminal.")
            print("👉 Dùng 'trading-agent status' để kiểm tra, 'trading-agent stop' để dừng.")
            if not no_browser:
                print("🌐 Đang kích hoạt mở trình duyệt Web Dashboard...")
                open_dashboard_browser(port)
        else:
            print(f"⚠️ Ứng dụng đã khởi chạy (PID: {proc.pid}) nhưng health check chưa hoàn tất. Vui lòng kiểm tra log: {LOG_FILE}")


def cmd_restart(args):
    print("🔄 Đang khởi động lại hệ thống Trading Agent...")
    cmd_stop(args)
    time.sleep(1.5)
    cmd_start(args)


def cmd_scan(args):
    criteria = args.criteria or "vsa_smc"
    print(f"🔍 Đang quét thị trường theo tiêu chí: {criteria.upper()}...")
    from trading_agent.data_engine import DataEngine
    from trading_agent.vsa_smc_screener import VSASMCScreener
    from trading_agent.screener import StockScreener

    de = DataEngine()
    if criteria in ["vsa_smc", "three_tier"]:
        vsa = VSASMCScreener(de)
        df_buy, df_wl, df_av = vsa.scan_three_tier_universe()
        print("\n" + "=" * 80)
        print("💎 NHÓM 1: TOP CỔ PHIẾU CHUẨN ĐIỂM MUA TỔ CHỨC (STAGE 2 & SEPA >= 5/8)")
        print("=" * 80)
        if not df_buy.empty:
            cols = [c for c in ["Mã CP", "Giá (VNĐ)", "Điểm Smart Money", "Giai Đoạn", "RS Rating", "SEPA", "Giá Vốn POC"] if c in df_buy.columns]
            print(df_buy[cols].to_string(index=False))
        else:
            print("🛡️ 0 mã đạt chuẩn giải ngân Stage 2 hôm nay. Khuyến nghị nắm giữ 100% tiền mặt phòng thủ.")

        print("\n" + "=" * 80)
        print("🟡 NHÓM 2: DANH MỤC TÍCH LŨY THEO DÕI QUAN SÁT (STAGE 1 TÍCH LŨY / CHỜ BỨT PHÁ PIVOT)")
        print("=" * 80)
        if not df_wl.empty:
            cols = [c for c in ["Mã CP", "Giá (VNĐ)", "Điểm Smart Money", "Giai Đoạn", "RS Rating", "SEPA", "Trạng Thái Theo Dõi"] if c in df_wl.columns]
            print(df_wl[cols].head(10).to_string(index=False))

        print("\n" + "=" * 80)
        print("⛔ NHÓM 3: CỔ PHIẾU DOWNTREND GIAI ĐOẠN 4 (CẤM BẮT ĐÁY)")
        print("=" * 80)
        if not df_av.empty:
            cols = [c for c in ["Mã CP", "Giá (VNĐ)", "Giai Đoạn", "RS Rating", "SEPA", "Lý Do Cấm Mua"] if c in df_av.columns]
            print(df_av[cols].head(8).to_string(index=False))
    else:
        sc = StockScreener(de)
        df = sc.scan_symbols(criteria=criteria)
        print(f"\nKết quả sàng lọc ({len(df)} mã):")
        if not df.empty:
            cols = [c for c in ["Mã CP", "Giá (VNĐ)", "Điểm Kỹ Thuật", "RS Rating", "SEPA", "Khuyến Nghị"] if c in df.columns]
            print(df[cols].head(12).to_string(index=False))


def cmd_analyze(args):
    symbol = args.symbol.strip().upper()
    print(f"🏛️ Đang triệu tập phiên họp Hội đồng Thẩm định CIO cho mã: {symbol}...")
    from trading_agent.cio_agent import CIOAgent
    cio = CIOAgent()
    res = cio.evaluate_and_decide(symbol)
    print("\n" + "=" * 80)
    print(f"🏛️ NGHỊ QUYẾT HỘI ĐỒNG ĐẦU TƯ CIO — MÃ {symbol}")
    print("=" * 80)
    print(f"Phán quyết chính thức : {res['final_decision']}")
    print(f"Điểm thuyết phục     : {res['conviction_score']}/10")
    print(f"Tỷ trọng phân bổ     : {res['allocation_pct']}% NAV")
    print(f"\nKế hoạch hành động   :\n{res['action_plan']}")
    print("=" * 80)


def cmd_verify(args):
    verify_script = os.path.join(PROJECT_ROOT, "verify_system.py")
    if os.path.exists(verify_script):
        subprocess.call([_get_python_executable(), verify_script])
    else:
        print(f"File kiểm thử {verify_script} chưa tồn tại.")


def main():
    parser = argparse.ArgumentParser(
        prog="trading-agent",
        description="Vietnam Quantitative Multi-Agent Hedge Fund & Trading Platform CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Lệnh thực thi")

    # Start
    p_start = subparsers.add_parser("start", help="Khởi động hệ thống Trading Agent (Daemon hoặc Foreground)")
    p_start.add_argument("--port", type=int, default=DEFAULT_PORT, help="Cổng dịch vụ (Mặc định: 8502)")
    p_start.add_argument("--foreground", "-f", action="store_true", help="Chạy trực tiếp trên terminal (không daemon)")
    p_start.add_argument("--no-browser", action="store_true", help="Không tự động mở trình duyệt sau khi khởi động")

    # Stop
    p_stop = subparsers.add_parser("stop", help="Dừng hệ thống Trading Agent và giải phóng cổng mạng")
    p_stop.add_argument("--port", type=int, default=DEFAULT_PORT, help="Cổng dịch vụ (Mặc định: 8502)")

    # Restart
    p_restart = subparsers.add_parser("restart", help="Khởi động lại hệ thống Trading Agent")
    p_restart.add_argument("--port", type=int, default=DEFAULT_PORT, help="Cổng dịch vụ (Mặc định: 8502)")
    p_restart.add_argument("--no-browser", action="store_true", help="Không tự động mở trình duyệt sau khi khởi động lại")

    # Status
    p_status = subparsers.add_parser("status", help="Kiểm tra trạng thái tiến trình, tài nguyên và HTTP health check")
    p_status.add_argument("--port", type=int, default=DEFAULT_PORT, help="Cổng dịch vụ (Mặc định: 8502)")

    # Scan
    p_scan = subparsers.add_parser("scan", help="Quét thị trường theo bộ lọc định lượng")
    p_scan.add_argument("criteria", nargs="?", default="vsa_smc", help="Tiêu chí quét: vsa_smc, bottom_fishing, sepa_vcp, avoid_stage4")

    # Analyze
    p_analyze = subparsers.add_parser("analyze", help="Triệu tập Hội đồng Đầu tư CIO thẩm định 1 mã cụ thể")
    p_analyze.add_argument("symbol", help="Mã cổ phiếu cần thẩm định (VD: VIC, NKG, VPB, TCM)")

    # Verify
    subparsers.add_parser("verify", help="Chạy bộ kiểm thử tự chẩn đoán toàn diện hệ thống")

    args = parser.parse_args()
    if args.command == "start":
        cmd_start(args)
    elif args.command == "stop":
        cmd_stop(args)
    elif args.command == "restart":
        cmd_restart(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "verify":
        cmd_verify(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
