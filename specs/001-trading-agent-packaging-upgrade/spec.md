# Feature Specification: 001 - Comprehensive Packaging, Optimization & System Upgrade for Trading Agent Vnstock

**Feature Branch**: `001-trading-agent-packaging-upgrade`  
**Created**: 2026-11-06  
**Status**: Completed (100% Verified)  
**Framework**: Specification-Driven Development (github/spec-kit)  
**Input**: User request: "hãy áp dụng nó rà soát tối ưu khắc phục các lỗi nâng cấp toàn diện lại chương trình Đóng Gói Trading Agent Vnstock"

---

## 🎯 Executive Summary & Business Goals

Dự án **Trading Agent Vnstock (Vietnam Quantitative Multi-Agent Hedge Fund Platform)** đã tích hợp tinh hoa từ 8 dự án mã nguồn mở (`TradingAgents`, `ai-hedge-fund`, `FinRL`, `FinRobot`, `claude-trading-skills`, `vnstock`, `TradingAgents-Vn`, `vnstock_chart`) và hệ thống AmiBroker VPA 5.0.

Tuy nhiên, khâu **Đóng gói (Packaging)**, **Quản lý tiến trình (Process Lifecycle)** và **Kiểm thử tự động (Verification)** hiện tại còn tồn tại một số điểm yếu kỹ thuật:
1. Thiếu chuẩn đóng gói Python chuẩn mực (`pyproject.toml`, `setup.py`, `requirements.txt`), package `trading_agent` chưa được cài đặt chính quy.
2. Scripts điều khiển tiến trình nền (`start_trading_agent.sh`, `status_trading_agent.sh`, `stop_trading_agent.sh`) có hiện tượng **lệch PID (PID desync)** khi khởi động từ các nguồn khác nhau, thiếu kiểm tra trạng thái HTTP health check (`/_stcore/health`) tự động.
3. Người dùng trên môi trường Linux Desktop thiếu lối tắt 1-click (`.desktop` launcher) để mở ứng dụng ngay từ màn hình Desktop mà không cần gõ lệnh terminal.
4. Thiếu bộ kiểm thử hồi quy xác định (Deterministic Verification Suite) để chứng minh 100% các thuật toán cốt lõi (3-Tier Institutional Consensus, Benjamin Graham, Minervini SEPA, VSA/SMC, Weinstein Stages, FinRL) không bị suy giảm hiệu năng hoặc phát sinh lỗi tiềm ẩn.

---

## 👥 User Scenarios & Prioritized User Stories

### User Story 1 (P1 - Core MVP): Standardized Python Packaging & Robust Process Control
**Mô tả**: Là một nhà đầu tư hoặc kỹ sư vận hành, tôi muốn hệ thống Trading Agent được đóng gói chuẩn mực theo quy cách Python (`pyproject.toml`, `setup.py`, `requirements.txt`, CLI entrypoint `trading-agent`) và có bộ script điều khiển tiến trình nền (`start`, `stop`, `restart`, `status`) chống treo, tự động đồng bộ PID và kiểm tra cổng mạng/health check.

**Why this priority**: Đây là nền tảng sống còn của việc "Đóng gói". Nếu tiến trình bị xung đột cổng, lưu sai PID hoặc thiếu file cấu hình cài đặt chuẩn, ứng dụng sẽ không thể vận hành độc lập, ổn định 24/7.

**Independent Test**:
- Cài đặt package ở chế độ editable hoặc build wheel thành công.
- Chạy `./start_trading_agent.sh`, kiểm tra `./status_trading_agent.sh` hiển thị đúng PID và HTTP 200 health check.
- Chạy `./stop_trading_agent.sh`, kiểm tra giải phóng toàn bộ port 8502 và xóa sạch PID file.

**Acceptance Scenarios**:
1. **Given** môi trường Python venv, **When** chạy `pip install -e .`, **Then** package `trading_agent` được cài đặt chính thức và lệnh CLI `trading-agent --help` hoặc `python -m trading_agent.cli` hiển thị menu trợ giúp.
2. **Given** ứng dụng đang chạy ở port 8502, **When** chạy `./status_trading_agent.sh`, **Then** script phát hiện chính xác PID thực tế, mức chiếm dụng RAM/CPU và tình trạng HTTP health check `/_stcore/health`.
3. **Given** lệnh `./start_trading_agent.sh` được gọi khi cổng 8502 đang bị tiến trình cũ chiếm dụng hoặc PID file bị stale, **When** khởi động, **Then** script tự động dọn dẹp tiến trình cũ, khởi chạy tiến trình mới và cập nhật PID file chuẩn xác.

---

### User Story 2 (P1 - Core MVP): One-Click Desktop Launcher for Linux
**Mô tả**: Là người dùng máy tính để bàn (Linux Desktop), tôi muốn có một biểu tượng lối tắt (Desktop Shortcut) ngay trên màn hình Desktop để chỉ cần nhấp đúp chuột là hệ thống Trading Agent tự khởi động và tự động mở trình duyệt web mà không cần mở terminal.

**Why this priority**: Mang lại trải nghiệm người dùng trực quan, chuyên nghiệp như một phần mềm thương mại độc lập.

**Independent Test**:
- Kiểm tra file `/home/osboxes/Desktop/TradingAgentVnstock.desktop` tồn tại, có quyền thực thi và mở đúng URL `http://localhost:8502`.

**Acceptance Scenarios**:
1. **Given** màn hình Desktop, **When** người dùng nhấp đúp chuột vào shortcut `TradingAgentVnstock.desktop`, **Then** dịch vụ daemon được khởi chạy và trình duyệt tự động mở đến `http://localhost:8502`.

---

### User Story 3 (P2): Engine Optimization & 100% Contradiction-Free Audit
**Mô tả**: Là một thành viên Hội đồng Đầu tư, tôi muốn toàn bộ mã nguồn của bộ lọc (`VSASMCScreener`, `StockScreener`), Hội đồng CIO (`CIOAgent`), và Giao diện (`app.py`) được tối ưu hóa tốc độ nạp dữ liệu, chống rò rỉ bộ nhớ cache, và duy trì nghiêm ngặt cơ chế phản biện 3 nhóm (Stage 2 Buys vs Stage 1 Watchlist vs Stage 4 Downtrend Avoid).

**Why this priority**: Đảm bảo hiệu năng phản hồi < 0.4s và ngăn chặn tuyệt đối các mâu thuẫn như vụ việc mã `NKG` tái diễn.

**Independent Test**:
- Chạy kiểm tra bộ lọc 3 tầng trên toàn bộ vũ trụ 70 cổ phiếu; xác nhận 0 mã nào ở Stage 1 lọt vào danh sách Mua Stage 2.

**Acceptance Scenarios**:
1. **Given** vũ trụ 70 mã cổ phiếu thanh khoản cao, **When** chạy `VSASMCScreener.scan_three_tier_universe()`, **Then** các mã Stage 1 như `NKG`, `TPB`, `VJC` bắt buộc nằm trong `df_watchlist` với khuyến nghị `TẠM DỪNG / WATCHLIST`, và chỉ mã Stage 2 đạt chuẩn Minervini SEPA $\ge 5/8$ mới vào `df_buy`.

---

### User Story 4 (P3): Self-Diagnostic Verification Suite (`verify_system.py`)
**Mô tả**: Là kỹ sư kiểm toán chất lượng, tôi muốn có một bộ script kiểm thử tự chẩn đoán toàn diện (`verify_system.py`) kiểm tra:
1. Cấu hình môi trường & thư viện dependencies.
2. Dữ liệu bảng giá KBS Batch & Lịch sử VN-Index.
3. Độ chính xác của các công thức định lượng (Damodaran, Graham, Minervini SEPA, VSA/SMC, FinRL Half-Kelly).
4. Tính thống nhất của Hội đồng CIO.
5. Tiến trình Streamlit daemon và cổng mạng.

**Why this priority**: Cung cấp bằng chứng kiểm chứng khách quan, có thể tái lập (Deterministic Verification Evidence) theo đúng chuẩn GitHub Spec Kit.

---

## 🚫 Out of Scope
- Không thay đổi các công thức toán học tài chính đã được kiểm chứng chuẩn xác (Graham, Minervini, VSA).
- Không chuyển đổi giao diện Streamlit sang web framework khác (React/Next.js) trong bản nâng cấp này để đảm bảo tính ổn định và quen thuộc của người dùng.
