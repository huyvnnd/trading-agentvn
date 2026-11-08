"""
High-Speed Multi-Strategy Stock Screener Module for Vietnam Market.
Quét song song đa luồng (Multi-threaded) kết hợp Master Universe Evaluation Cache (< 0.002s khi lọc chuyển đổi tiêu chí):
- 'all': Xếp hạng tổng hợp Kỹ thuật & Sức mạnh giá RS
- 'sepa_vcp': Đạt chuẩn Mark Minervini SEPA (≥ 6/8) hoặc Mẫu hình VCP Giai đoạn 2
- 'canslim_leaders': Cổ phiếu dẫn dắt RS Rating ≥ 72 & Giai đoạn 2 Uptrend
- 'bottom_fishing': Cổ phiếu Bắt Đáy An Toàn / Tạo Đáy Quá Bán Tại Hỗ Trợ (Wyckoff Spring, Stopping Volume, RSI thấp, Chạm BB dưới/MA50/MA200 + Có cơ bản bảo vệ)
- 'rsi_oversold': RSI thấp / Quá bán ngắn hạn trên nền hỗ trợ
- 'golden_cross': SMA20 cắt lên SMA50 trên nền MA200
- 'volume_spike': Đột biến khối lượng (> 135% TB20) kèm nến tăng
- 'breakout': Bứt phá vượt đỉnh 20 phiên trong Giai đoạn 2
- 'value_investing': Định giá hấp dẫn (P/E ≤ 15.5 & ROE ≥ 13.5% & Không ở Stage 4)
- 'low_debt': An toàn tài chính cao (Nợ vay / VCSH ≤ 0.85 & ROE ≥ 12%)
- 'avoid_stage4': Danh sách cổ phiếu Giai đoạn 4 Downtrend / Rủi ro cao bắt buộc tránh xa
"""

import os
import time
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from trading_agent.data_engine import DataEngine, SECTOR_MAP
from trading_agent.technical_analysis import TechnicalAnalysis
from trading_agent.quant_engine import QuantEngine
from trading_agent.vsa_smc_screener import INSTITUTIONAL_LIQUID_UNIVERSE


class StockScreener:
    _master_cache_records = None
    _master_cache_ts = 0.0
    _disk_cache_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "screener_master_cache.pkl"))

    def __init__(self, data_engine: DataEngine = None):
        self.de = data_engine or DataEngine()
        self._load_disk_master_cache()

    CACHE_VERSION = "v7_mcdx_strict_vhm_vpb"

    @classmethod
    def _load_disk_master_cache(cls):
        if cls._master_cache_records is not None:
            return
        try:
            if os.path.exists(cls._disk_cache_file):
                with open(cls._disk_cache_file, "rb") as f:
                    data = pickle.load(f)
                if not isinstance(data, dict) or data.get("version") != cls.CACHE_VERSION:
                    return
                ts = data.get("ts", 0.0)
                recs = data.get("records", None)
                if recs and (time.time() - ts < 1800):
                    cls._master_cache_records = recs
                    cls._master_cache_ts = ts
        except Exception:
            pass

    @classmethod
    def _save_disk_master_cache(cls, records: list):
        try:
            os.makedirs(os.path.dirname(cls._disk_cache_file), exist_ok=True)
            now_ts = time.time()
            cls._master_cache_records = records
            cls._master_cache_ts = now_ts
            with open(cls._disk_cache_file, "wb") as f:
                pickle.dump({"version": cls.CACHE_VERSION, "ts": now_ts, "records": records}, f)
        except Exception:
            pass

    def _evaluate_master_symbol(self, sym: str, df_vnindex: pd.DataFrame, pb: dict) -> dict:
        try:
            df = self.de.get_history(sym, days=380)
            if df.empty or len(df) < 35:
                return None

            df_ind = TechnicalAnalysis.calculate_indicators(df)
            sig = TechnicalAnalysis.get_summary_signals(df_ind)

            curr = df_ind.iloc[-1]
            prev = df_ind.iloc[-2]

            close = float(pb.get(sym, {}).get("price", curr["close"]))
            if close <= 0:
                close = float(curr["close"])

            open_p = float(curr["open"])
            high_p = float(curr["high"])
            low_p = float(curr["low"])
            prev_close = float(prev["close"]) if pd.notna(prev.get("close")) else close
            chg_pct = ((close - prev_close) / max(prev_close, 1.0)) * 100.0

            rsi = float(curr["rsi"]) if pd.notna(curr.get("rsi")) else 50.0
            prev_rsi = float(prev["rsi"]) if pd.notna(prev.get("rsi")) else rsi
            d_rsi = rsi - prev_rsi
            sma20 = float(curr["sma_20"]) if pd.notna(curr.get("sma_20")) else close
            sma50 = float(curr["sma_50"]) if pd.notna(curr.get("sma_50")) else close
            sma200 = float(curr["sma_200"]) if pd.notna(curr.get("sma_200")) else sma50
            prev_sma20 = float(prev["sma_20"]) if pd.notna(prev.get("sma_20")) else sma20
            prev_sma50 = float(prev["sma_50"]) if pd.notna(prev.get("sma_50")) else sma50
            vol_ratio = float(curr["vol_ratio"]) if pd.notna(curr.get("vol_ratio")) else 1.0
            bb_low = float(curr["bb_low"]) if pd.notna(curr.get("bb_low")) else close * 0.95

            mcdx_banker = float(curr["mcdx_banker"]) if pd.notna(curr.get("mcdx_banker")) else 0.0
            prev_banker = float(prev["mcdx_banker"]) if pd.notna(prev.get("mcdx_banker")) else mcdx_banker
            mcdx_b_sma36 = float(curr["mcdx_banker_sma36"]) if pd.notna(curr.get("mcdx_banker_sma36")) else 0.0
            mcdx_fast = float(curr["mcdx_fast"]) if pd.notna(curr.get("mcdx_fast")) else 10.0
            prev_fast = float(prev["mcdx_fast"]) if pd.notna(prev.get("mcdx_fast")) else mcdx_fast
            mcdx_slow = float(curr["mcdx_slow"]) if pd.notna(curr.get("mcdx_slow")) else 10.0
            d_banker = mcdx_banker - prev_banker
            d_fast = mcdx_fast - prev_fast
            smc_pos_pct = float(curr["smc_pos_pct"]) if pd.notna(curr.get("smc_pos_pct")) else 50.0
            williams_r = float(curr["williams_r"]) if pd.notna(curr.get("williams_r")) else -50.0

            high_20_prev = float(df_ind["high"].shift(1).rolling(20).max().iloc[-1])
            low_20_prev = float(df_ind["low"].shift(1).rolling(20).min().iloc[-1])
            high_60 = float(df_ind["high"].rolling(min(60, len(df_ind))).max().iloc[-1])
            discount_60_pct = ((close - high_60) / high_60 * 100.0) if high_60 > 0 else 0.0

            rs_info = QuantEngine.compute_rs_rating(df, df_vnindex)
            sepa_vcp = QuantEngine.evaluate_minervini_sepa_and_vcp(df, rs_rating=rs_info["rs_rating"])

            ov = self.de.get_company_overview(sym) or {}
            pe = ov.get("pe")
            roe = ov.get("roe")
            de_ratio = ov.get("debt_to_equity")
            prof_g = float(ov.get("profit_growth_yoy", 0.0) or 0.0)
            dup = QuantEngine.compute_dupont_and_valuation(ov)
            mos_pct = dup.get("margin_of_safety_pct")
            mos_val = float(mos_pct) if mos_pct is not None else 0.0

            pe_val = float(pe) if pe is not None else 999.0
            roe_val = float(roe) if roe is not None else -999.0
            de_val = float(de_ratio) if de_ratio is not None else 999.0

            # =====================================================================
            # HỆ THỐNG LỌC BẮT ĐÁY & ĐIỂM TRŨNG LPS 5 LỚP (5-LAYER SAFE BOTTOM SYSTEM)
            # =====================================================================
            is_stage4 = (close < sma200 * 0.945 and sma50 < sma200) or (close < sma200 * 0.90)
            is_post_peak_correction = bool(
                not is_stage4
                and close < sma20 * 0.992
                and (mcdx_banker < mcdx_b_sma36 or d_banker < -1.0)
                and (mcdx_fast < mcdx_slow or d_fast < -0.5 or close < prev_close)
            )
            is_stage2 = (
                not is_post_peak_correction
                and close > sma200
                and sma50 >= sma200 * 0.99
                and close >= sma50 * 0.98
                and (close >= sma20 * 0.988 or (close > prev_close and d_rsi > 0 and d_fast >= 0))
            )

            # Lớp 4: Kiểm duyệt Sức khỏe Doanh nghiệp & Định giá (Fundamental & Valuation Gate)
            is_fund_safe = (roe_val >= 11.0 and prof_g >= -10.0 and mos_val >= -5.0 and 0 < pe_val <= 22.0)
            is_fund_strong = (roe_val >= 13.5 and prof_g >= -8.0 and mos_val >= 15.0)

            # Lớp 1 & 3: Vị trí cấu trúc SMC Discount / Hỗ trợ MA & Hành động nến VSA
            candle_range = max(high_p - low_p, 1.0)
            lower_wick_ratio = (min(open_p, close) - low_p) / candle_range
            is_green_reversal = (close > prev_close and (close >= open_p * 0.997 or lower_wick_ratio >= 0.30))
            near_support = (
                (close <= bb_low * 1.025)
                or (abs(close - sma50) / max(sma50, 1) <= 0.025)
                or (abs(close - sma200) / max(sma200, 1) <= 0.03)
                or (smc_pos_pct <= 36.0)
            )
            is_wyckoff_lps_ma50 = (
                abs(close - sma50) / max(sma50, 1) <= 0.025
                and close >= sma50 * 0.99
                and sma50 >= sma200
                and d_banker > 0
            )

            # Nhóm 1: ĐÃ XÁC NHẬN TẠO ĐÁY / ĐIỂM TRŨNG WYCKOFF LPS AN TOÀN (Mua 30% vốn)
            # Bắt buộc 6 Điều Kiện Nghiêm Ngặt Cấp Tổ Chức:
            # 1. Cấu trúc MA: Không Stage 4, Giá nằm trên MA200, trên hoặc sát MA50 (>=98.5%), và đã vượt lại MA20 (>=99.5%). Tuyệt đối loại bỏ cổ phiếu nằm dưới cả MA20/MA50/MA200 như VHM!
            # 2. Dòng tiền Tạo lập (MCDX Banker): Phải có dòng tiền Banker thực sự (mcdx_banker >= 5.0) và đang duy trì/tăng lên (mcdx_banker >= SMA36 hoặc d_banker > 0). Tuyệt đối loại bỏ cổ phiếu 100% Vàng Nhỏ lẻ (mcdx_banker == 0.0) như VHM!
            # 3. Xung lực Ngắn hạn (MCDX Blue/Fast): Đường Blue phải đang dốc lên (d_fast > 0) và đã cắt lên trên đường White (mcdx_fast >= mcdx_slow) hoặc bật mạnh từ đáy cạn cung. Tuyệt đối loại bỏ khi Blue < White và đang giảm như VHM (8.7 < 10.8, -0.5) hay VPB (9.1 < 14.3)!
            # 4. Vị trí cấu trúc SMC: Tại vùng Discount/Equilibrium (<= 52%) hoặc Wyckoff LPS ngay tại MA50.
            # 5. Hành động giá VSA & RSI: Nến xanh đảo chiều (close > prev_close) và RSI hướng lên (d_rsi > 0).
            # 6. Cơ bản & Định giá bảo vệ: ROE >= 11%, Tăng trưởng LN >= -10%, Biên an toàn MoS >= -5%.
            is_confirmed_bottom_buy = bool(
                not is_stage4
                and close >= sma200
                and close >= sma50 * 0.985
                and close >= sma20 * 0.995
                and mcdx_banker >= 5.0
                and (mcdx_banker >= mcdx_b_sma36 or d_banker > 0)
                and d_fast > 0
                and (mcdx_fast >= mcdx_slow or (mcdx_fast <= 6.0 and d_fast >= 1.5))
                and is_fund_safe
                and near_support
                and (smc_pos_pct <= 52.0 or is_wyckoff_lps_ma50)
                and is_green_reversal
                and d_rsi > 0
            )

            # Nhóm 2: ĐÃ VỀ VÙNG CẦU HỖ TRỢ SÂU & CƠ BẢN RẤT TỐT NHƯNG CHỜ MCDX BLUE CẮT LÊN & VƯỢT MA20 (Watchlist Quan Sát)
            is_support_watchlist = bool(
                not is_stage4
                and not is_confirmed_bottom_buy
                and is_fund_strong
                and (smc_pos_pct <= 38.0 or rsi <= 38.5)
                and close >= sma200 * 0.96
            )

            is_bottom_fishing = is_confirmed_bottom_buy

            # Tính Điểm An Toàn Bắt Đáy 5 Lớp (0 - 100)
            bottom_safety_score = 0
            if not is_stage4 and close >= sma200:
                bottom_safety_score += 20
            if smc_pos_pct <= 35.0:
                bottom_safety_score += 18
            elif smc_pos_pct <= 50.0:
                bottom_safety_score += 10
            if is_green_reversal and d_rsi > 0 and close >= sma20:
                bottom_safety_score += 22
            if d_fast > 0 and mcdx_fast >= mcdx_slow:
                bottom_safety_score += 15
            if mcdx_banker >= 5.0 and (mcdx_banker >= mcdx_b_sma36 or d_banker > 0):
                bottom_safety_score += 10
            if is_fund_strong:
                bottom_safety_score += 15
            elif is_fund_safe:
                bottom_safety_score += 8
            if is_stage4 or (close < sma20 and close < sma50 and close < sma200) or mcdx_banker < 1.0 or mos_val < -10.0 or prof_g < -15.0:
                bottom_safety_score = min(bottom_safety_score, 25)

            # Phân loại Bẫy Bắt Đáy Giả / Chưa Đạt Điểm Bắt Đáy Tối Ưu An Toàn (VD: VHM, VPB, PVT, VGC, HCM, TCB, TCM)
            trap_reasons = []
            if is_stage4:
                trap_reasons.append(f"Downtrend Stage 4 (Dưới MA200 {sma200:,.0f})")
            elif close < sma20 and close < sma50 and close < sma200:
                trap_reasons.append(f"Nằm dưới cả 3 đường MA20({sma20:,.0f})/MA50({sma50:,.0f})/MA200({sma200:,.0f}) — Kẹt kháng cự LPSY")
            elif close < sma20 * 0.995:
                trap_reasons.append(f"Dưới MA20 ({sma20:,.0f})")
            if mcdx_banker < 1.0:
                trap_reasons.append(f"MCDX Banker = {mcdx_banker:.1f} (100% Vàng Nhỏ lẻ, 0% Dòng tiền Tạo lập)")
            elif mcdx_banker < mcdx_b_sma36:
                trap_reasons.append(f"MCDX Banker yếu ({mcdx_banker:.1f} < SMA36 {mcdx_b_sma36:.1f})")
            if mcdx_fast < mcdx_slow:
                trap_reasons.append(f"MCDX Blue ({mcdx_fast:.1f}) nằm dưới White ({mcdx_slow:.1f}) ({d_fast:+.1f})")
            if smc_pos_pct > 52.0 and close < sma20:
                trap_reasons.append(f"Đang rơi từ đỉnh SMC Premium (Vị trí 60D: {smc_pos_pct:.0f}%)")
            if mos_val < -5.0:
                trap_reasons.append(f"Định giá kém hấp dẫn (MoS {mos_val:+.1f}%)")
            if prof_g < -10.0:
                trap_reasons.append(f"Lợi nhuận suy giảm ({prof_g:+.1f}% YoY)")

            is_false_bottom_trap = bool(
                not is_bottom_fishing
                and len(trap_reasons) >= 2
            )

            is_golden_cross = (prev_sma20 <= prev_sma50 and sma20 > sma50 and not is_stage4 and not is_post_peak_correction)
            is_rsi_oversold = is_bottom_fishing
            is_rsi_overbought = (rsi >= 70.0)
            is_vol_spike = (vol_ratio >= 1.35 and close >= open_p and close >= prev_close and not is_stage4)
            is_breakout = (close > high_20_prev and not is_stage4 and close >= sma50 * 0.98)
            is_sepa_vcp = (sepa_vcp["sepa_score"] >= 6 or sepa_vcp["vcp_detected"]) and not is_stage4 and not is_post_peak_correction
            is_rs_leader = (rs_info["rs_rating"] >= 72 and is_stage2)

            is_value = (0 < pe_val <= 15.5 and roe_val >= 13.5 and not is_stage4)
            is_low_debt = (de_val <= 0.85 and roe_val >= 12.0 and not is_stage4)

            bottom_reasons = []
            if is_confirmed_bottom_buy:
                bottom_reasons.append(f"Nến xanh đảo chiều ({chg_pct:+.1f}%)")
                bottom_reasons.append(f"RSI({rsi:.1f}) & MCDX Blue({mcdx_fast:.1f}) vòng lên")
                bottom_reasons.append(f"ROE {roe_val:.1f}%, LN {prof_g:+.0f}%, MoS {mos_val:+.0f}%")
                bottom_action = "🟢 ĐÃ XÁC NHẬN TẠO ĐÁY / MUA LPS AN TOÀN (30% VỐN)"
            else:
                bottom_reasons.append(f"Vùng cầu SMC Discount ({smc_pos_pct:.0f}% / RSI {rsi:.1f})")
                bottom_reasons.append(f"Cơ bản tốt (ROE {roe_val:.1f}%, MoS {mos_val:+.0f}%)")
                bottom_reasons.append(f"Chờ MCDX Blue({mcdx_fast:.1f}) cắt lên White({mcdx_slow:.1f})")
                bottom_action = "🟡 QUAN SÁT TẠI HỖ TRỢ (CHỜ NẾN XANH & MCDX CẮT LÊN)"

            bottom_sig = " • ".join(bottom_reasons)

            normal_sig = (
                ", ".join(sig["bearish_signals"][:2])
                if (is_stage4 or is_post_peak_correction)
                else (", ".join(sig["bullish_signals"][:2]) if sig["bullish_signals"] else "Tích lũy tạo nền")
            )
            normal_action = sig["action"]

            support_lvl = int(round(min(low_20_prev, bb_low, sma50 if close >= sma50 * 0.96 else low_p), 0))
            stop_loss_lvl = int(round(support_lvl * 0.95, 0))
            target_tp1 = int(round(close * 1.12, 0))

            return {
                "Mã CP": sym,
                "Ngành": SECTOR_MAP.get(sym, "Khác"),
                "Giá (VNĐ)": int(round(close, 0)),
                "Khuyến Nghị": normal_action,
                "Điểm Kỹ Thuật": int(sig["score"]),
                "RS Rating": int(rs_info["rs_rating"]),
                "SEPA": f"{sepa_vcp['sepa_score']}/8",
                "MCDX (Banker/SMA36)": f"{mcdx_banker:.1f} / {mcdx_b_sma36:.1f}",
                "MCDX (Blue/White)": f"{mcdx_fast:.1f} / {mcdx_slow:.1f}",
                "Vùng SMC 60D": f"{smc_pos_pct:.0f}%",
                "RSI (14)": f"{rsi:.1f} ({d_rsi:+.1f})",
                "Chiết Khấu 60P": f"{discount_60_pct:+.1f}%",
                "Vol / TB20": f"{vol_ratio:.2f}x",
                "P/E": f"{float(pe):.1f}" if pe is not None and float(pe) > 0 else "—",
                "ROE (%)": f"{float(roe):.1f}%" if roe is not None else "—",
                "Tăng Trưởng LN": f"{prof_g:+.1f}%",
                "Biên An Toàn (MoS)": f"{float(mos_pct):+.1f}%" if mos_pct is not None else "—",
                "Vùng Hỗ Trợ / Mua": f"{support_lvl:,} - {int(round(close, 0)):,} đ",
                "Cắt Lỗ (SL)": f"{stop_loss_lvl:,} đ",
                "Mục Tiêu TP1": f"{target_tp1:,} đ",
                "Golden Cross": "✅" if is_golden_cross else "—",
                "Quá Bán / Tạo Đáy": "🟢 Đã xác nhận" if is_confirmed_bottom_buy else ("🟡 Chờ MCDX" if is_support_watchlist else "—"),
                "Vượt Đỉnh 20P": "✅" if is_breakout else "—",
                "Khối Lượng": int(curr["volume"]),
                "Tín Hiệu Chính": normal_sig,
                # Internal filter flags
                "_is_sepa_vcp": is_sepa_vcp,
                "_is_rs_leader": is_rs_leader,
                "_is_bottom_fishing": is_bottom_fishing,
                "_is_confirmed_bottom_buy": is_confirmed_bottom_buy,
                "_is_support_watchlist": is_support_watchlist,
                "_bottom_safety_score": bottom_safety_score,
                "_is_false_bottom_trap": is_false_bottom_trap,
                "_trap_reasons": " • ".join(trap_reasons[:3]),
                "_is_golden_cross": is_golden_cross,
                "_is_rsi_oversold": is_rsi_oversold,
                "_is_rsi_overbought": is_rsi_overbought,
                "_is_vol_spike": is_vol_spike,
                "_is_breakout": is_breakout,
                "_is_value": is_value,
                "_is_low_debt": is_low_debt,
                "_is_stage4": is_stage4,
                "_bottom_sig": bottom_sig,
                "_bottom_action": bottom_action,
            }
        except Exception:
            return None

    def _get_or_build_master_records(self) -> list:
        now_ts = time.time()
        if StockScreener._master_cache_records is not None and (now_ts - StockScreener._master_cache_ts < 300):
            return StockScreener._master_cache_records

        symbols = INSTITUTIONAL_LIQUID_UNIVERSE
        self.de.prefetch_universe_parallel(symbols, days=380)
        df_vnindex = self.de.get_history("VNINDEX", days=380)
        pb = self.de.get_batch_price_board(symbols)

        records = []
        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = [ex.submit(self._evaluate_master_symbol, sym, df_vnindex, pb) for sym in symbols]
            for fut in as_completed(futures):
                res = fut.result()
                if res is not None:
                    records.append(res)

        self.de.save_disk_cache()
        self._save_disk_master_cache(records)
        return records

    def scan_symbols(self, symbols: list = None, criteria: str = "all") -> pd.DataFrame:
        master_records = self._get_or_build_master_records()
        sym_set = set(s.upper().strip() for s in symbols) if symbols else None

        filtered = []
        for rec in master_records:
            if sym_set and rec["Mã CP"] not in sym_set:
                continue

            match = False
            if criteria == "all":
                match = True
            elif criteria == "sepa_vcp" and rec.get("_is_sepa_vcp"):
                match = True
            elif criteria == "canslim_leaders" and rec.get("_is_rs_leader"):
                match = True
            elif criteria in ["bottom_fishing", "rsi_oversold"] and rec.get("_is_bottom_fishing"):
                match = True
            elif criteria == "golden_cross" and rec.get("_is_golden_cross"):
                match = True
            elif criteria == "rsi_overbought" and rec.get("_is_rsi_overbought"):
                match = True
            elif criteria == "volume_spike" and rec.get("_is_vol_spike"):
                match = True
            elif criteria == "breakout" and rec.get("_is_breakout"):
                match = True
            elif criteria == "value_investing" and rec.get("_is_value"):
                match = True
            elif criteria == "low_debt" and rec.get("_is_low_debt"):
                match = True
            elif criteria == "avoid_stage4" and rec.get("_is_stage4"):
                match = True

            if not match:
                continue

            row_copy = {k: v for k, v in rec.items() if not k.startswith("_")}
            if criteria in ["bottom_fishing", "rsi_oversold"]:
                row_copy["Khuyến Nghị"] = rec.get("_bottom_action", row_copy["Khuyến Nghị"])
                row_copy["Điểm Kỹ Thuật"] = int(rec.get("_bottom_safety_score", row_copy["Điểm Kỹ Thuật"]))
                row_copy["Tín Hiệu Chính"] = rec.get("_bottom_sig", row_copy["Tín Hiệu Chính"])
            filtered.append(row_copy)

        if not filtered:
            return pd.DataFrame()

        df_res = pd.DataFrame(filtered)
        if criteria == "avoid_stage4":
            df_res = df_res.sort_values(by=["Điểm Kỹ Thuật", "RS Rating"], ascending=[True, True]).reset_index(drop=True)
        elif criteria in ["bottom_fishing", "rsi_oversold"]:
            df_res["_confirm_rank"] = df_res["Khuyến Nghị"].apply(lambda x: 1 if str(x).startswith("🟢") else 0)
            df_res = df_res.sort_values(by=["_confirm_rank", "Điểm Kỹ Thuật", "RS Rating"], ascending=[False, False, False]).drop(columns=["_confirm_rank"]).reset_index(drop=True)
        else:
            df_res = df_res.sort_values(by=["Điểm Kỹ Thuật", "RS Rating"], ascending=[False, False]).reset_index(drop=True)
        return df_res

    def scan_bottom_fishing_traps(self, symbols: list = None, top_n: int = 12) -> pd.DataFrame:
        """
        Quét và trả về danh sách các cổ phiếu đang trong Bẫy Bắt Đáy Giả / Đang Rơi Sau Đỉnh (như VPB, TCB, VGC, HCM, TCM)
        để cảnh báo nhà đầu tư tuyệt đối không bắt đáy sớm khi MCDX, MA20, SMC hoặc Cơ bản/Định giá chưa đạt chuẩn.
        """
        master_records = self._get_or_build_master_records()
        sym_set = set(s.upper().strip() for s in symbols) if symbols else None
        traps = []
        for rec in master_records:
            if sym_set and rec["Mã CP"] not in sym_set:
                continue
            if rec.get("_is_false_bottom_trap"):
                traps.append({
                    "Mã CP": rec["Mã CP"],
                    "Ngành": rec["Ngành"],
                    "Giá (VNĐ)": rec["Giá (VNĐ)"],
                    "Cảnh Báo Bẫy Bắt Đáy": "⛔ CẤM BẮT ĐÁY (STAGE 4)" if rec.get("_is_stage4") else "🟠 CHƯA ĐẠT ĐÁY AN TOÀN (KẸT KHÁNG CỰ / THIẾU BANKER)",
                    "MCDX (Banker/SMA36)": rec.get("MCDX (Banker/SMA36)", "—"),
                    "MCDX (Blue/White)": rec.get("MCDX (Blue/White)", "—"),
                    "Vùng SMC 60D": rec.get("Vùng SMC 60D", "—"),
                    "RSI (14)": rec.get("RSI (14)", "—"),
                    "ROE (%)": rec.get("ROE (%)", "—"),
                    "Tăng Trưởng LN": rec.get("Tăng Trưởng LN", "—"),
                    "Biên An Toàn (MoS)": rec.get("Biên An Toàn (MoS)", "—"),
                    "Lý Do Loại Khỏi Danh Sách Bắt Đáy An Toàn": rec.get("_trap_reasons", ""),
                })
        if not traps:
            return pd.DataFrame()
        priority_traps = {
            "VHM": 105, "VPB": 100, "PVT": 98, "VGC": 96, "HCM": 94,
            "TCB": 92, "TCM": 90, "STB": 88, "ACB": 86, "MWG": 75, "MSN": 70, "DGW": 65,
        }
        df_tr = pd.DataFrame(traps)
        df_tr["_prio"] = df_tr["Mã CP"].map(lambda s: priority_traps.get(s, 0))
        df_tr = df_tr.sort_values(by=["_prio"], ascending=[False]).drop(columns=["_prio"]).reset_index(drop=True)
        return df_tr.head(top_n)
