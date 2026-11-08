"""
Institutional Technical Analysis & Multi-Indicator Engine for Vietnam Stock Market.
Tính toán đầy đủ hệ thống chỉ báo kỹ thuật chuyên sâu phục vụ phân tích đa khung thời gian và Biểu đồ tùy biến:
- Đường trung bình động: SMA (20, 50, 150, 200), EMA (12, 26, 50), VWAP (20).
- Dải biến động & Cấu trúc: Bollinger Bands (20, 2), Kênh Donchian (High/Low 20), Ichimoku Kinko Hyo (Tenkan 9, Kijun 26, Span A/B 52).
- Động lượng & Dòng tiền: RSI (14), MACD (12, 26, 9), Stochastic (%K 14, %D 3), ADX/DMI (14), MFI (14 - Money Flow Index), OBV (On-Balance Volume), ATR (14).
"""

import pandas as pd
import numpy as np
import ta


class TechnicalAnalysis:
    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        Tính toán toàn bộ các chỉ báo kỹ thuật trên DataFrame OHLCV.
        """
        if df is None or df.empty or len(df) < 5:
            return df

        df = df.copy()

        close = df["close"].astype(float)
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        open_p = df["open"].astype(float)
        volume = df["volume"].astype(float)

        # 1. Simple Moving Averages (SMA 20, 50, 150, 200)
        df["sma_20"] = close.rolling(window=20, min_periods=5).mean()
        df["sma_50"] = close.rolling(window=50, min_periods=10).mean()
        df["sma_150"] = close.rolling(window=150, min_periods=20).mean()
        df["sma_200"] = close.rolling(window=200, min_periods=25).mean()

        # 2. Exponential Moving Averages (EMA 12, 26, 50)
        df["ema_12"] = close.ewm(span=12, adjust=False).mean()
        df["ema_26"] = close.ewm(span=26, adjust=False).mean()
        df["ema_50"] = close.ewm(span=50, adjust=False).mean()

        # 3. Rolling 20-period VWAP
        typ_price = (high + low + close) / 3.0
        tp_vol = (typ_price * volume).rolling(window=20, min_periods=3).sum()
        vol_sum = volume.rolling(window=20, min_periods=3).sum().replace(0, np.nan)
        df["vwap_20"] = tp_vol / vol_sum

        # 4. Relative Strength Index (RSI 14) + RSI SMA 9
        if len(df) >= 15:
            df["rsi"] = ta.momentum.rsi(close, window=14, fillna=False)
            df["rsi_ma9"] = df["rsi"].rolling(window=9, min_periods=3).mean()
        else:
            df["rsi"] = 50.0
            df["rsi_ma9"] = 50.0

        # 5. MACD (12, 26, 9)
        if len(df) >= 26:
            macd = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
            df["macd"] = macd.macd()
            df["macd_signal"] = macd.macd_signal()
            df["macd_diff"] = macd.macd_diff()
        else:
            df["macd"] = 0.0
            df["macd_signal"] = 0.0
            df["macd_diff"] = 0.0

        # 6. Bollinger Bands (20, 2)
        if len(df) >= 20:
            bb = ta.volatility.BollingerBands(close, window=20, window_dev=2)
            df["bb_high"] = bb.bollinger_hband()
            df["bb_mid"] = bb.bollinger_mavg()
            df["bb_low"] = bb.bollinger_lband()
            df["bb_wband"] = bb.bollinger_wband()
        else:
            df["bb_high"] = high
            df["bb_mid"] = close
            df["bb_low"] = low
            df["bb_wband"] = 0.0

        # 7. Ichimoku Kinko Hyo (9, 26, 52)
        high_9 = high.rolling(window=9, min_periods=3).max()
        low_9 = low.rolling(window=9, min_periods=3).min()
        df["ichi_tenkan"] = (high_9 + low_9) / 2.0

        high_26 = high.rolling(window=26, min_periods=5).max()
        low_26 = low.rolling(window=26, min_periods=5).min()
        df["ichi_kijun"] = (high_26 + low_26) / 2.0

        df["ichi_span_a"] = ((df["ichi_tenkan"] + df["ichi_kijun"]) / 2.0).shift(13)
        high_52 = high.rolling(window=52, min_periods=10).max()
        low_52 = low.rolling(window=52, min_periods=10).min()
        df["ichi_span_b"] = ((high_52 + low_52) / 2.0).shift(13)

        # 8. Stochastic Oscillator (%K 14, %D 3)
        if len(df) >= 15:
            stoch = ta.momentum.StochasticOscillator(high=high, low=low, close=close, window=14, smooth_window=3)
            df["stoch_k"] = stoch.stoch()
            df["stoch_d"] = stoch.stoch_signal()
        else:
            df["stoch_k"] = 50.0
            df["stoch_d"] = 50.0

        # 9. ADX & Directional Movement (+DI, -DI, ADX 14)
        if len(df) >= 28:
            try:
                adx_ind = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
                df["adx"] = adx_ind.adx()
                df["di_plus"] = adx_ind.adx_pos()
                df["di_minus"] = adx_ind.adx_neg()
            except Exception:
                df["adx"] = 20.0
                df["di_plus"] = 20.0
                df["di_minus"] = 20.0
        else:
            df["adx"] = 20.0
            df["di_plus"] = 20.0
            df["di_minus"] = 20.0

        # 10. Money Flow Index (MFI 14) & On-Balance Volume (OBV)
        if len(df) >= 15:
            try:
                df["mfi"] = ta.volume.money_flow_index(high=high, low=low, close=close, volume=volume, window=14)
            except Exception:
                df["mfi"] = 50.0
        else:
            df["mfi"] = 50.0

        direction = np.sign(close.diff().fillna(0))
        df["obv"] = (direction * volume).cumsum()
        df["obv_sma20"] = df["obv"].rolling(window=20, min_periods=3).mean()

        # 11. ATR (14) & Volume Ratio & Donchian 20-period High/Low
        if len(df) >= 15:
            df["atr"] = ta.volatility.average_true_range(high, low, close, window=14)
        else:
            df["atr"] = high - low

        df["vol_sma_20"] = volume.rolling(window=20, min_periods=3).mean()
        df["vol_ratio"] = df["volume"] / df["vol_sma_20"].replace(0, np.nan)
        df["high_20"] = high.rolling(window=20, min_periods=5).max()
        df["low_20"] = low.rolling(window=20, min_periods=5).min()

        # 12. Heikin-Ashi Candles
        ha_close = (open_p + high + low + close) / 4.0
        ha_open = np.zeros(len(df))
        ha_open[0] = (open_p.iloc[0] + close.iloc[0]) / 2.0
        for i in range(1, len(df)):
            ha_open[i] = (ha_open[i - 1] + ha_close.iloc[i - 1]) / 2.0
        df["ha_open"] = ha_open
        df["ha_close"] = ha_close
        df["ha_high"] = df[["high", "ha_open", "ha_close"]].max(axis=1)
        df["ha_low"] = df[["low", "ha_open", "ha_close"]].min(axis=1)

        # 13. MCDX RSI SMA [CongTrader] (50, 40, 30, 40, 3.0, 2.5, SMA 36, RSI 6/14)
        if len(df) >= 15:
            try:
                rsi_40 = ta.momentum.rsi(close, window=min(40, max(10, len(df) - 2))).fillna(50.0)
                rsi_6 = ta.momentum.rsi(close, window=6).fillna(50.0)
            except Exception:
                rsi_40 = pd.Series(50.0, index=df.index)
                rsi_6 = pd.Series(50.0, index=df.index)
        else:
            rsi_40 = pd.Series(50.0, index=df.index)
            rsi_6 = pd.Series(50.0, index=df.index)

        df["mcdx_banker"] = np.clip(3.0 * (rsi_40 - 50.0), 0.0, 20.0)
        df["mcdx_banker_sma36"] = df["mcdx_banker"].rolling(window=36, min_periods=5).mean()
        df["mcdx_hot"] = np.clip(2.5 * (rsi_40 - 30.0), 0.0, 20.0)
        df["mcdx_retail"] = np.clip(20.0 - df["mcdx_hot"], 0.0, 20.0)
        df["mcdx_fast"] = np.clip((rsi_6.rolling(window=2, min_periods=1).mean() - 20.0) / 60.0 * 20.0, 0.0, 20.0)
        df["mcdx_slow"] = df["mcdx_fast"].rolling(window=6, min_periods=2).mean()

        # 14. Williams %R (14) & 60-Day SMC Structure (Premium / Equilibrium / Discount)
        hh_14 = high.rolling(window=14, min_periods=3).max()
        ll_14 = low.rolling(window=14, min_periods=3).min()
        denom_14 = (hh_14 - ll_14).replace(0, np.nan)
        df["williams_r"] = ((-100.0 * (hh_14 - close) / denom_14).fillna(-50.0)).clip(-100.0, 0.0)

        df["smc_high_60"] = high.rolling(window=60, min_periods=10).max()
        df["smc_low_60"] = low.rolling(window=60, min_periods=10).min()
        smc_range_60 = (df["smc_high_60"] - df["smc_low_60"]).replace(0, np.nan)
        df["smc_pos_pct"] = (((close - df["smc_low_60"]) / smc_range_60) * 100.0).fillna(50.0).clip(0.0, 100.0)

        # 15. Quantitative VSA/SMC/MCDX Bottom BUY & Top SELL Signals + Wyckoff Tags (LPS / Spring / LPSY)
        prev_close_s = close.shift(1).fillna(close)
        prev_fast_s = df["mcdx_fast"].shift(1).fillna(df["mcdx_fast"])
        prev_slow_s = df["mcdx_slow"].shift(1).fillna(df["mcdx_slow"])
        prev_rsi_s = df["rsi"].shift(1).fillna(df["rsi"])
        prev_banker_s = df["mcdx_banker"].shift(1).fillna(df["mcdx_banker"])

        candle_spread = (high - low).replace(0, np.nan)
        close_loc = ((close - low) / candle_spread).fillna(0.5)

        # Confirmed Bottom BUY signal:
        # Must be in Discount/Lower-Equilibrium (smc_pos_pct <= 48% or RSI <= 40),
        # green reversal candle (close > prev_close and close >= open and close_loc >= 0.52),
        # and momentum turning up (mcdx_fast > prev_fast and rsi > prev_rsi)
        buy_bottom_cond = (
            (df["smc_pos_pct"] <= 48.0)
            & (close > prev_close_s)
            & (close >= open_p)
            & (close_loc >= 0.52)
            & (df["mcdx_fast"] > prev_fast_s)
            & (df["rsi"] > prev_rsi_s)
            & ((prev_fast_s <= 6.5) | (prev_rsi_s <= 42.0) | (low <= df["sma_50"] * 1.015))
        )
        # Filter consecutive duplicate signals within 4 bars
        buy_sig = np.zeros(len(df), dtype=bool)
        last_b = -10
        for idx_i, val_b in enumerate(buy_bottom_cond.values):
            if val_b and (idx_i - last_b >= 4):
                buy_sig[idx_i] = True
                last_b = idx_i
        df["buy_bottom_signal"] = buy_sig

        # Confirmed Top SELL / Distribution signal:
        # In Premium/Upper zone (smc_pos_pct >= 68% or prev_rsi >= 64),
        # red distribution/rejection candle (close < prev_close and close_loc <= 0.48),
        # and MCDX Fast or RSI turning down from high
        sell_top_cond = (
            (df["smc_pos_pct"] >= 65.0)
            & (close < prev_close_s)
            & (close_loc <= 0.48)
            & (df["mcdx_fast"] < prev_fast_s)
            & ((prev_fast_s >= 13.0) | (prev_rsi_s >= 62.0) | (high >= df["smc_high_60"] * 0.985))
        )
        sell_sig = np.zeros(len(df), dtype=bool)
        last_s = -10
        for idx_i, val_s in enumerate(sell_top_cond.values):
            if val_s and (idx_i - last_s >= 4):
                sell_sig[idx_i] = True
                last_s = idx_i
        df["sell_top_signal"] = sell_sig

        # Wyckoff structural tags (LPS vs LPSY)
        wyckoff_tags = [""] * len(df)
        for idx_i in range(2, len(df)):
            if buy_sig[idx_i]:
                wyckoff_tags[idx_i] = "LPS / BUY" if close.iloc[idx_i] >= df["sma_200"].iloc[idx_i] * 0.96 else "SPRING / BUY"
            elif sell_sig[idx_i]:
                wyckoff_tags[idx_i] = "LPSY / SELL"
            elif (
                close.iloc[idx_i] < df["sma_20"].iloc[idx_i]
                and prev_close_s.iloc[idx_i] >= df["sma_20"].iloc[idx_i]
                and df["mcdx_banker"].iloc[idx_i] < df["mcdx_banker_sma36"].iloc[idx_i]
            ):
                wyckoff_tags[idx_i] = "LPSY"
        df["wyckoff_tag"] = wyckoff_tags

        # 16. AFL VPA 5.0 Advanced Modules (Karthikmarar / BinhNT):
        # A. Order Flow Buying Pressure (Lực Cầu) vs Selling Pressure (Lực Cung)
        weights_10 = np.arange(1, 11)
        w_sum_10 = weights_10.sum()
        sp = high - close  # Râu nến trên (áp lực bán)
        bp = close - low   # Râu nến dưới (áp lực mua)
        sp_avg = sp.rolling(10).apply(lambda x: np.dot(x, weights_10) / w_sum_10, raw=True).fillna(sp.rolling(10, min_periods=1).mean()).replace(0, np.nan)
        bp_avg = bp.rolling(10).apply(lambda x: np.dot(x, weights_10) / w_sum_10, raw=True).fillna(bp.rolling(10, min_periods=1).mean()).replace(0, np.nan)
        v_avg10 = volume.rolling(10).apply(lambda x: np.dot(x, weights_10) / w_sum_10, raw=True).fillna(volume.rolling(10, min_periods=1).mean()).replace(0, np.nan)
        nbp = (bp / bp_avg).fillna(1.0)
        nsp = (sp / sp_avg).fillna(1.0)
        nv = (volume / v_avg10).fillna(1.0)
        nbf_raw = nbp * nv
        nsf_raw = nsp * nv
        bf_max = nbf_raw.rolling(60, min_periods=5).max()
        bf_min = nbf_raw.rolling(60, min_periods=5).min()
        nf_max = nsf_raw.rolling(60, min_periods=5).max()
        nf_min = nsf_raw.rolling(60, min_periods=5).min()
        df["buying_pressure"] = (((nbf_raw - bf_min) / (bf_max - bf_min + 1e-9)) * 100.0).fillna(50.0).clip(0.0, 100.0)
        df["selling_pressure"] = (((nsf_raw - nf_min) / (nf_max - nf_min + 1e-9)) * 100.0).fillna(50.0).clip(0.0, 100.0)

        # B. Effort vs Result (Nỗ Lực Khối Lượng vs Kết Quả Bước Giá)
        v_rg40 = volume.rolling(40, min_periods=5).mean().replace(0, np.nan)
        vro = (volume / v_rg40).fillna(1.0)
        vmax40 = vro.rolling(40, min_periods=5).max()
        vmin40 = vro.rolling(40, min_periods=5).min()
        df["effort_score"] = (((vmax40 - vro) / (vmax40 - vmin40 + 1e-9)) * 100.0).fillna(50.0).clip(0.0, 100.0)
        price_res = (close - prev_close_s).abs()
        res_avg40 = price_res.rolling(40, min_periods=5).mean().replace(0, np.nan)
        rso = (price_res / res_avg40).fillna(1.0)
        rmax40 = rso.rolling(40, min_periods=5).max()
        rmin40 = rso.rolling(40, min_periods=5).min()
        df["result_score"] = (((rmax40 - rso) / (rmax40 - rmin40 + 1e-9)) * 100.0).fillna(50.0).clip(0.0, 100.0)

        # C. Keltner Bands System (EMA20 ± 3*ATR)
        df["keltner_mid"] = close.ewm(span=20, adjust=False).mean()
        df["keltner_upper"] = df["keltner_mid"] + 3.0 * df["atr"]
        df["keltner_lower"] = df["keltner_mid"] - 3.0 * df["atr"]

        # D. Turtle Trading System: Chandelier ATR Dynamic Trailing Stop
        df["chand_stop_long"] = high.rolling(20, min_periods=5).max() - 3.0 * df["atr"]
        df["chand_stop_short"] = low.rolling(20, min_periods=5).min() + 3.0 * df["atr"]

        # E. Darvas Box (20-day high / low)
        df["darvas_top"] = high.rolling(20, min_periods=5).max()
        df["darvas_bottom"] = low.rolling(20, min_periods=5).min()

        # F. Ichimoku Vietnam Short-Term System (9, 17, 33, Dao Gam 65 / 129)
        high_17 = high.rolling(17, min_periods=3).max()
        low_17 = low.rolling(17, min_periods=3).min()
        df["ichi_kijun_vn"] = (high_17 + low_17) / 2.0
        df["ichi_span_a_vn"] = ((df["ichi_tenkan"] + df["ichi_kijun_vn"]) / 2.0).shift(13)
        high_33 = high.rolling(33, min_periods=5).max()
        low_33 = low.rolling(33, min_periods=5).min()
        df["ichi_span_b_vn"] = ((high_33 + low_33) / 2.0).shift(13)
        df["ichi_daogam_65"] = (high.rolling(65, min_periods=10).max() + low.rolling(65, min_periods=10).min()) / 2.0
        df["ichi_daogam_129"] = (high.rolling(129, min_periods=20).max() + low.rolling(129, min_periods=20).min()) / 2.0

        # G. VPA Two-Bar Reversals (Đảo chiều 2 thanh có Vol xác nhận)
        prev_c = prev_close_s
        prev_l = low.shift(1).fillna(low)
        prev_h = high.shift(1).fillna(high)
        is_prior_down = (prev_c < close.shift(2)) & (prev_c < close.shift(3)) & (prev_c < close.shift(4))
        is_prior_up = (prev_c > close.shift(2)) & (prev_c > close.shift(3)) & (prev_c > close.shift(4))
        df["vpa_two_bar_bull"] = is_prior_down & (low < prev_l) & (close > prev_c) & (volume > 1.15 * df["vol_sma_20"]) & (close_loc >= 0.65)
        df["vpa_two_bar_bear"] = is_prior_up & (high > prev_h) & (close < prev_c) & (volume > 1.15 * df["vol_sma_20"]) & (close_loc <= 0.35)

        # Provide uppercase aliases for InteractiveChartBuilder
        alias_map = {
            "SMA_20": "sma_20",
            "SMA_50": "sma_50",
            "SMA_150": "sma_150",
            "SMA_200": "sma_200",
            "EMA_12": "ema_12",
            "EMA_26": "ema_26",
            "EMA_50": "ema_50",
            "VWAP_20": "vwap_20",
            "BB_High": "bb_high",
            "BB_Mid": "bb_mid",
            "BB_Low": "bb_low",
            "Ichi_Tenkan": "ichi_tenkan",
            "Ichi_Kijun": "ichi_kijun",
            "Ichi_SpanA": "ichi_span_a",
            "Ichi_SpanB": "ichi_span_b",
            "Ichi_Kijun_VN": "ichi_kijun_vn",
            "Ichi_SpanA_VN": "ichi_span_a_vn",
            "Ichi_SpanB_VN": "ichi_span_b_vn",
            "Ichi_DaoGam_65": "ichi_daogam_65",
            "Ichi_DaoGam_129": "ichi_daogam_129",
            "Keltner_Mid": "keltner_mid",
            "Keltner_Upper": "keltner_upper",
            "Keltner_Lower": "keltner_lower",
            "Chand_Stop_Long": "chand_stop_long",
            "Chand_Stop_Short": "chand_stop_short",
            "Darvas_Top": "darvas_top",
            "Darvas_Bottom": "darvas_bottom",
            "Buying_Pressure": "buying_pressure",
            "Selling_Pressure": "selling_pressure",
            "Effort_Score": "effort_score",
            "Result_Score": "result_score",
            "Donchian_High_20": "high_20",
            "Donchian_Low_20": "low_20",
            "ATR_14": "atr",
            "Vol_SMA_20": "vol_sma_20",
            "RSI_14": "rsi",
            "RSI_MA9": "rsi_ma9",
            "MACD": "macd",
            "MACD_Signal": "macd_signal",
            "MACD_Hist": "macd_diff",
            "Stoch_K": "stoch_k",
            "Stoch_D": "stoch_d",
            "ADX_14": "adx",
            "DI_Plus": "di_plus",
            "DI_Minus": "di_minus",
            "MFI_14": "mfi",
            "OBV": "obv",
            "OBV_SMA20": "obv_sma20",
            "HA_Open": "ha_open",
            "HA_High": "ha_high",
            "HA_Low": "ha_low",
            "HA_Close": "ha_close",
            "MCDX_Banker": "mcdx_banker",
            "MCDX_Banker_SMA36": "mcdx_banker_sma36",
            "MCDX_Hot": "mcdx_hot",
            "MCDX_Retail": "mcdx_retail",
            "MCDX_Fast": "mcdx_fast",
            "MCDX_Slow": "mcdx_slow",
            "Williams_R": "williams_r",
            "SMC_High_60": "smc_high_60",
            "SMC_Low_60": "smc_low_60",
            "SMC_Pos_Pct": "smc_pos_pct",
            "Buy_Bottom_Signal": "buy_bottom_signal",
            "Sell_Top_Signal": "sell_top_signal",
            "Wyckoff_Tag": "wyckoff_tag",
        }
        alias_cols = {
            up_col: df[low_col]
            for up_col, low_col in alias_map.items()
            if low_col in df.columns
        }
        if alias_cols:
            df = pd.concat([df, pd.DataFrame(alias_cols, index=df.index)], axis=1)

        return df.copy()

    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        return TechnicalAnalysis.calculate_indicators(df)

    @staticmethod
    def get_summary_signals(df: pd.DataFrame) -> dict:
        if df is None or df.empty or len(df) < 2:
            return {
                "score": 0,
                "action": "CHƯA ĐỦ DỮ LIỆU",
                "reasons": ["Không đủ dữ liệu lịch sử để phân tích kỹ thuật"],
                "bullish_signals": [],
                "bearish_signals": [],
                "indicators": {}
            }

        curr = df.iloc[-1]
        prev = df.iloc[-2]

        score = 0
        bullish_signals = []
        bearish_signals = []

        close = float(curr["close"])

        # 1. RSI
        rsi_val = float(curr["rsi"]) if pd.notna(curr.get("rsi")) else None
        if rsi_val is not None:
            if rsi_val < 30:
                score += 3
                bullish_signals.append(f"RSI quá bán ({rsi_val:.1f} < 30)")
            elif rsi_val < 45 and rsi_val > float(prev.get("rsi", 0) or 0):
                score += 1
                bullish_signals.append(f"RSI phục hồi từ đáy ({rsi_val:.1f})")
            elif rsi_val > 70:
                score -= 2
                bearish_signals.append(f"RSI quá mua ({rsi_val:.1f} > 70)")
            elif rsi_val > 55:
                score += 1
                bullish_signals.append(f"RSI xung lực khỏe ({rsi_val:.1f})")

        # 2. Moving Average Cross (SMA20 vs SMA50 & Price vs SMA20)
        sma20 = float(curr["sma_20"]) if pd.notna(curr.get("sma_20")) else None
        sma50 = float(curr["sma_50"]) if pd.notna(curr.get("sma_50")) else None
        prev_sma20 = float(prev["sma_20"]) if pd.notna(prev.get("sma_20")) else None
        prev_sma50 = float(prev["sma_50"]) if pd.notna(prev.get("sma_50")) else None

        if sma20 and sma50:
            if prev_sma20 and prev_sma50 and prev_sma20 <= prev_sma50 and sma20 > sma50:
                score += 4
                bullish_signals.append("Golden Cross: SMA20 cắt lên SMA50")
            elif prev_sma20 and prev_sma50 and prev_sma20 >= prev_sma50 and sma20 < sma50:
                score -= 4
                bearish_signals.append("Death Cross: SMA20 cắt xuống SMA50")
            elif sma20 > sma50:
                score += 1
                bullish_signals.append("Xu hướng ngắn hạn tích cực (SMA20 > SMA50)")
            else:
                score -= 1
                bearish_signals.append("Xu hướng ngắn hạn suy yếu (SMA20 < SMA50)")

        if sma20:
            if close > sma20:
                score += 1
                bullish_signals.append(f"Giá nằm trên SMA20 ({sma20:,.0f} đ)")
            else:
                score -= 1
                bearish_signals.append(f"Giá nằm dưới SMA20 ({sma20:,.0f} đ)")

        # 2b. Long-term Trend Filter (SMA200 & Death Cross)
        sma200 = float(curr["sma_200"]) if pd.notna(curr.get("sma_200")) else None
        if sma200:
            if close < sma200 * 0.945:
                score -= 3
                bearish_signals.append(f"Downtrend dài hạn: Giá dưới SMA200 ({sma200:,.0f} đ)")
            elif close >= sma200 * 0.99:
                score += 2
                bullish_signals.append(f"Uptrend dài hạn: Giá giữ trên SMA200 ({sma200:,.0f} đ)")

        if sma50 and sma200:
            if sma50 < sma200 * 0.98 and close < sma200 * 0.945:
                score -= 2
                bearish_signals.append("Stage 4 Downtrend: SMA50 < SMA200")
            elif sma50 >= sma200 * 0.99:
                score += 1
                bullish_signals.append("Stage 2 Uptrend: SMA50 ≥ SMA200")

        # 3. MACD
        macd = float(curr["macd"]) if pd.notna(curr.get("macd")) else None
        macd_sig = float(curr["macd_signal"]) if pd.notna(curr.get("macd_signal")) else None
        prev_macd = float(prev["macd"]) if pd.notna(prev.get("macd")) else None
        prev_macd_sig = float(prev["macd_signal"]) if pd.notna(prev.get("macd_signal")) else None

        if macd is not None and macd_sig is not None:
            if prev_macd and prev_macd_sig and prev_macd <= prev_macd_sig and macd > macd_sig:
                score += 3
                bullish_signals.append("MACD cắt lên Signal (Tín hiệu Mua)")
            elif prev_macd and prev_macd_sig and prev_macd >= prev_macd_sig and macd < macd_sig:
                score -= 3
                bearish_signals.append("MACD cắt xuống Signal (Tín hiệu Bán)")
            elif macd > macd_sig:
                score += 1
                bullish_signals.append("MACD > Signal")
            else:
                score -= 1
                bearish_signals.append("MACD < Signal")

        # 4. Bollinger Bands
        bb_low = float(curr["bb_low"]) if pd.notna(curr.get("bb_low")) else None
        bb_high = float(curr["bb_high"]) if pd.notna(curr.get("bb_high")) else None
        if bb_low and close <= bb_low * 1.01:
            score += 1
            bullish_signals.append(f"Chạm hỗ trợ BB dưới ({bb_low:,.0f} đ)")
        if bb_high and close >= bb_high * 0.99:
            score -= 1
            bearish_signals.append(f"Chạm kháng cự BB trên ({bb_high:,.0f} đ)")

        # 5. Volume Spike
        vol_ratio = float(curr["vol_ratio"]) if pd.notna(curr.get("vol_ratio")) else 1.0
        if vol_ratio >= 1.4:
            if close >= float(curr["open"]) and close >= float(prev.get("close", close)):
                score += 2
                bullish_signals.append(f"Vol bùng nổ ({vol_ratio:.2f}x TB20) kèm nến tăng")
            else:
                score -= 2
                bearish_signals.append(f"Áp lực bán Vol lớn ({vol_ratio:.2f}x TB20)")

        # 5b. MCDX RSI SMA [CongTrader] & SMC Structure Check
        mcdx_banker = float(curr["mcdx_banker"]) if pd.notna(curr.get("mcdx_banker")) else 0.0
        mcdx_b_sma36 = float(curr["mcdx_banker_sma36"]) if pd.notna(curr.get("mcdx_banker_sma36")) else 0.0
        mcdx_fast = float(curr["mcdx_fast"]) if pd.notna(curr.get("mcdx_fast")) else 10.0
        mcdx_slow = float(curr["mcdx_slow"]) if pd.notna(curr.get("mcdx_slow")) else 10.0
        prev_mcdx_fast = float(prev.get("mcdx_fast", mcdx_fast) or mcdx_fast)
        smc_pos_pct = float(curr["smc_pos_pct"]) if pd.notna(curr.get("smc_pos_pct")) else 50.0

        is_post_peak_correction = bool(
            sma20
            and close < sma20 * 0.992
            and mcdx_banker < mcdx_b_sma36
            and (mcdx_fast < mcdx_slow or mcdx_fast < prev_mcdx_fast)
        )
        if is_post_peak_correction:
            score -= 3
            bearish_signals.append(
                f"Cảnh báo gãy MA20 ({sma20:,.0f}) kèm MCDX Banker ({mcdx_banker:.1f} < SMA36 {mcdx_b_sma36:.1f}) & Fast ({mcdx_fast:.1f}) lao dốc"
            )
        elif mcdx_banker >= mcdx_b_sma36 and mcdx_banker >= 8.0 and mcdx_fast >= mcdx_slow:
            score += 2
            bullish_signals.append(
                f"Dòng tiền tạo lập MCDX Banker ({mcdx_banker:.1f} ≥ SMA36 {mcdx_b_sma36:.1f}) & Fast cắt lên Slow"
            )

        # 5c. AFL VPA 5.0 Buying vs Selling Pressure & Two-Bar Reversal
        bp_val = float(curr["buying_pressure"]) if pd.notna(curr.get("buying_pressure")) else 50.0
        sp_val = float(curr["selling_pressure"]) if pd.notna(curr.get("selling_pressure")) else 50.0
        is_tbc_bull = bool(curr.get("vpa_two_bar_bull", False))
        is_tbc_bear = bool(curr.get("vpa_two_bar_bear", False))
        if is_tbc_bull:
            score += 2
            bullish_signals.append("VPA Two-Bar Bullish Reversal: Đảo chiều tăng có Vol xác nhận")
        elif is_tbc_bear:
            score -= 2
            bearish_signals.append("VPA Two-Bar Bearish Reversal: Đảo chiều giảm có Vol xác nhận")
        if bp_val >= 65.0 and bp_val > sp_val * 1.25:
            score += 1
            bullish_signals.append(f"Áp lực Mua (Cầu) áp đảo Cung ({bp_val:.0f}% vs {sp_val:.0f}%)")
        elif sp_val >= 65.0 and sp_val > bp_val * 1.25:
            score -= 1
            bearish_signals.append(f"Áp lực Bán (Cung) áp đảo Cầu ({sp_val:.0f}% vs {bp_val:.0f}%)")

        # 6. Strict Weinstein Stage 4 Downtrend & Post-Peak Correction Override
        is_stage4_downtrend = bool(sma200 and sma50 and ((close < sma200 * 0.945 and sma50 < sma200) or close < sma200 * 0.90))
        if is_stage4_downtrend:
            score = min(score, -5)
            action = "CẤM MUA (STAGE 4 DOWNTREND) ⛔"
            color = "#d50000"
        elif is_post_peak_correction:
            score = min(score, -2)
            action = "ĐANG ĐIỀU CHỈNH SAU ĐỈNH (CHƯA CÓ ĐÁY) 🟠"
            color = "#f97316"
        elif score >= 4 and (not sma200 or close >= sma200 * 0.97) and (not sma20 or close >= sma20 * 0.99):
            action = "MUA MẠNH (STAGE 2) 🚀"
            color = "#00c853"
        elif score >= 2 and (not sma200 or close >= sma200 * 0.95):
            action = "MUA THĂM DÒ 🟢"
            color = "#66bb6a"
        elif score <= -4:
            action = "BÁN / TRÁNH XA 🔻"
            color = "#d50000"
        elif score <= -2:
            action = "HẠ TỶ TRỌNG / CHỜ TẠO ĐÁY 🔴"
            color = "#ef5350"
        else:
            action = "THEO DÕI (HOLD) 🟡"
            color = "#ffa726"

        high_20 = float(curr["high_20"]) if pd.notna(curr.get("high_20")) else close * 1.07
        low_20 = float(curr["low_20"]) if pd.notna(curr.get("low_20")) else close * 0.93

        return {
            "score": score,
            "action": action,
            "color": color,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "support": low_20,
            "resistance": high_20,
            "indicators": {
                "close": close,
                "rsi": rsi_val,
                "sma_20": sma20,
                "sma_50": sma50,
                "sma_200": sma200,
                "macd": macd,
                "macd_signal": macd_sig,
                "vol_ratio": vol_ratio,
                "mcdx_banker": mcdx_banker,
                "mcdx_banker_sma36": mcdx_b_sma36,
                "mcdx_fast": mcdx_fast,
                "mcdx_slow": mcdx_slow,
                "smc_pos_pct": smc_pos_pct,
                "buying_pressure": bp_val,
                "selling_pressure": sp_val,
                "effort_score": float(curr["effort_score"]) if pd.notna(curr.get("effort_score")) else 50.0,
                "result_score": float(curr["result_score"]) if pd.notna(curr.get("result_score")) else 50.0,
            }
        }
