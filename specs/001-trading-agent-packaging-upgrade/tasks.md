# Tasks: 001 - Comprehensive Packaging, Optimization & System Upgrade for Trading Agent Vnstock

**Input**: Design documents from `specs/001-trading-agent-packaging-upgrade/`  
**Prerequisites**: `spec.md`, `plan.md`

## Format: `[ID] [P?] [Story] Description`
- `[P]`: Can run in parallel
- `[Story]`: User story association (`US1`, `US2`, `US3`, `US4`)

---

## Phase 1: Packaging Infrastructure (US1)
- [x] **T001** `[US1]` Trích xuất danh mục dependencies chuẩn hóa ra tệp `requirements.txt` từ môi trường `venv`.
- [x] **T002** `[US1]` Xây dựng tệp `pyproject.toml` chuẩn hóa PEP 517/621 với metadata, dependencies và entrypoint CLI `trading-agent`.
- [x] **T003** `[US1]` Tạo tệp `setup.py` để hỗ trợ `pip install -e .` tương thích ngược.
- [x] **T004** `[US1]` Xây dựng module `trading_agent/cli.py` hỗ trợ đầy đủ các lệnh: `start`, `stop`, `restart`, `status`, `scan`, `analyze`, `verify`.
- [x] **T005** `[US1]` Cài đặt package `trading_agent` vào virtualenv và kiểm thử lệnh CLI `trading-agent --help`.

---

## Phase 2: Process Control & Desktop Launcher (US1, US2)
- [x] **T006** `[US1]` Nâng cấp `start_trading_agent.sh` hỗ trợ tự phát hiện xung đột cổng, tự động dọn stale PID, kiểm tra HTTP health check và tham số `restart`.
- [x] **T007** `[US1]` Nâng cấp `stop_trading_agent.sh` và `status_trading_agent.sh` với cơ chế nhận diện PID thực từ port và hiển thị kết quả kiểm tra `/_stcore/health`.
- [x] **T008** `[US2]` Tạo tệp lối tắt màn hình Desktop `/home/osboxes/Desktop/TradingAgentVnstock.desktop` cấp quyền thực thi `chmod +x`.

---

## Phase 3: Engine Audit & Zero-Contradiction Verification (US3)
- [x] **T009** `[US3]` Rà soát toàn bộ bộ lọc và kiểm chứng 100% không phát sinh mâu thuẫn giữa `vsa_smc_screener.py`, `screener.py`, `cio_agent.py` và `app.py`.

---

## Phase 4: Self-Diagnostic Suite & Documentation (US4)
- [x] **T010** `[US4]` Xây dựng script kiểm tra tự động `verify_system.py` kiểm định toàn diện môi trường, nguồn cấp dữ liệu, công thức định lượng, tiến trình nền và in bảng báo cáo tổng hợp.
- [x] **T011** `[US4]` Cập nhật `HUONG_DAN_SU_DUNG.md` và `README.md` bổ sung hướng dẫn chi tiết cách vận hành gói phần mềm, các lệnh CLI và lối tắt Desktop.
