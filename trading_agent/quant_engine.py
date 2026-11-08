"""
Unified Institutional Quantitative & Multi-Persona Engine.
Tổng hợp tinh hoa định lượng và học thuật từ 8 dự án mã nguồn mở hàng đầu:
1. tradermonty/claude-trading-skills: Mark Minervini 8-Point SEPA Trend Template, VCP Contraction Detector, Stan Weinstein Stage 1-4, William O'Neil CANSLIM (0-100) & RS Rating (1-99).
2. AI4Finance-Foundation/FinRL: Sharpe Ratio, Sortino Ratio, Calmar Ratio, Max Drawdown, Mahalanobis Turbulence, Half-Kelly & Volatility-Targeted Lot-100 Position Sizing (T+2.5 adjusted).
3. AI4Finance-Foundation/FinRobot: 3-Step DuPont Decomposition, Earnings Quality / Cash Flow Forensics, Sector-Adapted Valuation Football Field.
4. virattt/ai-hedge-fund: Hội đồng 9 Đại Kiện Tướng Đầu Tư (Buffett, Munger, Graham, Lynch, Druckenmiller, Burry, Cathie Wood, Ackman, Damodaran).
"""

import math
import numpy as np
import pandas as pd


class QuantEngine:
    # Tham số chuẩn thị trường Việt Nam (NHNN & HOSE)
    VN_RISK_FREE_RATE = 0.045   # Lãi suất phi rủi ro tham chiếu (Trái phiếu CP 10Y / Tiền gửi kỳ hạn ~4.5%)
    VN_ERP = 0.065              # Phần bù rủi ro vốn cổ phần Việt Nam (Equity Risk Premium ~6.5%)
    TRADING_DAYS = 252

    @classmethod
    def compute_rs_rating(cls, df_stock: pd.DataFrame, df_vnindex: pd.DataFrame) -> dict:
        """
        Tính chỉ số Sức Mạnh Giá Tương Đối (William O'Neil Relative Strength - RS Rating 1..99)
        so với chỉ số chuẩn VN-INDEX theo công thức trọng số:
        RS_Raw = 0.40 * Ret_3M + 0.20 * Ret_6M + 0.20 * Ret_9M + 0.20 * Ret_12M
        """
        if df_stock is None or df_stock.empty or len(df_stock) < 25:
            return {"rs_rating": 50, "rs_raw_stock": 0.0, "rs_raw_index": 0.0, "outperformance_pct": 0.0, "rs_line_new_high": False}

        closes = df_stock["close"].values
        curr = float(closes[-1])

        def _ret(arr, bars):
            if len(arr) <= bars:
                prev = float(arr[0])
            else:
                prev = float(arr[-bars - 1])
            return (( arr[-1] - prev) / prev * 100.0) if prev > 0 else 0.0

        r_1m = _ret(closes, 21)
        r_3m = _ret(closes, 63)
        r_6m = _ret(closes, 126)
        r_9m = _ret(closes, 189)
        r_12m = _ret(closes, 252)

        rs_stock = 0.40 * r_3m + 0.20 * r_6m + 0.20 * r_9m + 0.20 * r_12m

        rs_idx = 0.0
        rs_line_new_high = False
        if df_vnindex is not None and not df_vnindex.empty and len(df_vnindex) >= 25:
            idx_c = df_vnindex["close"].values
            ir_3m = _ret(idx_c, 63)
            ir_6m = _ret(idx_c, 126)
            ir_9m = _ret(idx_c, 189)
            ir_12m = _ret(idx_c, 252)
            rs_idx = 0.40 * ir_3m + 0.20 * ir_6m + 0.20 * ir_9m + 0.20 * ir_12m

            # Check if RS line (Stock / VNINDEX) is at a 60-day high
            min_len = min(len(closes), len(idx_c), 120)
            if min_len >= 30:
                rs_curve = closes[-min_len:] / np.maximum(idx_c[-min_len:], 1.0)
                if rs_curve[-1] >= np.max(rs_curve[:-1]) * 0.995:
                    rs_line_new_high = True

        alpha = rs_stock - rs_idx
        # Map relative alpha (-40% .. +50%) smoothly onto O'Neil 1..99 percentile scale
        raw_score = 55.0 + alpha * 1.15
        rs_rating = int(max(1, min(99, round(raw_score))))

        return {
            "rs_rating": rs_rating,
            "rs_raw_stock": round(rs_stock, 2),
            "rs_raw_index": round(rs_idx, 2),
            "outperformance_pct": round(alpha, 2),
            "ret_1m": round(r_1m, 2),
            "ret_3m": round(r_3m, 2),
            "ret_6m": round(r_6m, 2),
            "ret_12m": round(r_12m, 2),
            "rs_line_new_high": rs_line_new_high
        }

    @classmethod
    def evaluate_minervini_sepa_and_vcp(cls, df_daily: pd.DataFrame, rs_rating: int = 50) -> dict:
        """
        Đánh giá Bộ Khuôn Mẫu Xu Hướng 8 Tiêu Chí của Mark Minervini (SEPA Trend Template)
        và Thuật toán Nhận diện Mẫu hình Thu Hẹp Độ Biến Động VCP (Volatility Contraction Pattern).
        """
        if df_daily is None or df_daily.empty or len(df_daily) < 50:
            return {
                "sepa_score": 0,
                "sepa_max": 8,
                "sepa_passed": False,
                "criteria": [],
                "vcp_detected": False,
                "vcp_contractions": [],
                "vdu_detected": False,
                "pivot_price": 0.0
            }

        closes = df_daily["close"]
        highs = df_daily["high"]
        lows = df_daily["low"]
        vols = df_daily["volume"]

        curr_p = float(closes.iloc[-1])
        sma50 = float(closes.rolling(50).mean().iloc[-1])
        sma150 = float(closes.rolling(150).mean().iloc[-1]) if len(closes) >= 150 else float(closes.rolling(min(len(closes), 100)).mean().iloc[-1])
        sma200_series = closes.rolling(200).mean() if len(closes) >= 200 else closes.rolling(min(len(closes), 120)).mean()
        sma200 = float(sma200_series.iloc[-1])
        sma200_20d_ago = float(sma200_series.iloc[-21]) if len(sma200_series) > 21 and pd.notna(sma200_series.iloc[-21]) else sma200

        window_52w = df_daily.tail(252)
        high_52w = float(window_52w["high"].max())
        low_52w = float(window_52w["low"].min())

        pct_above_52w_low = ((curr_p - low_52w) / low_52w * 100.0) if low_52w > 0 else 0.0
        pct_below_52w_high = ((high_52w - curr_p) / high_52w * 100.0) if high_52w > 0 else 0.0

        c1 = curr_p > sma150 and curr_p > sma200
        c2 = sma150 > sma200
        c3 = sma200 > sma200_20d_ago
        c4 = sma50 > sma150 and sma50 > sma200
        c5 = curr_p > sma50
        c6 = pct_above_52w_low >= 25.0   # Adapted for HOSE ±7% band (≥25% above 52W low)
        c7 = pct_below_52w_high <= 25.0  # Within 25% of 52W high
        c8 = rs_rating >= 70

        criteria = [
            {"id": 1, "name": "Giá > SMA150 & SMA200", "passed": c1, "detail": f"Giá {curr_p:,.0f} vs SMA150 ({sma150:,.0f}), SMA200 ({sma200:,.0f})"},
            {"id": 2, "name": "SMA150 > SMA200", "passed": c2, "detail": f"SMA150 ({sma150:,.0f}) vs SMA200 ({sma200:,.0f})"},
            {"id": 3, "name": "SMA200 dốc lên ≥ 1 tháng", "passed": c3, "detail": f"SMA200 hiện tại {sma200:,.0f} vs 20 phiên trước {sma200_20d_ago:,.0f}"},
            {"id": 4, "name": "SMA50 > SMA150 & SMA200", "passed": c4, "detail": f"SMA50 ({sma50:,.0f}) nằm trên SMA150 & SMA200"},
            {"id": 5, "name": "Giá > SMA50", "passed": c5, "detail": f"Giá {curr_p:,.0f} vs SMA50 ({sma50:,.0f})"},
            {"id": 6, "name": "Giá ≥ +25% từ Đáy 52 Tuần", "passed": c6, "detail": f"+{pct_above_52w_low:.1f}% từ đáy 52W ({low_52w:,.0f})"},
            {"id": 7, "name": "Giá cách Đỉnh 52 Tuần ≤ 25%", "passed": c7, "detail": f"-{pct_below_52w_high:.1f}% từ đỉnh 52W ({high_52w:,.0f})"},
            {"id": 8, "name": "RS Rating ≥ 70 (Cổ phiếu dẫn dắt)", "passed": c8, "detail": f"RS Rating = {rs_rating}/99"}
        ]
        sepa_score = sum(1 for item in criteria if item["passed"])

        # --- VCP (Volatility Contraction Pattern) Detection ---
        # Compare 3 sequential 15-bar windows (T1: -45..-31, T2: -30..-16, T3: -15..-1)
        vcp_contractions = []
        vcp_detected = False
        vdu_detected = False
        pivot_price = float(highs.tail(20).max())

        if len(df_daily) >= 45:
            w1 = df_daily.iloc[-45:-30]
            w2 = df_daily.iloc[-30:-15]
            w3 = df_daily.iloc[-15:]

            r1 = (w1["high"].max() - w1["low"].min()) / max(w1["high"].max(), 1) * 100.0
            r2 = (w2["high"].max() - w2["low"].min()) / max(w2["high"].max(), 1) * 100.0
            r3 = (w3["high"].max() - w3["low"].min()) / max(w3["high"].max(), 1) * 100.0
            vcp_contractions = [round(r1, 1), round(r2, 1), round(r3, 1)]

            vol_5d = float(vols.tail(5).mean())
            vol_50d = float(vols.tail(50).mean())
            vdu_detected = vol_5d < (vol_50d * 0.75)

            # VCP hợp chuẩn Minervini: Biên độ co hẹp dần qua các nhịp (r1 >= r2 >= r3) với nhịp cuối cùng nén rất chặt (r3 <= 8.5%)
            is_valid_contraction = (r1 >= r2 * 0.92 and r2 >= r3 * 0.92) and r3 <= 8.5
            if is_valid_contraction and curr_p >= sma50 * 0.97 and curr_p > sma200:
                vcp_detected = True

        return {
            "sepa_score": sepa_score,
            "sepa_max": 8,
            "sepa_passed": sepa_score >= 6,
            "criteria": criteria,
            "vcp_detected": vcp_detected,
            "vcp_contractions": vcp_contractions,
            "vdu_detected": vdu_detected,
            "pivot_price": pivot_price,
            "high_52w": high_52w,
            "low_52w": low_52w,
            "pct_above_52w_low": round(pct_above_52w_low, 1),
            "pct_below_52w_high": round(pct_below_52w_high, 1)
        }

    @classmethod
    def evaluate_canslim_score(cls, fund_info: dict, sepa_info: dict, rs_info: dict, df_daily: pd.DataFrame) -> dict:
        """
        Tính điểm CANSLIM (0 - 100 điểm) của William O'Neil:
        - C (Current Quarterly Earnings Growth YoY): 20 điểm
        - A (Annual ROE & Profitability): 20 điểm
        - N (New Highs / Catalyst - khoảng cách tới đỉnh 52W): 15 điểm
        - S (Supply & Demand - Tỷ lệ phiên Mua gom / Phân phối 20 phiên): 15 điểm
        - L (Leader vs Laggard - RS Rating): 15 điểm
        - I (Institutional Sponsorship - Thanh khoản tổ chức & Khối ngoại): 15 điểm
        """
        c_score = 0
        a_score = 0
        n_score = 0
        s_score = 0
        l_score = 0
        i_score = 0

        # C: Current Quarterly Profit Growth YoY
        p_growth = fund_info.get("profit_growth_yoy")
        r_growth = fund_info.get("revenue_growth_yoy")
        if p_growth is not None:
            if p_growth >= 25.0:
                c_score = 20
            elif p_growth >= 15.0:
                c_score = 16
            elif p_growth >= 5.0:
                c_score = 10
            elif p_growth >= 0.0:
                c_score = 5
            else:
                c_score = 0
        elif r_growth is not None and r_growth >= 15.0:
            c_score = 12
        else:
            c_score = 6

        # A: Annual ROE & Operating Margins
        roe = fund_info.get("roe")
        if roe is not None:
            if roe >= 20.0:
                a_score = 20
            elif roe >= 15.0:
                a_score = 16
            elif roe >= 10.0:
                a_score = 10
            elif roe > 0:
                a_score = 4
            else:
                a_score = 0
        else:
            a_score = 6

        # N: Distance to 52-Week High & VCP Pivot
        pct_below_high = sepa_info.get("pct_below_52w_high", 50.0)
        if pct_below_high <= 10.0:
            n_score = 15
        elif pct_below_high <= 20.0:
            n_score = 12
        elif pct_below_high <= 30.0:
            n_score = 7
        else:
            n_score = 2

        # S: Supply/Demand Up/Down Volume Ratio over last 20 sessions
        up_down_vol_ratio = 1.0
        if df_daily is not None and len(df_daily) >= 21:
            recent = df_daily.tail(21).copy()
            recent["chg"] = recent["close"].diff()
            up_vol = recent.loc[recent["chg"] > 0, "volume"].sum()
            dn_vol = recent.loc[recent["chg"] < 0, "volume"].sum()
            up_down_vol_ratio = round(float(up_vol / max(dn_vol, 1.0)), 2)
            if up_down_vol_ratio >= 1.4:
                s_score = 15
            elif up_down_vol_ratio >= 1.1:
                s_score = 12
            elif up_down_vol_ratio >= 0.9:
                s_score = 8
            else:
                s_score = 3

        # L: Leader vs Laggard (RS Rating)
        rs_rating = rs_info.get("rs_rating", 50)
        if rs_rating >= 85:
            l_score = 15
        elif rs_rating >= 75:
            l_score = 12
        elif rs_rating >= 60:
            l_score = 8
        else:
            l_score = 2

        # I: Institutional Liquidity & Sponsorship
        avg_val_vnd = fund_info.get("avg_liquidity_vnd", 0.0)
        if avg_val_vnd >= 80_000_000_000:
            i_score = 15
        elif avg_val_vnd >= 25_000_000_000:
            i_score = 12
        elif avg_val_vnd >= 5_000_000_000:
            i_score = 7
        else:
            i_score = 0

        total = c_score + a_score + n_score + s_score + l_score + i_score
        grade = "A+" if total >= 85 else ("A" if total >= 75 else ("B" if total >= 60 else ("C" if total >= 45 else "D")))

        return {
            "canslim_score": total,
            "canslim_grade": grade,
            "up_down_vol_ratio": up_down_vol_ratio,
            "components": {
                "C_Quarterly_Growth": f"{c_score}/20 ({p_growth:+.1f}% YoY)" if p_growth is not None else f"{c_score}/20",
                "A_Annual_ROE": f"{a_score}/20 (ROE {roe:.1f}%)" if roe is not None else f"{a_score}/20",
                "N_Near_52W_High": f"{n_score}/15 (-{pct_below_high:.1f}% từ đỉnh 52W)",
                "S_Supply_Demand": f"{s_score}/15 (Up/Down Vol = {up_down_vol_ratio:.2f}x)",
                "L_Leader_RS": f"{l_score}/15 (RS Rating = {rs_rating}/99)",
                "I_Institutional": f"{i_score}/15 (Thanh khoản {avg_val_vnd/1e9:.1f} tỷ/phiên)"
            }
        }

    @classmethod
    def compute_finrl_risk_and_sizing(
        cls,
        df_daily: pd.DataFrame,
        curr_price: float,
        stop_loss_price: float,
        target_price: float,
        nav_vnd: float = 1_000_000_000.0,
        beta: float = 1.0,
        is_downtrend: bool = False
    ) -> dict:
        """
        Tính toán Bộ Chỉ Số Định Lượng & Quản Trị Vốn FinRL + TradingAgents-Vn:
        - Annualized Sharpe Ratio, Sortino Ratio, Calmar Ratio, Max Drawdown (MDD%), Volatility%.
        - Half-Kelly Criterion & Volatility-Targeted Lot-100 Sizing (có cộng biên độ trượt giá T+2.5 tại Việt Nam).
        """
        if df_daily is None or df_daily.empty or len(df_daily) < 30 or curr_price <= 0:
            return {
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "calmar_ratio": 0.0,
                "max_drawdown_pct": 0.0,
                "annual_volatility_pct": 0.0,
                "cagr_pct": 0.0,
                "half_kelly_pct": 0.0,
                "recommended_nav_pct": 0.0,
                "recommended_shares_lot100": 0,
                "t25_effective_risk_pct": 0.0
            }

        window = df_daily.tail(252).copy()
        rets = window["close"].pct_change().dropna()
        if rets.empty:
            rets = pd.Series([0.0])

        mean_daily = float(rets.mean())
        std_daily = float(rets.std()) if len(rets) > 1 else 0.02
        ann_vol = std_daily * math.sqrt(cls.TRADING_DAYS)
        ann_ret = (1.0 + mean_daily) ** cls.TRADING_DAYS - 1.0

        # Sharpe Ratio
        sharpe = ((ann_ret - cls.VN_RISK_FREE_RATE) / ann_vol) if ann_vol > 1e-6 else 0.0

        # Sortino Ratio (Downside deviation only)
        downside_rets = rets[rets < 0]
        downside_std = float(downside_rets.std()) * math.sqrt(cls.TRADING_DAYS) if len(downside_rets) > 1 else ann_vol
        sortino = ((ann_ret - cls.VN_RISK_FREE_RATE) / downside_std) if downside_std > 1e-6 else 0.0

        # Max Drawdown
        cum = (1.0 + rets).cumprod()
        peak = cum.cummax()
        dd = (cum - peak) / peak
        max_dd = float(dd.min()) if not dd.empty else 0.0

        # Calmar Ratio
        calmar = (ann_ret / abs(max_dd)) if abs(max_dd) > 1e-4 else 0.0

        # Win-rate & Payoff for Half-Kelly Criterion
        wins = rets[rets > 0]
        losses = rets[rets < 0]
        win_prob = len(wins) / max(len(rets), 1)
        rr_ratio = ((target_price - curr_price) / max(curr_price - stop_loss_price, curr_price * 0.01)) if target_price > curr_price else 2.0
        b = max(rr_ratio, 1.0)
        q = 1.0 - win_prob
        full_kelly = max(0.0, (win_prob * b - q) / b)
        half_kelly_pct = round(min(25.0, full_kelly * 0.5 * 100.0), 1)

        # Vietnam T+2.5 Settlement Slippage Adjustment:
        # Because shares bought on T+0 cannot be sold until T+2 afternoon (13:00),
        # we add a 1.5% T+2.5 gap/slippage buffer to the structural stop distance.
        raw_stop_pct = abs(curr_price - stop_loss_price) / curr_price
        t25_slippage_buffer = 0.015
        effective_risk_pct = max(0.03, raw_stop_pct + t25_slippage_buffer)

        if is_downtrend:
            rec_nav_pct = 0.0
            lot100_shares = 0
        else:
            # 1% NAV risk budget per trade (Claude Trading Skills & FinRL Institutional Rule)
            risk_budget_vnd = nav_vnd * 0.012  # 1.2% NAV max loss if stopped out with T+2.5 slippage
            risk_per_share_vnd = curr_price * effective_risk_pct
            raw_shares = risk_budget_vnd / max(risk_per_share_vnd, 100.0)
            # Cap position value by Half-Kelly and 25% Max Single-Stock Concentration
            max_pos_pct = min(25.0, max(10.0, half_kelly_pct))
            max_shares_by_cap = (nav_vnd * (max_pos_pct / 100.0)) / curr_price
            final_shares = min(raw_shares, max_shares_by_cap)
            lot100_shares = int(final_shares // 100) * 100
            rec_nav_pct = round((lot100_shares * curr_price) / nav_vnd * 100.0, 1)

        return {
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "calmar_ratio": round(calmar, 2),
            "max_drawdown_pct": round(max_dd * 100.0, 2),
            "annual_volatility_pct": round(ann_vol * 100.0, 2),
            "cagr_pct": round(ann_ret * 100.0, 2),
            "win_rate_daily_pct": round(win_prob * 100.0, 1),
            "half_kelly_pct": half_kelly_pct,
            "recommended_nav_pct": rec_nav_pct,
            "recommended_shares_lot100": lot100_shares,
            "t25_effective_risk_pct": round(effective_risk_pct * 100.0, 2)
        }

    @classmethod
    def compute_dupont_and_valuation(cls, ov: dict) -> dict:
        """
        Thực hiện Phân Tích DuPont 3 Bước (FinRobot) & Định Giá Giá Trị Nội Tại Đa Mô Hình (Aswath Damodaran / Ben Graham / Peter Lynch).
        Tự động phân nhánh chuẩn xác giữa Ngân Hàng (Excess Return / P/B-ROE) và Phi Tài Chính (DCF + Graham + Lynch PEG).
        """
        curr_price = float(ov.get("current_price") or 0.0)
        pe = ov.get("pe")
        pb = ov.get("pb")
        eps = ov.get("eps")
        bvps = ov.get("bvps")
        roe = ov.get("roe")
        roa = ov.get("roa")
        beta = float(ov.get("beta") or 1.0)
        is_bank = bool(ov.get("is_bank"))
        net_margin = ov.get("net_margin")
        asset_turnover = ov.get("asset_turnover")
        de = ov.get("debt_to_equity")
        p_growth = ov.get("profit_growth_yoy")

        # Cost of Equity (CAPM for Vietnam Market)
        ke = cls.VN_RISK_FREE_RATE + max(0.6, min(1.8, beta)) * cls.VN_ERP  # Typically ~9.5% - 13.5%

        # --- 1. 3-Step DuPont Analysis ---
        if is_bank:
            nim = ov.get("nim") or 0.9
            cir = ov.get("cir") or 32.0
            eq_assets = ov.get("equity_to_assets") or 10.0
            eq_mult = round(100.0 / max(eq_assets, 4.0), 2)
            dupont_summary = (
                f"Mô hình Ngân hàng: ROE ({roe or 0:.1f}%) = ROA ({roa or 0:.2f}%) × Đòn bẩy Vốn ({eq_mult:.1f}x) | "
                f"NIM quý: {nim:.2f}% | CIR: {cir:.1f}%."
            )
            roe_driver = "Quản trị chi phí (CIR thấp) & CASA/NIM tốt" if cir < 35 else "Đòn bẩy tín dụng ngân hàng thương mại"
        else:
            nm = net_margin if net_margin is not None else ((roe / 1.5) if roe else 8.0)
            at = asset_turnover if asset_turnover is not None else 0.65
            eq_mult = round(1.0 + (de if de is not None else 0.5), 2)
            dupont_summary = (
                f"DuPont 3 Bước: ROE ({roe or 0:.1f}%) ≈ Biên LN Ròng ({nm:.1f}%) × "
                f"Vòng Quay Tài Sản ({at:.2f}x) × Đòn Bẩy Tài Chính ({eq_mult:.2f}x)."
            )
            if nm >= 15.0 and eq_mult <= 2.2:
                roe_driver = "Lợi thế cạnh tranh bền vững (Biên lợi nhuận cao, nợ vay thấp - Chuẩn Buffett)"
            elif at >= 1.2:
                roe_driver = "Hiệu suất vòng quay tài sản cao (Bán lẻ / Sản xuất tối ưu)"
            elif eq_mult >= 2.8:
                roe_driver = "⚠️ ROE được phóng đại bởi Đòn bẩy nợ vay cao (Rủi ro tài chính)"
            else:
                roe_driver = "Cân bằng giữa biên lợi nhuận và vòng quay vốn"

        # --- 2. Multi-Model Intrinsic Valuation ("Football Field") ---
        models = {}
        roe_dec = (roe / 100.0) if (roe is not None and roe > 0) else 0.12
        g_terminal = 0.05  # 5% long-term nominal terminal growth in Vietnam

        if is_bank:
            # Model 1: Damodaran Excess Return / Justified P/B Model for Banks
            if bvps and bvps > 0:
                justified_pb = max(0.6, min(3.2, (roe_dec - g_terminal) / max(0.03, ke - g_terminal)))
                # Blend with historical Vietnam bank P/B ceiling
                models["Damodaran Excess Return (P/B-ROE)"] = round(bvps * justified_pb, 0)
            # Model 2: Sector Fair P/E (10.5x for High-ROE Quality Banks, 8.5x for Average)
            if eps and eps > 0:
                fair_pe_bank = 10.5 if (roe and roe >= 16.0) else (9.2 if (roe and roe >= 13.0) else 7.8)
                models["Định Giá P/E Chuẩn Ngân Hàng"] = round(eps * fair_pe_bank, 0)
        else:
            # Model 1: Benjamin Graham Number = sqrt(22.5 * EPS * BVPS)
            if eps and eps > 0 and bvps and bvps > 0:
                models["Benjamin Graham Number"] = round(math.sqrt(22.5 * eps * bvps), 0)

            # Benjamin Graham Multi-Model Suite (AFL VPA 5.0 formulas):
            # Vgraham1 = EPS * (7 + 1.5 * g) * 4.4 / y (y = 6.5% VN bond yield)
            # Vgraham2 = EPS * (7 + 1.5 * g)
            # Vgraham3 = EPS * (8.5 + 2 * g)
            # VgrahamBVPS = sqrt(22.5 * EPS * BVPS)
            # VTB = (Vgraham1 + Vgraham2 + Vgraham3 + VgrahamBVPS) / 4 | VCHIETKHAU = VTB * 0.70
            eff_g = max(3.0, min(25.0, p_growth if (p_growth is not None and p_growth > 0) else (roe if roe else 8.0)))
            if eps and eps > 0:
                y_bond = 6.5  # Lợi suất trái phiếu chính phủ Việt Nam danh nghĩa
                vg1 = eps * (7.0 + 1.5 * eff_g) * 4.4 / y_bond
                vg2 = eps * (7.0 + 1.5 * eff_g)
                vg3 = eps * (8.5 + 2.0 * eff_g)
                vg_bvps = math.sqrt(22.5 * eps * bvps) if (bvps and bvps > 0) else vg1
                v_tb = (vg1 + vg2 + vg3 + vg_bvps) / 4.0
                models["Benjamin Graham Hợp Nhất (VTB)"] = round(v_tb, 0)
                models["Benjamin Graham Chiết Khấu An Toàn (-30%)"] = round(v_tb * 0.70, 0)

            # Model 2: Peter Lynch GARP Fair Value
            if eps and eps > 0:
                fair_pe_lynch = max(8.0, min(22.0, eff_g * 0.85))
                models["Peter Lynch GARP Valuation"] = round(eps * fair_pe_lynch, 0)

            # Model 3: Damodaran 2-Stage Discounted Earnings / FCFF Model
            if eps and eps > 0:
                g_stage1 = min(0.22, max(0.04, ((p_growth or 10.0) / 100.0) * 0.6 + roe_dec * 0.4))
                if p_growth is not None and p_growth < 0:
                    g_stage1 = 0.03  # Penalize contracting earnings
                payout = 0.55
                pv_stage1 = 0.0
                proj_eps = eps
                for yr in range(1, 6):
                    proj_eps *= (1.0 + g_stage1)
                    pv_stage1 += (proj_eps * payout) / ((1.0 + ke) ** yr)
                terminal_val = (proj_eps * (1.0 + g_terminal) * 0.65) / max(0.04, ke - g_terminal)
                pv_terminal = terminal_val / ((1.0 + ke) ** 5)
                models["Damodaran 2-Stage DCF"] = round(pv_stage1 + pv_terminal, 0)

        valid_vals = [v for v in models.values() if v and v > 0]
        intrinsic_value = round(float(np.mean(valid_vals)), 0) if valid_vals else curr_price
        mos_pct = round(((intrinsic_value - curr_price) / intrinsic_value * 100.0), 1) if intrinsic_value > 0 and curr_price > 0 else 0.0

        if mos_pct >= 18.0:
            val_status = "ĐỊNH GIÁ RẺ - BIÊN AN TOÀN HẤP DẪN (UNDERVALUED) 🟢"
        elif mos_pct >= -5.0:
            val_status = "ĐỊNH GIÁ HỢP LÝ (FAIR VALUE) 🟡"
        else:
            val_status = "ĐỊNH GIÁ ĐẮT / VƯỢT GIÁ TRỊ NỘI TẠI (OVERVALUED) 🔴"

        return {
            "cost_of_equity_pct": round(ke * 100.0, 2),
            "dupont_summary": dupont_summary,
            "roe_driver": roe_driver,
            "valuation_models": models,
            "intrinsic_value": intrinsic_value,
            "margin_of_safety_pct": mos_pct,
            "valuation_status": val_status
        }

    @classmethod
    def evaluate_legendary_personas(
        cls,
        symbol: str,
        ov: dict,
        dupont_val: dict,
        sepa_vcp: dict,
        canslim: dict,
        rs_info: dict,
        tech_report: dict
    ) -> list:
        """
        Hội Đồng 9 Đại Kiện Tướng Đầu Tư Thế Giới (virattt/ai-hedge-fund):
        Chấm điểm độc lập và đưa ra lập luận chuẩn phong cách từng huyền thoại.
        """
        pe = ov.get("pe")
        pb = ov.get("pb")
        roe = ov.get("roe")
        de = ov.get("debt_to_equity")
        p_growth = ov.get("profit_growth_yoy")
        gross_m = ov.get("gross_margin")
        is_bank = bool(ov.get("is_bank"))
        mos = dupont_val.get("margin_of_safety_pct", 0.0)
        iv = dupont_val.get("intrinsic_value", 0.0)
        is_downtrend = tech_report.get("is_downtrend", False)
        stage = tech_report.get("market_stage", 1)
        rs_rating = rs_info.get("rs_rating", 50)
        sepa_score = sepa_vcp.get("sepa_score", 0)

        council = []

        # 1. Warren Buffett
        buffett_bull = (roe is not None and roe >= 15.0) and (is_bank or (de is None or de <= 0.8)) and mos >= -5.0 and not is_downtrend
        council.append({
            "persona": "Warren Buffett",
            "title": "Hào Kinh Tế & Lãi Kép (Economic Moat)",
            "signal": "BULLISH 🟢" if buffett_bull else ("BEARISH 🔴" if (roe is not None and roe < 10) or is_downtrend else "NEUTRAL 🟡"),
            "confidence": 85 if buffett_bull else 65,
            "rationale": (
                f"ROE đạt {roe or 0:.1f}%, {'biên lợi nhuận gộp ' + str(round(gross_m, 1)) + '% vững chắc, ' if gross_m else ''}"
                f"giá trị nội tại ước tính {iv:,.0f} đ (MoS: {mos:+.1f}%). "
                + ("Doanh nghiệp có hào kinh tế tốt ở mức giá hợp lý." if buffett_bull else "Chưa đạt chuẩn con hào kinh tế hoặc biên an toàn chưa đủ hấp dẫn.")
            )
        })

        # 2. Charlie Munger
        munger_veto = is_downtrend or (p_growth is not None and p_growth < -15.0) or (not is_bank and de is not None and de > 1.5)
        council.append({
            "persona": "Charlie Munger",
            "title": "Tư Duy Ngược & Tránh Sự Ngu Ngốc (Inversion)",
            "signal": "BEARISH 🔴" if munger_veto else ("BULLISH 🟢" if (roe and roe >= 16.0 and not is_downtrend) else "NEUTRAL 🟡"),
            "confidence": 90 if munger_veto else 75,
            "rationale": (
                "Hãy đảo ngược vấn đề: Đâu là nơi chúng ta sẽ chết? "
                + (
                    (f"Cổ phiếu đang ở Stage 4 Downtrend." if is_downtrend else f"Lợi nhuận suy giảm mạnh ({p_growth or 0:+.1f}% YoY) hoặc đòn bẩy nợ cao (D/E={de or 'N/A'}).") + " Tuyệt đối tránh xa!"
                    if munger_veto
                    else f"Không phát hiện bẫy nợ vay hay suy thoái cấu trúc; doanh nghiệp chất lượng cao (ROE {roe or 0:.1f}%)."
                )
            )
        })

        # 3. Benjamin Graham
        graham_ok = (pe is not None and 0 < pe <= 12.5) and (pb is not None and 0 < pb <= 1.6) and mos >= 15.0 and not is_downtrend
        council.append({
            "persona": "Benjamin Graham",
            "title": "Đầu Tư Giá Trị Cổ Điển & Biên An Toàn (Margin of Safety)",
            "signal": "BULLISH 🟢" if graham_ok else ("BEARISH 🔴" if (mos < -10 or is_downtrend) else "NEUTRAL 🟡"),
            "confidence": 82 if graham_ok else 68,
            "rationale": (
                f"P/E = {pe or 'N/A'}x, P/B = {pb or 'N/A'}x, Biên an toàn (MoS) = {mos:+.1f}%. "
                + ("Đạt chuẩn định giá rẻ Graham với đệm tài sản an toàn." if graham_ok else "Định giá chưa đủ rẻ theo tiêu chuẩn Graham hoặc xu hướng giá đang rơi.")
            )
        })

        # 4. Peter Lynch
        eff_g = p_growth if (p_growth is not None and p_growth > 0) else (roe if (roe and roe > 0) else 1.0)
        peg = round(pe / max(eff_g, 1.0), 2) if (pe and pe > 0) else 9.9
        lynch_ok = peg <= 1.25 and (p_growth is None or p_growth >= 10.0) and not is_downtrend
        council.append({
            "persona": "Peter Lynch",
            "title": "Tăng Trưởng Ở Mức Giá Hợp Lý (GARP / PEG)",
            "signal": "BULLISH 🟢" if lynch_ok else ("BEARISH 🔴" if (p_growth is not None and p_growth < 0) or is_downtrend else "NEUTRAL 🟡"),
            "confidence": 80 if lynch_ok else 65,
            "rationale": (
                f"Chỉ số PEG ước tính = {peg:.2f}x (P/E {pe or 'N/A'}x so với tốc độ tăng trưởng/ROE {eff_g:.1f}%). "
                + ("PEG ≤ 1.25 cho thấy cổ phiếu tăng trưởng đang được định giá rất hấp dẫn." if lynch_ok else "Tăng trưởng lợi nhuận quý gần nhất đang chững lại hoặc PEG chưa đủ rẻ.")
            )
        })

        # 5. Stanley Druckenmiller
        druck_ok = (stage == 2 and rs_rating >= 70 and sepa_score >= 6)
        council.append({
            "persona": "Stanley Druckenmiller",
            "title": "Động Lượng Vĩ Mô & Cược Bất Đối Xứng (Asymmetric Trend)",
            "signal": "BULLISH 🟢" if druck_ok else ("BEARISH 🔴" if is_downtrend else "NEUTRAL 🟡"),
            "confidence": 88 if druck_ok else 78,
            "rationale": (
                f"Cấu trúc kỹ thuật: Stage {stage} | SEPA Trend Template: {sepa_score}/8 | RS Rating: {rs_rating}/99. "
                + ("Cổ phiếu dẫn dắt (Leader) hội tụ cả dòng tiền lẫn xu hướng tăng Giai đoạn 2." if druck_ok else "Tôi không bao giờ mua cổ phiếu nằm dưới MA200 hoặc thiếu xung lực dẫn dắt thị trường.")
            )
        })

        # 6. Aswath Damodaran
        ke_pct = dupont_val.get("cost_of_equity_pct", 11.0)
        spread = (roe or 0.0) - ke_pct
        damo_ok = spread > 2.0 and mos >= 5.0 and not is_downtrend
        council.append({
            "persona": "Aswath Damodaran",
            "title": "Định Giá Dòng Tiền & Chi Phí Vốn (Intrinsic Valuation)",
            "signal": "BULLISH 🟢" if damo_ok else ("BEARISH 🔴" if spread < -2.0 or mos < -15.0 else "NEUTRAL 🟡"),
            "confidence": 84,
            "rationale": (
                f"Chi phí vốn cổ phần (Ke) = {ke_pct:.1f}%, ROE = {roe or 0:.1f}% (Excess Return Spread = {spread:+.1f}%). "
                f"Giá trị hợp lý đa mô hình = {iv:,.0f} đ ({mos:+.1f}% MoS)."
            )
        })

        # 7. William O'Neil / Mark Minervini (CANSLIM & SEPA Growth)
        cs_score = canslim.get("canslim_score", 50)
        oneil_ok = cs_score >= 68 and not is_downtrend and stage == 2
        council.append({
            "persona": "William O'Neil & Minervini",
            "title": "CANSLIM & Mẫu Hình Thu Hẹp Biến Động SEPA/VCP",
            "signal": "BULLISH 🟢" if oneil_ok else ("BEARISH 🔴" if is_downtrend or stage == 4 else "NEUTRAL 🟡"),
            "confidence": 90 if (oneil_ok or is_downtrend) else 70,
            "rationale": (
                f"Điểm CANSLIM = {cs_score}/100 (Hạng {canslim.get('canslim_grade', 'C')}), SEPA = {sepa_score}/8, "
                f"VCP = {'Đã xác nhận' if sepa_vcp.get('vcp_detected') else 'Chưa nén hoàn chỉnh'}. "
                + ("Đạt chuẩn Siêu Cổ Phiếu Giai đoạn 2!" if oneil_ok else ("Vi phạm quy tắc Giai đoạn 4 Downtrend - Cấm mua bắt đáy!" if is_downtrend else "Chờ điểm nổ Pivot kèm khối lượng."))
            )
        })

        # 8. Michael Burry
        burry_ok = (pb is not None and pb <= 1.25) and mos >= 15.0 and not is_downtrend
        council.append({
            "persona": "Michael Burry",
            "title": "Giá Trị Ngược Dòng & Tài Sản Ròng (Deep Value)",
            "signal": "BULLISH 🟢" if burry_ok else ("BEARISH 🔴" if is_downtrend else "NEUTRAL 🟡"),
            "confidence": 75,
            "rationale": (
                f"P/B = {pb or 'N/A'}x, Giá trị sổ sách BVPS = {ov.get('bvps') or 0:,.0f} đ. "
                + ("Giao dịch sát giá trị sổ sách với biên an toàn lớn." if burry_ok else "Chưa phải cơ hội Deep Value cực đoan hoặc rủi ro xu hướng giảm chưa kết thúc.")
            )
        })

        # 9. Bill Ackman
        ackman_ok = (roe is not None and roe >= 16.0) and (canslim.get("up_down_vol_ratio", 1.0) >= 1.1) and not is_downtrend
        council.append({
            "persona": "Bill Ackman",
            "title": "Chất Lượng Dòng Tiền Tổ Chức & Quản Trị Vốn",
            "signal": "BULLISH 🟢" if ackman_ok else ("BEARISH 🔴" if is_downtrend else "NEUTRAL 🟡"),
            "confidence": 78,
            "rationale": (
                f"Tỷ lệ dòng tiền Mua gom / Phân phối 20 phiên = {canslim.get('up_down_vol_ratio', 1.0):.2f}x | "
                f"Nguồn gốc ROE: {dupont_val.get('roe_driver', 'N/A')}."
            )
        })

        return council
