# Implementation Plan: 001 - Comprehensive Packaging, Optimization & System Upgrade for Trading Agent Vnstock

**Branch**: `001-trading-agent-packaging-upgrade` | **Date**: 2026-11-06 | **Spec**: [spec.md](./spec.md)  
**Input**: Feature specification from `specs/001-trading-agent-packaging-upgrade/spec.md`

---

## 1. Summary

Nâng cấp toàn diện cơ chế đóng gói, kiến trúc điều khiển tiến trình và bộ kiểm thử tự chẩn đoán cho nền tảng **Trading Agent Vnstock**:
1. Chuẩn hóa bộ tệp đóng gói Python: `pyproject.toml`, `setup.py`, `requirements.txt`, và CLI module `trading_agent/cli.py`.
2. Nâng cấp toàn diện bộ shell scripts: `start_trading_agent.sh`, `stop_trading_agent.sh`, `status_trading_agent.sh` với cơ chế đồng bộ PID thông minh, kiểm tra health check HTTP 200, và hỗ trợ lệnh `restart`.
3. Tạo launcher 1-click `TradingAgentVnstock.desktop` trên màn hình Desktop của người dùng.
4. Xây dựng bộ công cụ kiểm thử tự chẩn đoán `verify_system.py` kiểm định toàn diện từ dữ liệu, thuật toán định lượng, cơ chế phản biện 3 nhóm đến tiến trình nền.

---

## 2. Technical Context

- **Ngôn ngữ & Phiên bản**: Python 3.13 (trong môi trường virtualenv `/home/osboxes/Desktop/trading/venv`).
- **Thư viện chính**: `streamlit`, `pandas`, `numpy`, `plotly`, `requests`, `vnstock` (local editable).
- **Giao thức tiến trình**: Linux daemon qua `setsid`, I/O redirection sang `trading_agent.log`, PID tracking qua `trading_agent.pid`, HTTP health probe tại `/_stcore/health`.
- **Cổng dịch vụ mặc định**: `8502`.
- **Mục tiêu hiệu năng**: Khởi động daemon < 3 giây, kiểm tra status < 0.2 giây, `verify_system.py` chạy toàn bộ kiểm thử < 8 giây.

---

## 3. Constitution Check (Tuân Thủ Hiến Pháp Dự Án)

- ✅ **The Power Inversion**: Toàn bộ các thay đổi được định nghĩa trong `spec.md` và `plan.md` trước khi triển khai code.
- ✅ **Capital Preservation & Zero Contradiction**: Duy trì 100% cơ chế 3 nhóm (Stage 2 Buys vs Stage 1 Watchlist vs Stage 4 Avoid) không hạ chuẩn ép mua.
- ✅ **Deterministic Verification**: Mọi hành vi nâng cấp phải có bài test kiểm chứng có thể tái lập trước và sau khi triển khai.

---

## 4. Architecture & File Structure

```text
/home/osboxes/Desktop/trading/
├── pyproject.toml                         # [MỚI] Khai báo packaging chuẩn PEP 517/621
├── setup.py                               # [MỚI] Hỗ trợ pip install -e .
├── requirements.txt                       # [MỚI] Danh mục dependencies chuẩn hóa
├── verify_system.py                       # [MỚI] Script tự chẩn đoán toàn diện hệ thống
├── start_trading_agent.sh                 # [NÂNG CẤP] Tự dọn dẹp port, check health, hỗ trợ restart
├── stop_trading_agent.sh                  # [NÂNG CẤP] Graceful shutdown + dọn sạch stale PIDs
├── status_trading_agent.sh                # [NÂNG CẤP] Nhận diện PID thực từ port, check HTTP health
├── trading_agent/
│   ├── cli.py                             # [MỚI] Command Line Interface đa năng
│   ├── app.py                             # [DUY TRÌ & TỐI ƯU] UI Dashboard 12 Tabs
│   └── ...                                # Các Agents và Engines định lượng
└── /home/osboxes/Desktop/
    └── TradingAgentVnstock.desktop        # [MỚI] Lối tắt 1-click trên màn hình Desktop
```
