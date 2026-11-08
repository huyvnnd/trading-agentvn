"""
High-Speed Institutional VSA, VPA, SMC, SEPA/VCP & Volume Profile Screener.
Bộ lọc định lượng song song (Multi-threaded) tìm kiếm:
1. Danh sách Siêu Cổ Phiếu Điểm Mua Tổ Chức (Weinstein Stage 2 + Minervini SEPA/VCP + Wyckoff VSA/SMC + Volume Profile POC + RS Rating cao).
2. Danh sách Cổ Phiếu Rủi Ro Cao / Giai đoạn 4 Downtrend / Phân Phối Đỉnh Bắt Buộc Tránh Xa.
"""

import os
import time
import pickle
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from trading_agent.data_engine import DataEngine, SECTOR_MAP
from trading_agent.quant_engine import QuantEngine


INSTITUTIONAL_LIQUID_UNIVERSE = [
    # VN30
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE",
    # BĐS & KCN
    "DIG", "DXG", "PDR", "KBC", "KDH", "NLG", "VGC", "IDC", "SZC",
    # Chứng khoán
    "VND", "VCI", "HCM", "SHS", "MBS", "BSI", "FTS", "CTS", "VIX",
    # Thép, Hóa chất, Dầu khí, Xuất khẩu, Bán lẻ, Cảng biển
    "HSG", "NKG", "DGC", "DCM", "DPM", "PVD", "PVS", "PVT", "BSR",
    "CTR", "FRT", "DGW", "PNJ", "HAH", "GMD", "VHC", "ANV", "TCM", "TNG"
]


class VSASMCScreener:
    _scan_cache = {}  # key -> (ts, df_buy, df_avoid)
    _disk_cache_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "vsa_smc_cache.pkl"))

    def __init__(self, data_engine: DataEngine = None, cio_agent=None):
        self.de = data_engine or DataEngine()
        self._cio_agent = cio_agent
        self._load_disk_cache()

    @property
    def cio_agent(self):
        if self._cio_agent is None:
            from trading_agent.cio_agent import CIOAgent
            self._cio_agent = CIOAgent()
        return self._cio_agent

    @classmethod
    def _load_disk_cache(cls):
        if cls._scan_cache:
            return
        try:
            if os.path.exists(cls._disk_cache_file):
                with open(cls._disk_cache_file, "rb") as f:
                    saved = pickle.load(f)
                now_ts = time.time()
                for k, v in saved.items():
                    if len(v) == 4:
                        ts, df_b, df_w, df_a = v
                        if now_ts - ts < 1800:
                            cls._scan_cache[k] = (ts, df_b, df_w, df_a)
                    elif len(v) == 3:
                        ts, df_b, df_a = v
                        if now_ts - ts < 1800:
                            cls._scan_cache[k] = (ts, df_b, pd.DataFrame(), df_a)
        except Exception:
            pass

    @classmethod
    def _save_disk_cache(cls):
        try:
            os.makedirs(os.path.dirname(cls._disk_cache_file), exist_ok=True)
            with open(cls._disk_cache_file, "wb") as f:
                pickle.dump(cls._scan_cache, f)
        except Exception:
            pass

    def calculate_volume_profile(self, df: pd.DataFrame, num_bins: int = 20) -> dict:
        if df.empty or len(df) < 15:
            return {"poc": 0.0, "vah": 0.0, "val": 0.0}

        min_p = float(df["low"].min())
        max_p = float(df["high"].max())
        if max_p <= min_p:
            return {"poc": min_p, "vah": min_p, "val": min_p}

        bins = np.linspace(min_p, max_p, num_bins + 1)
        bin_volumes = np.zeros(num_bins)
        typ_p = (df["high"] + df["low"] + df["close"]) / 3.0

        for tp, vol in zip(typ_p, df["volume"]):
            idx = min(max(int((float(tp) - min_p) / (max_p - min_p) * num_bins), 0), num_bins - 1)
            bin_volumes[idx] += float(vol)

        max_vol_idx = int(np.argmax(bin_volumes))
        poc_price = (bins[max_vol_idx] + bins[max_vol_idx + 1]) / 2.0

        total_vol = np.sum(bin_volumes)
        target_vol = total_vol * 0.70
        cur_vol = bin_volumes[max_vol_idx]
        low_idx = max_vol_idx
        high_idx = max_vol_idx

        while cur_vol < target_vol and (low_idx > 0 or high_idx < num_bins - 1):
            next_low_vol = bin_volumes[low_idx - 1] if low_idx > 0 else -1
            next_high_vol = bin_volumes[high_idx + 1] if high_idx < num_bins - 1 else -1
            if next_high_vol >= next_low_vol and high_idx < num_bins - 1:
                high_idx += 1
                cur_vol += next_high_vol
            elif low_idx > 0:
                low_idx -= 1
                cur_vol += next_low_vol
            else:
                break

        return {
            "poc": round(float(poc_price), 0),
            "vah": round(float(bins[high_idx + 1]), 0),
            "val": round(float(bins[low_idx]), 0)
        }

    def detect_vsa_vpa_smc_signals(self, df: pd.DataFrame, df_vnindex: pd.DataFrame = None) -> dict:
        if df.empty or len(df) < 35:
            return {"score": 0, "is_downtrend": True, "stage": 4, "signals": [], "warnings": [], "method_details": {}}

        df = df.copy()
        df["spread"] = df["high"] - df["low"]
        df["avg_spread_20"] = df["spread"].rolling(20).mean()
        df["avg_vol_20"] = df["volume"].rolling(20).mean()
        df["vol_ratio"] = df["volume"] / df["avg_vol_20"].replace(0, np.nan)

        vp = self.calculate_volume_profile(df.tail(90))
        poc = vp["poc"]
        vah = vp["vah"]
        val = vp["val"]

        curr = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        close = float(curr["close"])
        open_p = float(curr["open"])
        high = float(curr["high"])
        low = float(curr["low"])
        volume = float(curr["volume"])
        spread = float(curr["spread"])
        avg_spread = float(curr["avg_spread_20"]) if pd.notna(curr["avg_spread_20"]) else spread
        vol_ratio = float(curr["vol_ratio"]) if pd.notna(curr["vol_ratio"]) else 1.0

        sma20 = float(df["close"].rolling(20).mean().iloc[-1])
        sma50 = float(df["close"].rolling(50).mean().iloc[-1]) if len(df) >= 50 else sma20
        sma150 = float(df["close"].rolling(150).mean().iloc[-1]) if len(df) >= 150 else sma50
        sma200 = float(df["close"].rolling(200).mean().iloc[-1]) if len(df) >= 200 else sma150

        # Compute MCDX RSI SMA [CongTrader] & RSI(14) to filter out post-peak breakdown traps (like VPB/TCB)
        delta_c = df["close"].diff()
        gain_14 = delta_c.clip(lower=0).ewm(alpha=1 / 14.0, min_periods=14, adjust=False).mean()
        loss_14 = (-delta_c.clip(upper=0)).ewm(alpha=1 / 14.0, min_periods=14, adjust=False).mean()
        rsi_s = 100.0 - (100.0 / (1.0 + gain_14 / loss_14.replace(0, np.nan)))
        rsi_now = float(rsi_s.iloc[-1]) if pd.notna(rsi_s.iloc[-1]) else 50.0
        rsi_prev = float(rsi_s.iloc[-2]) if len(rsi_s) >= 2 and pd.notna(rsi_s.iloc[-2]) else rsi_now

        w40 = min(40, max(10, len(df) - 2))
        gain_40 = delta_c.clip(lower=0).ewm(alpha=1 / float(w40), min_periods=w40, adjust=False).mean()
        loss_40 = (-delta_c.clip(upper=0)).ewm(alpha=1 / float(w40), min_periods=w40, adjust=False).mean()
        rsi_40_s = (100.0 - (100.0 / (1.0 + gain_40 / loss_40.replace(0, np.nan)))).fillna(50.0)
        banker_s = np.clip(3.0 * (rsi_40_s - 50.0), 0.0, 20.0)
        banker_sma36_s = banker_s.rolling(36, min_periods=5).mean()
        mcdx_banker = float(banker_s.iloc[-1])
        mcdx_b_sma36 = float(banker_sma36_s.iloc[-1]) if pd.notna(banker_sma36_s.iloc[-1]) else 0.0

        gain_6 = delta_c.clip(lower=0).ewm(alpha=1 / 6.0, min_periods=6, adjust=False).mean()
        loss_6 = (-delta_c.clip(upper=0)).ewm(alpha=1 / 6.0, min_periods=6, adjust=False).mean()
        rsi_6_s = (100.0 - (100.0 / (1.0 + gain_6 / loss_6.replace(0, np.nan)))).fillna(50.0)
        fast_s = np.clip((rsi_6_s.rolling(2, min_periods=1).mean() - 20.0) / 60.0 * 20.0, 0.0, 20.0)
        slow_s = fast_s.rolling(6, min_periods=2).mean()
        mcdx_fast = float(fast_s.iloc[-1])
        prev_fast = float(fast_s.iloc[-2]) if len(fast_s) >= 2 else mcdx_fast
        mcdx_slow = float(slow_s.iloc[-1]) if pd.notna(slow_s.iloc[-1]) else 10.0

        prev_close = float(prev["close"])
        is_stage_4 = (close < sma200 * 0.945 and sma50 < sma200) or (close < sma200 * 0.90)
        is_post_peak_correction = bool(
            not is_stage_4
            and close < sma20 * 0.992
            and (mcdx_banker < mcdx_b_sma36 or close < prev_close)
            and (mcdx_fast < mcdx_slow or mcdx_fast < prev_fast or rsi_now < rsi_prev)
        )
        is_stage_2 = (
            not is_post_peak_correction
            and close >= sma200 * 0.99
            and sma50 >= sma200 * 0.99
            and close >= sma50 * 0.98
            and (close >= sma20 * 0.988 or (close > prev_close and rsi_now > rsi_prev and mcdx_fast >= prev_fast))
        )
        stage = 4 if is_stage_4 else (2 if is_stage_2 else (3 if (close < sma50 * 0.96 or is_post_peak_correction) else 1))

        rs_info = QuantEngine.compute_rs_rating(df, df_vnindex)
        sepa_vcp = QuantEngine.evaluate_minervini_sepa_and_vcp(df, rs_rating=rs_info["rs_rating"])

        buy_signals = []
        warnings = []
        score = 0
        method_details = {
            "vsa_signal": "—",
            "vpa_signal": "—",
            "smc_signal": "—",
            "vp_signal": "—",
            "poc": poc,
            "vah": vah,
            "val": val,
            "rs_rating": rs_info["rs_rating"],
            "sepa_score": sepa_vcp["sepa_score"],
            "vcp_detected": sepa_vcp["vcp_detected"],
            "mcdx_banker": round(mcdx_banker, 1),
            "mcdx_banker_sma36": round(mcdx_b_sma36, 1),
            "mcdx_fast": round(mcdx_fast, 1),
            "mcdx_slow": round(mcdx_slow, 1),
            "stage": stage
        }

        # 1. VSA Signals (only valid if not in active post-peak breakdown with red candle)
        if spread <= avg_spread * 0.88 and close >= (low + spread * 0.42) and not is_post_peak_correction:
            if volume < prev["volume"] and vol_ratio <= 0.80:
                score += 28
                buy_signals.append("VSA No Supply / Test Cung Cạn Kiệt 🎯")
                method_details["vsa_signal"] = "No Supply (Cạn Cung)"

        lower_shadow = min(open_p, close) - low
        if lower_shadow >= spread * 0.38 and vol_ratio >= 1.35 and close >= open_p:
            score += 25
            buy_signals.append(f"VSA Stopping Volume (Hấp thụ Vol {vol_ratio:.1f}x) 🌊")
            method_details["vsa_signal"] = "Stopping Volume"

        min_low_prev = float(df["low"].iloc[-20:-1].min()) if len(df) >= 20 else low
        if low < min_low_prev and close > min_low_prev and close > prev_close:
            score += 32
            buy_signals.append("VSA Wyckoff Spring (Rũ Bỏ Rút Chân) 🚀")
            method_details["vsa_signal"] = "Wyckoff Spring"

        # 2. VPA Signals
        body = close - open_p
        chg_pct = (close - prev_close) / prev_close * 100.0 if prev_close > 0 else 0.0
        if body >= spread * 0.50 and chg_pct >= 1.8 and vol_ratio >= 1.3:
            score += 30
            buy_signals.append(f"VPA Effort vs Result (+{chg_pct:.1f}%, Vol {vol_ratio:.1f}x) ⚡")
            method_details["vpa_signal"] = "Effort vs Result"
        elif -1.2 <= chg_pct <= 0.8 and vol_ratio <= 0.78 and close >= sma20 * 0.99 and not is_post_peak_correction:
            score += 22
            buy_signals.append(f"VPA Low-Vol Pullback trên MA20 (Vol {vol_ratio:.2f}x TB20) 🟢")
            method_details["vpa_signal"] = "Pullback Cạn Vol"

        # 3. SMC & SEPA VCP Signals
        high_20_prev = float(df["high"].iloc[-20:-1].max()) if len(df) >= 20 else high
        if close > high_20_prev:
            score += 32
            buy_signals.append("SMC Break of Structure (BOS Vượt Đỉnh 20P) 📈")
            method_details["smc_signal"] = "BOS Vượt Đỉnh"
        elif close >= sma20 and low <= sma20 * 1.02:
            score += 24
            buy_signals.append(f"SMC Bullish Order Block Retest ({sma20:,.0f} đ) 🛡️")
            method_details["smc_signal"] = "Order Block Retest"

        if sepa_vcp["vcp_detected"]:
            score += 25
            buy_signals.append(f"Minervini VCP Contraction ({sepa_vcp['vcp_contractions']}%) 🔥")
            if method_details["smc_signal"] == "—":
                method_details["smc_signal"] = "VCP Tight Base"

        # 4. Volume Profile Confluence
        if poc > 0:
            if close >= poc and float(prev["close"]) < poc:
                score += 22
                buy_signals.append(f"Volume Profile POC Breakout ({poc:,.0f} đ) 💎")
                method_details["vp_signal"] = "POC Breakout"
            elif close >= poc:
                score += 14
                method_details["vp_signal"] = "Giữ Trên POC"

        # Bonus for High RS & Stage 2 Alignment
        if stage == 2:
            score += 20
        elif stage == 1:
            score += 10
        if rs_info["rs_rating"] >= 68:
            score += 12

        # STRICT STAGE 4 / DOWNTREND & POST-PEAK CORRECTION VETO
        is_downtrend = (stage == 4)
        if is_downtrend:
            score = 0
            warnings.append(f"⛔ Giai đoạn 4 Downtrend: Giá ({close:,.0f} đ) nằm dưới SMA200 ({sma200:,.0f} đ) & SMA50 ({sma50:,.0f} đ)")
        elif is_post_peak_correction:
            score = min(score, 35)
            warnings.append(
                f"⚠️ Đang điều chỉnh sau đỉnh: Gãy dưới SMA20 ({sma20:,.0f} đ) kèm MCDX Banker ({mcdx_banker:.1f} < SMA36 {mcdx_b_sma36:.1f}) & Fast ({mcdx_fast:.1f}) lao dốc — Chưa có đáy an toàn"
            )
        elif close < sma50 * 0.96:
            score = max(0, score - 30)
            warnings.append(f"⚠️ Gãy dưới SMA50 ({sma50:,.0f} đ) - Suy yếu ngắn hạn")

        final_score = max(0, min(score, 100))

        swing_low = float(df["low"].tail(15).min())
        stop_loss = max(swing_low * 0.985, close * 0.93)
        risk = close - stop_loss
        if risk <= 0:
            risk = close * 0.05
            stop_loss = close * 0.95

        tp1 = close + (risk * 2.5)
        tp2 = close + (risk * 3.5)

        return {
            "score": final_score,
            "is_downtrend": is_downtrend,
            "stage": stage,
            "signals": buy_signals,
            "warnings": warnings,
            "method_details": method_details,
            "sma50": sma50,
            "sma200": sma200,
            "trade_plan": {
                "entry_zone": f"{close * 0.985:,.0f} - {close:,.0f} VNĐ" if not is_downtrend else "CẤM MUA BẮT ĐÁY",
                "stop_loss": stop_loss,
                "stop_loss_pct": round(((stop_loss - close) / close) * 100.0, 1),
                "take_profit_1": tp1,
                "target_1_pct": round(((tp1 - close) / close) * 100.0, 1),
                "take_profit_2": tp2,
                "target_2_pct": round(((tp2 - close) / close) * 100.0, 1),
                "rr_ratio": 2.5
            }
        }

    def _run_full_universe_scan(self, symbols: list = None) -> tuple:
        if symbols is None or len(symbols) == 0:
            symbols = INSTITUTIONAL_LIQUID_UNIVERSE
        key = tuple(sorted(symbols))
        now_ts = time.time()
        if key in VSASMCScreener._scan_cache:
            cached_item = VSASMCScreener._scan_cache[key]
            if len(cached_item) == 4:
                ts, df_buy, df_watchlist, df_avoid = cached_item
                if now_ts - ts < 600:
                    return df_buy.copy(), df_watchlist.copy(), df_avoid.copy()

        # Parallel prefetch of price board + history
        self.de.prefetch_universe_parallel(symbols, days=380)
        df_vnindex = self.de.get_history("VNINDEX", days=380)
        pb = self.de.get_batch_price_board(symbols)

        buy_rows = []
        watchlist_rows = []
        avoid_rows = []

        for sym in symbols:
            try:
                df = self.de.get_history(sym, days=380)
                if df.empty or len(df) < 35:
                    continue

                avg_vol = float(df["volume"].tail(20).mean())
                close_p = float(pb.get(sym, {}).get("price", df["close"].iloc[-1]))
                if close_p <= 0:
                    close_p = float(df["close"].iloc[-1])
                avg_val_vnd = avg_vol * close_p
                f_net = int(pb.get(sym, {}).get("foreign_net_volume", 0))

                det = self.detect_vsa_vpa_smc_signals(df, df_vnindex=df_vnindex)
                m = det["method_details"]
                tp = det["trade_plan"]

                # 1. NHÓM 3: Giai đoạn 4 Downtrend & Bị Phủ Quyết Rủi Ro Cao (Tránh xa 100%)
                if det["is_downtrend"] or det["stage"] == 4 or close_p < 7000 or avg_val_vnd < 2_000_000_000:
                    reason = det["warnings"][0] if det["warnings"] else "Downtrend Giai đoạn 4 / Rủi ro cao"
                    avoid_rows.append({
                        "Mã CP": sym,
                        "Ngành": SECTOR_MAP.get(sym, "Khác"),
                        "Giá (VNĐ)": close_p,
                        "Giai Đoạn": f"Stage {det['stage']} (Downtrend)",
                        "RS Rating": m.get("rs_rating", 20),
                        "SEPA": f"{m.get('sepa_score', 0)}/8",
                        "SMA50 (đ)": round(det["sma50"], 0),
                        "SMA200 (đ)": round(det["sma200"], 0),
                        "Giá Vốn POC": f"{m['poc']:,.0f} đ",
                        "Lý Do Cấm Mua": reason
                    })

                # 2. NHÓM 1: Chuẩn Điểm Mua Tổ Chức Giai Đoạn 2 (Stage 2 Uptrend & SEPA ≥ 5/8 & RS ≥ 65 & Xung lực dòng tiền đồng thuận)
                elif (
                    det["stage"] == 2
                    and (m.get("sepa_score", 0) >= 5 or m.get("vcp_detected", False))
                    and m.get("rs_rating", 0) >= 65
                    and close_p >= det["sma200"]
                    and close_p >= det["sma50"] * 0.98
                    and det["score"] >= 35
                ):
                    # BẮT BUỘC RÀ SOÁT CHÉO ĐA PHÒNG BAN VỚI HỘI ĐỒNG CIO (ĐỊNH GIÁ & 9 KIỆN TƯỚNG & VCP):
                    cross_audit = self.cio_agent.cross_audit_departmental_consensus(sym)
                    if cross_audit.get("is_buy_approved", False):
                        buy_rows.append({
                            "Mã CP": sym,
                            "Ngành": SECTOR_MAP.get(sym, "Khác"),
                            "Giá (VNĐ)": close_p,
                            "Điểm Smart Money": det["score"],
                            "Giai Đoạn": f"Stage {det['stage']} (Uptrend)",
                            "RS Rating": m.get("rs_rating", 50),
                            "SEPA": f"{m.get('sepa_score', 0)}/8",
                            "Tín Hiệu VSA": m["vsa_signal"],
                            "Tín Hiệu VPA": m["vpa_signal"],
                            "Tín Hiệu SMC": m["smc_signal"],
                            "Giá Vốn POC": f"{m['poc']:,.0f} đ",
                            "Khối Ngoại Ròng": f_net,
                            "Vùng Mua An Toàn": tp["entry_zone"],
                            "Cắt Lỗ Cấu Trúc": f"{tp['stop_loss']:,.0f} đ ({tp['stop_loss_pct']}%)",
                            "Mục Tiêu TP1 (+R:R 2.5)": f"{tp['take_profit_1']:,.0f} đ (+{tp['target_1_pct']}%)",
                            "Chi Tiết Tín Hiệu": " | ".join(det["signals"][:3]) if det["signals"] else "Tích lũy kênh trên quanh POC"
                        })
                    else:
                        # BỊ VETO TỪ MA TRẬN RÀ SOÁT CHÉO (ĐỊNH GIÁ CAO HOẶC HỘI ĐỒNG BẤT ĐỒNG) -> CHUYỂN NGAY SANG WATCHLIST
                        stage_lbl = f"Stage {det['stage']} (Chờ Bứt Phá)"
                        status_desc = f"🟡 {cross_audit['summary']}"
                        trigger_cond = f"Vượt cản Pivot ({tp.get('pivot_breakout', m['poc']):,.0f} đ) + Hội đồng Đồng thuận"
                        watchlist_rows.append({
                            "Mã CP": sym,
                            "Ngành": SECTOR_MAP.get(sym, "Khác"),
                            "Giá (VNĐ)": close_p,
                            "Điểm Smart Money": det["score"],
                            "Giai Đoạn": stage_lbl,
                            "RS Rating": m.get("rs_rating", 50),
                            "SEPA": f"{m.get('sepa_score', 0)}/8",
                            "Tín Hiệu VSA": m["vsa_signal"],
                            "Tín Hiệu SMC": m["smc_signal"],
                            "Giá Vốn POC": f"{m['poc']:,.0f} đ",
                            "Khối Ngoại Ròng": f_net,
                            "Trạng Thái Theo Dõi": status_desc,
                            "Điều Kiện Kích Hoạt Mua": trigger_cond,
                            "Khuyến Nghị Hội Đồng": cross_audit["verdict"]
                        })

                # 3. NHÓM 2: Danh Mục Theo Dõi Quan Sát (Stage 1 Tích Lũy / Chờ Bứt Phá Pivot & SEPA - VD: NKG, TPB, VJC)
                else:
                    stage_lbl = f"Stage {det['stage']} (Tích Lũy Nền Giá)" if det["stage"] == 1 else f"Stage {det['stage']} (Chờ Bứt Phá)"
                    status_desc = "🟡 Tích lũy Stage 1 quanh POC — Chờ bứt phá Stage 2" if det["stage"] == 1 else "🟡 Tích lũy cạn cung — Chờ xác nhận vượt Pivot"
                    trigger_cond = f"Vượt cản POC ({m['poc']:,.0f} đ) + SEPA ≥ 5/8 + Vol ≥ 1.35x TB20"
                    watchlist_rows.append({
                        "Mã CP": sym,
                        "Ngành": SECTOR_MAP.get(sym, "Khác"),
                        "Giá (VNĐ)": close_p,
                        "Điểm Smart Money": det["score"],
                        "Giai Đoạn": stage_lbl,
                        "RS Rating": m.get("rs_rating", 50),
                        "SEPA": f"{m.get('sepa_score', 0)}/8",
                        "Tín Hiệu VSA": m["vsa_signal"],
                        "Tín Hiệu SMC": m["smc_signal"],
                        "Giá Vốn POC": f"{m['poc']:,.0f} đ",
                        "Khối Ngoại Ròng": f_net,
                        "Trạng Thái Theo Dõi": status_desc,
                        "Điều Kiện Kích Hoạt Mua": trigger_cond,
                        "Khuyến Nghị Hội Đồng": "TẠM DỪNG / THEO DÕI QUAN SÁT (0% NAV)"
                    })
            except Exception:
                continue

        df_buy = pd.DataFrame(buy_rows)
        if not df_buy.empty:
            df_buy = df_buy.sort_values(by=["Điểm Smart Money", "RS Rating"], ascending=[False, False]).reset_index(drop=True)

        df_watchlist = pd.DataFrame(watchlist_rows)
        if not df_watchlist.empty:
            # Ưu tiên các mã có điểm Smart Money cao và Stage 1/2 tích lũy tích cực lên đầu
            df_watchlist = df_watchlist.sort_values(by=["Điểm Smart Money", "RS Rating"], ascending=[False, False]).reset_index(drop=True)

        df_avoid = pd.DataFrame(avoid_rows)
        if not df_avoid.empty:
            df_avoid = df_avoid.sort_values(by="RS Rating", ascending=True).reset_index(drop=True)

        VSASMCScreener._scan_cache[key] = (now_ts, df_buy, df_watchlist, df_avoid)
        self._save_disk_cache()
        return df_buy.copy(), df_watchlist.copy(), df_avoid.copy()

    def scan_three_tier_universe(self, symbols: list = None) -> tuple:
        """Trả về đầy đủ 3 nhóm: (df_buy_stage2, df_watchlist_stage1, df_avoid_stage4)."""
        return self._run_full_universe_scan(symbols)

    def scan_vsa_smc_universe(self, symbols: list = None, min_score: int = 35) -> pd.DataFrame:
        """Chỉ trả về các cổ phiếu đạt chuẩn Giai đoạn 2 (Stage 2) & SEPA ≥ 5/8 được Hội đồng phê duyệt."""
        df_buy, _, _ = self._run_full_universe_scan(symbols)
        if df_buy.empty:
            return df_buy
        filtered = df_buy[df_buy["Điểm Smart Money"] >= min_score].reset_index(drop=True)
        return filtered if not filtered.empty else df_buy

    def scan_watchlist_universe(self, symbols: list = None) -> pd.DataFrame:
        """Trả về danh mục cổ phiếu tích lũy Giai đoạn 1 hoặc chờ điểm nổ Pivot (VD: NKG, TPB, VJC)."""
        _, df_watchlist, _ = self._run_full_universe_scan(symbols)
        return df_watchlist

    def scan_danger_stocks_to_avoid(self, symbols: list = None) -> pd.DataFrame:
        """Trả về danh sách các cổ phiếu đang ở Giai đoạn 4 Downtrend / Gãy cấu trúc cần tuyệt đối tránh xa."""
        _, _, df_avoid = self._run_full_universe_scan(symbols)
        return df_avoid
