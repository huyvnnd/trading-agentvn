# 🏛️ Vietnam Institutional Quantitative Multi-Agent Hedge Fund Platform (V2.0.0)

Hệ thống AI Trading Agent Mô Hình Tổ Chức Quỹ Đầu Tư Chuyên Nghiệp (Institutional Investment Committee & Hedge Fund) cho thị trường chứng khoán Việt Nam, tích hợp trực tiếp dữ liệu realtime từ [vnstock](https://github.com/thinh-vu/vnstock.git) và tuân thủ chặt chẽ phương pháp luận **Specification-Driven Development (GitHub Spec-Kit SDD)**.

---

## 🌟 Tinh Hoa Kiến Trúc & Tính Năng Chuyên Nghiệp

- **Đóng gói chuẩn Python Package (PEP 517 / PEP 621)**:
  - Cài đặt và phân phối độc lập qua `pyproject.toml`, `setup.py`, `requirements.txt`.
  - Cung cấp CLI console script toàn năng: `trading-agent` (`start`, `stop`, `restart`, `status`, `scan`, `analyze`, `verify`).
- **Phân tách 3 Tầng Nhà Nghề (Three-Tier Institutional Separation)**:
  - 🟢 **Tier 1 (Approved Stage 2 Buys)**: Stage 2 + SEPA ≥ 5/8 + RS ≥ 65 + Score ≥ 35 + Phê duyệt CIO (12% - 25% NAV).
  - 🟡 **Tier 2 (Watchlist)**: Stage 1 Tích lũy nền giá hoặc pullback hỗ trợ POC (Ví dụ: `NKG`, `TPB`, `VJC`). Phân bổ tuyệt đối 0% NAV.
  - ⛔ **Tier 3 (Avoid / Strict Veto)**: Cổ phiếu Downtrend Stage 4 & rủi ro cao. Phủ quyết 100%.
- **Hội Đồng Đầu Tư Đa Agent (Investment Committee Swarm)**:
  - 🌐 **Macro & Turbulence Agent**: Phân tích vĩ mô toàn cầu & trong nước, đếm ngày phân phối VN-Index, Mahalanobis Turbulence Index.
  - 🏢 **Fundamental & Valuation Agent**: DuPont 3 bước, định giá Damodaran DCF / Excess Return, Benjamin Graham, Peter Lynch PEG.
  - 📐 **MTF Structure & VSA/SMC Agent**: Chu kỳ Stan Weinstein Stage 1-4, Mark Minervini SEPA 8 tiêu chí, mẫu hình VCP, Wyckoff Volume Profile POC.
  - 🌊 **Foreign & Sentiment Agent**: Dòng tiền Khối ngoại, tự doanh, cảnh báo bẫy truyền thông FOMO.
  - 🛡️ **Risk Officer (Bear Officer)**: Phản biện đối kháng rủi ro, kiểm định trượt giá chu kỳ $T+2.5$.
  - 🎯 **CIO Phán Quyết**: Tỷ trọng tối ưu Half-Kelly, quy đổi lô chẵn 100 cổ phiếu, giải ngân 2 đợt an toàn.
- **Tự Học & Tự Chẩn Đoán (Self-Learning & Auto-Verification)**:
  - Ghi nhận và phản tư liên tục tại `data/reflection_memory.json` và `data/self_learning_memory.json`.
  - Bộ kiểm định tự động `trading-agent verify` (100% test pass).

---

## 🚀 Hướng Dẫn Khởi Động & Sử Dụng

### 1. Khởi động 1-Click từ Màn Hình Desktop (Cả 2 Biểu Tượng)
Nhấp đúp chuột vào bất kỳ biểu tượng nào trên màn hình Desktop (**`Trading Agent Vnstock`** hoặc **`Vietnam Trading Agent`**). Hệ thống sẽ bắn thông báo xác nhận (`notify-send`), kiểm tra kích hoạt tiến trình daemon nền và tự động mở trình duyệt Web trực tiếp vào Dashboard. Bạn cũng có thể nhấp chuột phải vào biểu tượng để chọn các tác vụ nhanh (*Mở Browser, Kiểm tra Status Terminal, Khởi động lại, Dừng*).

### 2. Sử dụng Giao Diện Dòng Lệnh Toàn Năng (`trading-agent` CLI)
Hệ thống cung cấp lệnh CLI chuyên dụng:

```bash
# Kích hoạt môi trường (nếu chưa kích hoạt)
source /home/osboxes/Desktop/trading/venv/bin/activate

# 1. Khởi động tiến trình nền (Daemon)
trading-agent start

# 2. Kiểm tra trạng thái hoạt động, CPU, RAM & HTTP Health
trading-agent status

# 3. Quét thị trường theo bộ lọc 3 tầng định lượng
trading-agent scan

# 4. Triệu tập Hội đồng CIO thẩm định 1 mã cụ thể
trading-agent analyze NKG
trading-agent analyze VIC

# 5. Chạy bộ kiểm thử tự chẩn đoán toàn diện hệ thống
trading-agent verify

# 6. Dừng hoặc khởi động lại hệ thống
trading-agent stop
trading-agent restart
```

### 3. Vận Hành Qua Shell Scripts Truyền Thống
```bash
cd /home/osboxes/Desktop/trading

./start_trading_agent.sh       # Khởi động nền (hoặc ./start_trading_agent.sh restart)
./status_trading_agent.sh      # Kiểm tra trạng thái
./stop_trading_agent.sh        # Dừng hệ thống an toàn
```

🌐 **Giao diện Web Dashboard:** [http://localhost:8502](http://localhost:8502)

---

## 🛠️ Cài Đặt & Phát Triển (Developer Setup)

```bash
cd /home/osboxes/Desktop/trading

# Cài đặt môi trường ở chế độ Editable
pip install -e .

# Chạy kiểm định toàn diện
python verify_system.py
```

---

## 📖 Tài Liệu Tham Chiếu
- Xem chi tiết tại [HUONG_DAN_SU_DUNG.md](HUONG_DAN_SU_DUNG.md).
- Thông số kỹ thuật SDD tại [specs/001-trading-agent-packaging-upgrade/spec.md](specs/001-trading-agent-packaging-upgrade/spec.md).
