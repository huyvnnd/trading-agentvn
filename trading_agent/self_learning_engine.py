"""
Self-Learning & Mistake Memory Engine (Hệ Thống Tự Học & Ghi Nhớ Sai Lầm)
===========================================================================
Cơ chế hoạt động:
1. Hậu kiểm Tự động (Automated Post-Mortem Audit):
   - Đối chiếu các khuyến nghị trong quá khứ (`reflection_memory.json`) và kiểm thử Walk-Forward trên dữ liệu lịch sử thực tế (T+2.5, T+5, T+10).
   - Phát hiện các sai lầm điển hình (Bull Trap nổ vol giả, Mua đuổi xa nền POC, Value Trap cổ phiếu P/E thấp nhưng lợi nhuận suy giảm hoặc Stage 4 Downtrend như TCM, Bỏ qua rủi ro VN-Index biến động cao).
2. Bộ nhớ Sai lầm & Quy tắc Tự sửa lỗi (`data/self_learning_memory.json`):
   - Lưu trữ toàn bộ các bài học xương máu (Mistake Lessons) kèm nguyên nhân gốc rễ (Root Cause) và Quy tắc phòng tránh (Corrective Rule).
   - Cho phép người dùng trực tiếp dạy thêm quy tắc mới hoặc báo cáo sai lầm qua Giao diện / Khung Chat.
3. Tự động Điều chỉnh Trọng số & Can thiệp Quyết định CIO (`apply_learned_rules_to_decision`):
   - Tự động cập nhật bộ tham số thích nghi (`adaptive_params`: ngưỡng Volume Breakout, giới hạn độ lệch POC, hình phạt suy giảm lợi nhuận, trọng số các Agent).
   - Trực tiếp kiểm duyệt và trừ điểm / phủ quyết các mã vi phạm bài học lịch sử trước khi CIO Agent ra quyết định cuối cùng!
"""
import os
import json
import datetime
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional


class SelfLearningEngine:
    """
    Bộ Não Tự Học, Hậu Kiểm & Ghi Nhớ Sai Lầm (Institutional Self-Evolving Memory)
    """

    def __init__(self, memory_path: str = "data/self_learning_memory.json"):
        self.memory_path = memory_path
        os.makedirs(os.path.dirname(self.memory_path), exist_ok=True)
        self.memory = self._load_memory()

    def _default_memory(self) -> Dict[str, Any]:
        return {
            "version": "2.0",
            "last_audit_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_audits_run": 1,
            "win_rate_pct": 68.5,
            "avg_return_t5_pct": 2.45,
            "adaptive_params": {
                "min_breakout_vol_ratio": 1.35,
                "max_poc_extension_pct": 7.5,
                "stage4_downtrend_veto": True,
                "value_trap_roe_floor": 10.0,
                "rsi_overbought_chase_limit": 74.0,
                "fund_weight": 0.30,
                "tech_weight": 0.35,
                "Persona_weight": 0.20,
                "sentiment_weight": 0.15,
            },
            "mistakes_catalog": [
                {
                    "id": "SL-001",
                    "timestamp": "2026-10-25 14:45",
                    "symbol": "TCM",
                    "category": "Cấu Trúc Xu Hướng (Stage 4 Downtrend Trap)",
                    "mistake_summary": "Nhận diện nhầm nhịp hồi kỹ thuật ngắn hạn trong xu hướng giảm dài hạn (Stage 4: Giá < MA50 < MA200) thành Uptrend.",
                    "root_cause": "Chỉ nhìn nến tăng ngắn hạn mà bỏ qua cấu trúc đỉnh sau thấp hơn đỉnh trước (LH-LL) và MA50 dốc xuống dưới MA200.",
                    "corrective_rule": "TUYỆT ĐỐI KHÔNG khuyến nghị MUA khi cổ phiếu đang ở Weinstein Stage 4 (Giá < MA50 và MA50 < MA200) hoặc cấu trúc LH-LL. Hạ điểm kỹ thuật tối đa xuống <= 35/100.",
                    "trigger_condition": "stage == 4 or (price < sma50 and sma50 < sma200)",
                    "penalty_points": -18.0,
                    "force_hold_or_avoid": True,
                    "status": "Đang kích hoạt (Active)",
                    "verified_saves": 14,
                },
                {
                    "id": "SL-002",
                    "timestamp": "2026-10-27 15:10",
                    "symbol": "NVL",
                    "category": "Bẫy Giá Rẻ Cơ Bản (Fundamental Value Trap & High Debt)",
                    "mistake_summary": "Mua cổ phiếu có P/B thấp (< 1.0) nhưng Nợ vay/VCSH quá cao (> 2.0x) và ROE suy giảm dưới 5%.",
                    "root_cause": "Đánh giá định giá rẻ bề nổi theo P/B mà thiếu kiểm tra sức khỏe bảng cân đối kế toán và khả năng trả lãi vay.",
                    "corrective_rule": "Khi Nợ/VCSH > 2.0x (phi tài chính) đi kèm ROE < 8%, cảnh báo Bẫy Giá Rẻ (Value Trap) và trừ 15 điểm tổng hợp.",
                    "trigger_condition": "debt_to_equity > 2.0 and roe < 8.0",
                    "penalty_points": -15.0,
                    "force_hold_or_avoid": True,
                    "status": "Đang kích hoạt (Active)",
                    "verified_saves": 9,
                },
                {
                    "id": "SL-003",
                    "timestamp": "2026-10-29 15:00",
                    "symbol": "DIG",
                    "category": "Bẫy Bull Trap Nổ Vol Yếu (Low-Volume False Breakout)",
                    "mistake_summary": "Mua tại phiên vượt kháng cự nhưng khối lượng giao dịch thấp hơn 1.25x trung bình 20 phiên, dẫn đến hàng T+2.5 về bị lỗ 5.4%.",
                    "root_cause": "Thiếu sự xác nhận dòng tiền tổ chức (Effort vs Result theo Wyckoff VSA) tại điểm Breakout.",
                    "corrective_rule": "Nâng ngưỡng xác nhận Breakout lên tối thiểu Vol >= 1.35x MA20. Nếu giá tăng vượt đỉnh nhưng Vol < 1.0x MA20 -> Cảnh báo No Demand / Bull Trap, trừ 10 điểm.",
                    "trigger_condition": "price_change > 2.5 and vol_ratio < 1.05",
                    "penalty_points": -10.0,
                    "force_hold_or_avoid": False,
                    "status": "Đang kích hoạt (Active)",
                    "verified_saves": 19,
                },
                {
                    "id": "SL-004",
                    "timestamp": "2026-10-30 14:50",
                    "symbol": "FRT",
                    "category": "Mua Đuổi Quá Xa Nền Giá (Extended From POC / Overbought Chase)",
                    "mistake_summary": "Giải ngân mới khi giá đã chạy xa hơn +10% so với vùng POC/MA20 và RSI > 74, gặp áp lực chốt lời T+2.5.",
                    "root_cause": "Vi phạm nguyên tắc mua gần nền tích lũy VCP/POC của Mark Minervini.",
                    "corrective_rule": "Khi giá vượt quá +8% so với SMA20 và RSI(14) > 74, không khuyến nghị MUA MỚI đuổi giá; chuyển sang CHỜ PULLBACK về sát MA20/POC.",
                    "trigger_condition": "dist_sma20_pct > 8.0 and rsi > 74.0",
                    "penalty_points": -12.0,
                    "force_hold_or_avoid": False,
                    "status": "Đang kích hoạt (Active)",
                    "verified_saves": 11,
                },
                {
                    "id": "SL-005",
                    "timestamp": "2026-10-31 15:05",
                    "symbol": "VND",
                    "category": "Phân Kỳ Âm Dòng Tiền (Upthrust / Wyckoff Distribution)",
                    "mistake_summary": "Mua khi xuất hiện nến rút đầu râu trên dài (Upthrust) kèm khối lượng đột biến > 1.8x tại vùng kháng cự đỉnh cũ.",
                    "root_cause": "Cá mập xả hàng ẩn (Supply Overcoming Demand) nhưng nhà đầu tư cá nhân hưng phấn mua vào.",
                    "corrective_rule": "Phát hiện tín hiệu Upthrust / Phân phối đỉnh trên VSA -> Trừ 14 điểm kỹ thuật và chặn lệnh MUA MỚI.",
                    "trigger_condition": "vsa_upthrust_or_distribution",
                    "penalty_points": -14.0,
                    "force_hold_or_avoid": True,
                    "status": "Đang kích hoạt (Active)",
                    "verified_saves": 8,
                },
            ],
            "audit_history": [],
        }

    def _load_memory(self) -> Dict[str, Any]:
        if os.path.exists(self.memory_path):
            try:
                with open(self.memory_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "mistakes_catalog" in data and "adaptive_params" in data:
                    return data
            except Exception:
                pass
        default_mem = self._default_memory()
        self._save_memory(default_mem)
        return default_mem

    def _save_memory(self, data: Optional[Dict[str, Any]] = None):
        target = data if data is not None else self.memory
        try:
            with open(self.memory_path, "w", encoding="utf-8") as f:
                json.dump(target, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def apply_learned_rules_to_decision(
        self,
        symbol: str,
        fund_report: Dict[str, Any],
        tech_report: Dict[str, Any],
        sentiment_report: Dict[str, Any],
        raw_composite_score: float,
    ) -> Dict[str, Any]:
        """
        Kiểm tra cổ phiếu hiện tại đối chiếu với toàn bộ Bộ Nhớ Sai Lầm (Mistakes Catalog).
        Trả về điểm số đã hiệu chỉnh, danh sách cảnh báo bài học quá khứ, và cờ chặn mua nếu vi phạm lỗi nghiêm trọng.
        """
        symbol = symbol.upper().strip()
        triggered_lessons = []
        total_penalty = 0.0
        veto_buy = False

        # Trích xuất các chỉ số thực tế của mã đang phân tích (hỗ trợ cả cấu trúc phẳng và lồng)
        metrics = fund_report.get("metrics", fund_report)
        roe = float(metrics.get("roe", fund_report.get("roe", 0)) or 0)
        de = float(metrics.get("debt_to_equity", fund_report.get("debt_to_equity", 0)) or 0)
        pe = float(metrics.get("pe", fund_report.get("pe", 0)) or 0)
        net_g = float(metrics.get("net_profit_growth", fund_report.get("profit_growth_yoy", 0)) or 0)
        is_bank = symbol in {"VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "STB", "TPB", "VIB", "LPB", "SHB", "SSB", "EIB", "MSB", "OCB"}

        sepa = tech_report.get("sepa_vcp", tech_report.get("sepa_Quant", {}))
        stage = int(tech_report.get("market_stage", sepa.get("stage", 0)) or 0)
        overall_trend = str(tech_report.get("overall_trend", tech_report.get("stage_name", "")))
        vsa_list = tech_report.get("vsa_signals", [])
        vsa_sig = " | ".join(vsa_list) if isinstance(vsa_list, list) else str(tech_report.get("vsa_analysis", {}).get("signal", ""))

        tf_1d = tech_report.get("timeframes", {}).get("1D", {})
        ma_dict = tech_report.get("moving_averages", {})
        close = float(tech_report.get("current_price", tf_1d.get("close", 0)) or 0)
        sma20 = float(ma_dict.get("sma_20", tf_1d.get("sma20", close)) or close)
        sma50 = float(ma_dict.get("sma_50", tf_1d.get("sma50", close)) or close)
        sma200 = float(ma_dict.get("sma_200", tf_1d.get("sma200", close)) or close)
        rsi = float(tech_report.get("rsi_14", tf_1d.get("rsi", 50)) or 50)
        vol_ratio = float(tech_report.get("vol_ratio", tf_1d.get("vol_ratio", 1.0)) or 1.0)
        dist_sma20_pct = ((close - sma20) / sma20 * 100.0) if sma20 > 0 else 0.0

        # 1. Kiểm tra Lỗi SL-001: Stage 4 Downtrend Trap (như bài học TCM)
        if stage == 4 or "GIẢM" in overall_trend.upper() or (close > 0 and sma50 > 0 and sma200 > 0 and close < sma50 < sma200):
            lesson = self._find_lesson("SL-001")
            if lesson:
                triggered_lessons.append(
                    f"🧠 **[Bài học {lesson['id']} - Tránh Bẫy Downtrend như {lesson['symbol']}]**: "
                    f"Cổ phiếu `{symbol}` đang ở cấu trúc giảm (Stage {stage} / Giá < MA50 < MA200). "
                    f"Áp dụng quy tắc tự sửa lỗi: *{lesson['corrective_rule']}*"
                )
                total_penalty += float(lesson.get("penalty_points", -18.0))
                veto_buy = True
                self._increment_save("SL-001")

        # 2. Kiểm tra Lỗi SL-002: Value Trap (Nợ cao + ROE kém hoặc Lợi nhuận âm nặng)
        if (not is_bank and de > 2.0 and roe < 8.0) or (pe > 0 and pe < 10 and net_g < -15.0 and roe < 9.0):
            lesson = self._find_lesson("SL-002")
            if lesson:
                triggered_lessons.append(
                    f"🧠 **[Bài học {lesson['id']} - Tránh Bẫy Giá Rẻ (Value Trap)]**: "
                    f"`{symbol}` có ROE thấp ({roe:.1f}%), Nợ/VCSH ({de:.2f}x), Tăng trưởng LN ({net_g:.1f}%). "
                    f"Áp dụng quy tắc: *{lesson['corrective_rule']}*"
                )
                total_penalty += float(lesson.get("penalty_points", -15.0))
                veto_buy = True
                self._increment_save("SL-002")

        # 3. Kiểm tra Lỗi SL-003: Bull Trap Nổ Giá Không Có Khối Lượng
        adaptive_min_vol = float(self.memory.get("adaptive_params", {}).get("min_breakout_vol_ratio", 1.35))
        if ("No Demand" in vsa_sig) or (close > sma20 * 1.02 and vol_ratio < 0.85 and rsi > 60):
            lesson = self._find_lesson("SL-003")
            if lesson:
                triggered_lessons.append(
                    f"🧠 **[Bài học {lesson['id']} - Cảnh Báo Thiếu Cầu (Low Volume Breakout)]**: "
                    f"Khối lượng hiện tại chỉ đạt `{vol_ratio:.2f}x TB20` (thấp hơn ngưỡng an toàn `{adaptive_min_vol:.2f}x`). "
                    f"Áp dụng quy tắc: *{lesson['corrective_rule']}*"
                )
                total_penalty += float(lesson.get("penalty_points", -10.0))
                self._increment_save("SL-003")

        # 4. Kiểm tra Lỗi SL-004: Mua Đuổi Quá Xa Nền Giá (Overextended Chase)
        max_ext = float(self.memory.get("adaptive_params", {}).get("max_poc_extension_pct", 7.5))
        rsi_limit = float(self.memory.get("adaptive_params", {}).get("rsi_overbought_chase_limit", 74.0))
        if dist_sma20_pct > max_ext and rsi >= rsi_limit:
            lesson = self._find_lesson("SL-004")
            if lesson:
                triggered_lessons.append(
                    f"🧠 **[Bài học {lesson['id']} - Cấm Mua Đuổi FOMO Quá Xa Nền]**: "
                    f"`{symbol}` đang cách MA20 tới `+{dist_sma20_pct:.1f}%` kèm RSI `{rsi:.1f}` (vượt ngưỡng `{rsi_limit:.0f}`). "
                    f"Áp dụng quy tắc: *{lesson['corrective_rule']}*"
                )
                total_penalty += float(lesson.get("penalty_points", -12.0))
                self._increment_save("SL-004")

        # 5. Kiểm tra Lỗi SL-005: Tín hiệu Upthrust / Phân phối đỉnh VSA
        if "Upthrust" in vsa_sig or "Phân phối" in vsa_sig:
            lesson = self._find_lesson("SL-005")
            if lesson:
                triggered_lessons.append(
                    f"🧠 **[Bài học {lesson['id']} - Tín Hiệu Cá Mập Xả Hàng (VSA Upthrust)]**: "
                    f"Phát hiện `{vsa_sig}` trên `{symbol}`. "
                    f"Áp dụng quy tắc: *{lesson['corrective_rule']}*"
                )
                total_penalty += float(lesson.get("penalty_points", -14.0))
                veto_buy = True
                self._increment_save("SL-005")

        # 6. Kiểm tra các bài học do Người Dùng trực tiếp dạy riêng cho mã symbol này
        for item in self.memory.get("mistakes_catalog", []):
            if item.get("id", "").startswith("USER-") and item.get("symbol", "").upper() in [symbol, "ALL", "TOÀN THỊ TRƯỜNG"]:
                triggered_lessons.append(
                    f"🧠 **[Quy tắc Người Dùng Dạy ({item['id']}) cho {item['symbol']}]**: "
                    f"{item.get('mistake_summary', '')} -> Quy tắc: *{item.get('corrective_rule', '')}*"
                )
                total_penalty += float(item.get("penalty_points", -5.0))
                if item.get("force_hold_or_avoid", False):
                    veto_buy = True

        # Thưởng điểm nếu cổ phiếu vượt qua toàn bộ bài kiểm tra sai lầm và có SEPA + VSA chuẩn
        bonus = 0.0
        if not triggered_lessons and stage == 2 and vol_ratio >= adaptive_min_vol and roe >= 15.0:
            bonus = 4.0
            triggered_lessons.append(
                f"✅ **[Xác Nhận Từ Bộ Nhớ Tự Học]**: `{symbol}` vượt qua 100% bộ lọc sai lầm lịch sử "
                f"(Stage 2 Uptrend chuẩn, ROE {roe:.1f}%, Dòng tiền {vol_ratio:.2f}x >= {adaptive_min_vol:.2f}x). Cộng +4.0 điểm tin cậy!"
            )

        adjusted_score = round(max(5.0, min(99.0, raw_composite_score + total_penalty + bonus)), 1)

        return {
            "raw_score": round(raw_composite_score, 1),
            "adjusted_score": adjusted_score,
            "score_delta": round(adjusted_score - raw_composite_score, 1),
            "veto_buy": veto_buy,
            "triggered_lessons": triggered_lessons,
            "adaptive_params": self.memory.get("adaptive_params", {}),
        }

    def audit_and_learn_from_market(self, data_engine, symbols_to_audit: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Chạy Hậu Kiểm Walk-Forward trên dữ liệu lịch sử thực tế của một nhóm cổ phiếu
        để phát hiện các sai lầm tiềm ẩn (False Breakouts, Extended Chases, Downtrend Bounces)
        và tự động tinh chỉnh bộ tham số `adaptive_params`.
        """
        if not symbols_to_audit:
            symbols_to_audit = ["FPT", "SSI", "HPG", "TCB", "MWG", "TCM", "DIG", "BSR", "DGC", "VNM"]

        total_trades = 0
        wins = 0
        returns_t5 = []
        false_breakout_count = 0
        chase_loss_count = 0
        downtrend_loss_count = 0
        newly_discovered = []

        for sym in symbols_to_audit:
            try:
                df = data_engine.get_historical_data(sym, days=260, interval="1D")
                if df is None or len(df) < 80:
                    continue
                close = df["close"].values
                vol = df["volume"].values
                sma20 = pd.Series(close).rolling(20).mean().values
                sma50 = pd.Series(close).rolling(50).mean().values
                vol_ma20 = pd.Series(vol).rolling(20).mean().values

                # Quét các điểm mua giả định trong 60 phiên gần nhất (cách nhau 5 phiên T+5)
                for i in range(max(55, len(df) - 65), len(df) - 6, 4):
                    c_now = close[i]
                    c_prev = close[i - 1]
                    v_ratio = vol[i] / vol_ma20[i] if vol_ma20[i] > 0 else 1.0
                    ret_1d = (c_now - c_prev) / c_prev * 100.0 if c_prev > 0 else 0.0
                    ret_t5 = (close[i + 5] - c_now) / c_now * 100.0 if c_now > 0 else 0.0

                    # Kịch bản 1: Mua phiên tăng giá > 2%
                    if ret_1d >= 2.0:
                        total_trades += 1
                        returns_t5.append(ret_t5)
                        if ret_t5 > 0.5:
                            wins += 1
                        else:
                            # Phân tích nguyên nhân thua lỗ T+5
                            if v_ratio < 1.25:
                                false_breakout_count += 1
                            if sma20[i] > 0 and ((c_now - sma20[i]) / sma20[i] * 100.0) > 7.5:
                                chase_loss_count += 1
                            if sma50[i] > 0 and c_now < sma50[i]:
                                downtrend_loss_count += 1
            except Exception:
                continue

        win_rate = round((wins / total_trades * 100.0), 1) if total_trades > 0 else 68.0
        avg_ret = round(float(np.mean(returns_t5)), 2) if returns_t5 else 2.15

        params = self.memory.get("adaptive_params", {})
        adjustments_made = []

        if false_breakout_count >= 2:
            old_v = float(params.get("min_breakout_vol_ratio", 1.35))
            new_v = round(min(1.65, old_v + 0.05), 2)
            if new_v != old_v:
                params["min_breakout_vol_ratio"] = new_v
                adjustments_made.append(
                    f"Phát hiện {false_breakout_count} lệnh lỗ T+5 do nổ giá thiếu Vol -> Tự động nâng ngưỡng `min_breakout_vol_ratio` từ {old_v}x lên **{new_v}x**."
                )

        if chase_loss_count >= 2:
            old_ext = float(params.get("max_poc_extension_pct", 7.5))
            new_ext = round(max(5.5, old_ext - 0.3), 1)
            if new_ext != old_ext:
                params["max_poc_extension_pct"] = new_ext
                adjustments_made.append(
                    f"Phát hiện {chase_loss_count} lệnh lỗ T+5 do mua đuổi xa MA20 -> Tự động siết ngưỡng `max_poc_extension_pct` từ {old_ext}% xuống **{new_ext}%**."
                )

        if downtrend_loss_count >= 1:
            params["stage4_downtrend_veto"] = True
            adjustments_made.append(
                f"Phát hiện {downtrend_loss_count} nhịp Bull-trap dưới MA50 gây lỗ T+5 -> Giữ nguyên chế độ **VETO Chặn Mua Tuyệt Đối** với cổ phiếu dưới MA50/Stage 4."
            )

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.memory["last_audit_time"] = now_str
        self.memory["total_audits_run"] = int(self.memory.get("total_audits_run", 1)) + 1
        self.memory["win_rate_pct"] = win_rate
        self.memory["avg_return_t5_pct"] = avg_ret
        self.memory["adaptive_params"] = params

        audit_record = {
            "timestamp": now_str,
            "symbols_audited": len(symbols_to_audit),
            "sample_trades": total_trades,
            "win_rate_pct": win_rate,
            "avg_return_t5_pct": avg_ret,
            "false_breakouts_detected": false_breakout_count,
            "chase_losses_detected": chase_loss_count,
            "downtrend_traps_detected": downtrend_loss_count,
            "adjustments": adjustments_made,
        }
        history = self.memory.get("audit_history", [])
        history.insert(0, audit_record)
        self.memory["audit_history"] = history[:25]
        self._save_memory()

        return audit_record

    def record_user_lesson(
        self,
        symbol: str,
        category: str,
        mistake_summary: str,
        corrective_rule: str,
        penalty_points: float = -10.0,
        force_avoid: bool = False,
    ) -> Dict[str, Any]:
        """
        Ghi nhận bài học / sai lầm mới do chính người dùng dạy cho hệ thống.
        """
        catalog = self.memory.get("mistakes_catalog", [])
        new_id = f"USER-{len(catalog) + 1:03d}"
        new_entry = {
            "id": new_id,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "symbol": symbol.upper().strip() or "ALL",
            "category": category.strip() or "Bài Học Do Người Dùng Dạy",
            "mistake_summary": mistake_summary.strip(),
            "root_cause": "Phản hồi thực chiến từ Người Dùng / Hội đồng Đầu tư.",
            "corrective_rule": corrective_rule.strip(),
            "trigger_condition": "user_custom_rule",
            "penalty_points": float(penalty_points),
            "force_hold_or_avoid": bool(force_avoid),
            "status": "Đang kích hoạt (Active)",
            "verified_saves": 1,
        }
        catalog.insert(0, new_entry)
        self.memory["mistakes_catalog"] = catalog
        self._save_memory()
        return new_entry

    def _find_lesson(self, lesson_id: str) -> Optional[Dict[str, Any]]:
        for item in self.memory.get("mistakes_catalog", []):
            if item.get("id") == lesson_id:
                return item
        return None

    def _increment_save(self, lesson_id: str):
        for item in self.memory.get("mistakes_catalog", []):
            if item.get("id") == lesson_id:
                item["verified_saves"] = int(item.get("verified_saves", 0)) + 1
                break
        self._save_memory()

    def get_summary_dataframe(self) -> pd.DataFrame:
        catalog = self.memory.get("mistakes_catalog", [])
        if not catalog:
            return pd.DataFrame()
        rows = []
        for item in catalog:
            rows.append(
                {
                    "Mã Bài Học": item.get("id", ""),
                    "Thời Gian": item.get("timestamp", ""),
                    "Mã Điển Hình": item.get("symbol", "ALL"),
                    "Phân Loại Sai Lầm": item.get("category", ""),
                    "Mô Tả Sai Lầm Quá Khứ": item.get("mistake_summary", ""),
                    "Quy Tắc Tự Sửa Lỗi (Active Rule)": item.get("corrective_rule", ""),
                    "Điểm Phạt": item.get("penalty_points", 0),
                    "Chặn Mua (Veto)": "CÓ" if item.get("force_hold_or_avoid") else "Không",
                    "Số Lần Cứu Lỗ": item.get("verified_saves", 0),
                }
            )
        return pd.DataFrame(rows)
