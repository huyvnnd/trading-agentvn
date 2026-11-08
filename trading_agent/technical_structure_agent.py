"""
Multi-Timeframe Market Structure, SEPA/VCP, Volume Profile & FinRL Quantitative Technical Agent.
Phân tích toàn diện cấu trúc thị trường đa khung thời gian (Tháng - Tuần - Ngày - Intraday 15m):
1. Chu kỳ 4 giai đoạn Stan Weinstein & Wyckoff: Stage 1 (Tích lũy), Stage 2 (Đẩy giá Uptrend), Stage 3 (Phân phối), Stage 4 (Đè giá Downtrend - CẤM MUA).
2. Bộ Khuôn Mẫu 8 Tiêu Chí Mark Minervini (SEPA Trend Template) & Mẫu hình Thu Hẹp Độ Biến Động VCP (T1 > T2 > T3 + Volume Dry-Up).
3. Sức mạnh giá tương đối William O'Neil RS Rating (1-99) so với VN-INDEX.
4. Volume Profile (POC, VAH, VAL) & Tín hiệu Dòng tiền Thông minh Wyckoff VSA / SMC.
5. Chỉ số định lượng FinRL: Sharpe, Sortino, Calmar, Max Drawdown, Half-Kelly & Khối lượng Lô 100 CP điều chỉnh T+2.5.
"""

import pandas as pd
import numpy as np
from trading_agent.data_engine import DataEngine
from trading_agent.technical_analysis import TechnicalAnalysis
from trading_agent.quant_engine import QuantEngine


class TechnicalStructureAgent:
    def __init__(self, data_engine: DataEngine = None):
        self.de = data_engine or DataEngine()

    def analyze_multi_timeframe_structure(self, symbol: str) -> dict:
        symbol = symbol.strip().upper()

        # 1. Thu thập dữ liệu lịch sử 1500 ngày (từ Master Cache chỉ tốn < 1ms sau lần đầu)
        df_daily_raw = self.de.get_history(symbol, days=1500)
        df_vnindex = self.de.get_history("VNINDEX", days=450)

        if df_daily_raw.empty or len(df_daily_raw) < 30:
            return {
                "symbol": symbol,
                "status": "error",
                "message": f"Dữ liệu lịch sử của mã {symbol} không đủ để phân tích cấu trúc đa khung thời gian."
            }

        df_daily = df_daily_raw.copy()
        df_daily["time"] = pd.to_datetime(df_daily["time"])
        df_daily = df_daily.sort_values("time").reset_index(drop=True)

        quote = self.de.get_latest_quote(symbol)
        curr_price = float(quote.get("price", df_daily["close"].iloc[-1]))
        if curr_price <= 0:
            curr_price = float(df_daily["close"].iloc[-1])

        # =========================================================================
        # RESAMPLE NẾN TUẦN (W-FRI) VÀ NẾN THÁNG (ME) CHUẨN TỔ CHỨC
        # =========================================================================
        df_weekly = df_daily.set_index("time").resample("W-FRI").agg({
            "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
        }).dropna().reset_index()

        df_monthly = df_daily.set_index("time").resample("ME").agg({
            "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"
        }).dropna().reset_index()

        # =========================================================================
        # 1. PHÂN TÍCH KHUNG THÁNG (MONTHLY HTF - MACRO TREND & CYCLE)
        # =========================================================================
        all_time_high = float(df_daily["high"].max())
        discount_from_ath = ((all_time_high - curr_price) / all_time_high * 100.0) if all_time_high > 0 else 0.0

        monthly_trend = "ĐANG TÍCH LŨY / TÁI CÂN BẰNG DÀI HẠN"
        monthly_score = 0
        sma12_m = None

        if len(df_monthly) >= 12:
            sma12_m = float(df_monthly["close"].rolling(12).mean().iloc[-1])
            sma24_m = float(df_monthly["close"].rolling(24).mean().iloc[-1]) if len(df_monthly) >= 24 else sma12_m
            sma12_m_prev = float(df_monthly["close"].rolling(12).mean().iloc[-3]) if len(df_monthly) >= 15 else sma12_m
            is_monthly_sloping_down = sma12_m < sma12_m_prev

            if curr_price < sma12_m * 0.95 and is_monthly_sloping_down:
                monthly_trend = f"DOWNTREND DÀI HẠN (GIAI ĐOẠN 4 SUY THOÁI CHU KỲ - DƯỚI MA12 THÁNG {sma12_m:,.0f} đ)"
                monthly_score = -5
            elif curr_price < sma12_m * 0.96:
                monthly_trend = f"ĐIỀU CHỈNH CHU KỲ (NẰM DƯỚI ĐƯỜNG MA12 THÁNG {sma12_m:,.0f} đ)"
                monthly_score = -2
            elif curr_price >= sma12_m and sma12_m >= sma24_m * 0.98:
                monthly_trend = f"UPTREND DÀI HẠN (CHU KỲ MỞ RỘNG TRÊN MA12 THÁNG {sma12_m:,.0f} đ)"
                monthly_score = 4
            else:
                monthly_trend = f"TÍCH LŨY / HẤP THỤ TRÊN VÙNG HỖ TRỢ DÀI HẠN (QUANH MA12 THÁNG {sma12_m:,.0f} đ)"
                monthly_score = 2
        elif len(df_monthly) >= 6:
            sma6_m = float(df_monthly["close"].rolling(6).mean().iloc[-1])
            if curr_price < sma6_m:
                monthly_trend = "XU HƯỚNG DÀI HẠN SUY YẾU (DƯỚI TRUNG BÌNH 6 THÁNG)"
                monthly_score = -3
            else:
                monthly_trend = "XU HƯỚNG DÀI HẠN KHẢ QUAN"
                monthly_score = 2

        # =========================================================================
        # 2. PHÂN TÍCH KHUNG TUẦN (WEEKLY HTF - STAN WEINSTEIN 30-WEEK MA & WYCKOFF)
        # =========================================================================
        weekly_score = 0
        weekly_structure = "ĐI NGANG (SIDEWAY)"
        major_weekly_support = curr_price * 0.90
        major_weekly_resistance = curr_price * 1.15
        sma30_w = curr_price

        if len(df_weekly) >= 20:
            high_26w = float(df_weekly["high"].rolling(26).max().iloc[-1])
            low_26w = float(df_weekly["low"].rolling(26).min().iloc[-1])
            sma20_w = float(df_weekly["close"].rolling(20).mean().iloc[-1])
            sma30_w = float(df_weekly["close"].rolling(30).mean().iloc[-1]) if len(df_weekly) >= 30 else sma20_w
            sma50_w = float(df_weekly["close"].rolling(50).mean().iloc[-1]) if len(df_weekly) >= 50 else sma30_w

            major_weekly_support = low_26w
            major_weekly_resistance = high_26w

            if curr_price < sma20_w * 0.95 and sma20_w < sma50_w:
                weekly_structure = f"DOWNTREND TRUNG HẠN (CẤU TRÚC ĐỈNH ĐÁY HẠ DẦN - DƯỚI MA20 TUẦN {sma20_w:,.0f} đ & MA30 TUẦN {sma30_w:,.0f} đ)"
                weekly_score = -5
            elif curr_price < sma20_w * 0.96:
                weekly_structure = f"SUY YẾU DƯỚI MA20 TUẦN ({sma20_w:,.0f} đ) - ÁP LỰC CUNG TRUNG HẠN ĐÈ NẶNG"
                weekly_score = -3
            elif curr_price >= sma20_w * 0.985 and sma20_w >= sma50_w * 0.985:
                weekly_structure = f"CẤU TRÚC UPTREND TRUNG HẠN VỮNG CHẮC (TRÊN HỖ TRỢ MA20/MA30 TUẦN WEINSTEIN {sma30_w:,.0f} đ)"
                weekly_score = 4
            elif curr_price >= sma20_w * 0.97:
                weekly_structure = f"PHA TÍCH LŨY KÊNH TRÊN / RETEST HỖ TRỢ TUẦN ({sma20_w:,.0f} đ - WYCKOFF PHASE D)"
                weekly_score = 2
            else:
                weekly_structure = "TÍCH LŨY HẤP THỤ BIÊN ĐỘ TUẦN (SIDEWAY)"
                weekly_score = 0

        # =========================================================================
        # 3. KHUNG NGÀY: WEINSTEIN STAGES, MINERVINI SEPA 8-POINT, VCP, MCDX & SMC
        # =========================================================================
        df_daily_ind = TechnicalAnalysis.calculate_indicators(df_daily)
        sma20_d = float(df_daily_ind["sma_20"].iloc[-1]) if pd.notna(df_daily_ind.get("sma_20", pd.Series()).iloc[-1]) else curr_price
        sma50_d = float(df_daily_ind["sma_50"].iloc[-1]) if pd.notna(df_daily_ind.get("sma_50", pd.Series()).iloc[-1]) else curr_price
        sma150_d = float(df_daily["close"].rolling(150).mean().iloc[-1]) if len(df_daily) >= 150 else sma50_d
        sma200_d = float(df_daily_ind["sma_200"].iloc[-1]) if pd.notna(df_daily_ind.get("sma_200", pd.Series()).iloc[-1]) else curr_price
        rsi_d = float(df_daily_ind["rsi"].iloc[-1]) if pd.notna(df_daily_ind.get("rsi", pd.Series()).iloc[-1]) else 50.0
        prev_rsi_d = float(df_daily_ind["rsi"].iloc[-2]) if len(df_daily_ind) >= 2 and pd.notna(df_daily_ind["rsi"].iloc[-2]) else rsi_d
        vol_ratio = float(df_daily_ind["vol_ratio"].iloc[-1]) if pd.notna(df_daily_ind.get("vol_ratio", pd.Series()).iloc[-1]) else 1.0

        prev_close_d = float(df_daily_ind["close"].iloc[-2]) if len(df_daily_ind) >= 2 else curr_price
        open_d = float(df_daily_ind["open"].iloc[-1]) if "open" in df_daily_ind.columns else curr_price

        mcdx_banker = float(df_daily_ind["mcdx_banker"].iloc[-1]) if "mcdx_banker" in df_daily_ind.columns else 0.0
        prev_banker = float(df_daily_ind["mcdx_banker"].iloc[-2]) if "mcdx_banker" in df_daily_ind.columns and len(df_daily_ind) >= 2 else mcdx_banker
        mcdx_b_sma36 = float(df_daily_ind["mcdx_banker_sma36"].iloc[-1]) if "mcdx_banker_sma36" in df_daily_ind.columns and pd.notna(df_daily_ind["mcdx_banker_sma36"].iloc[-1]) else 0.0
        mcdx_hot = float(df_daily_ind["mcdx_hot"].iloc[-1]) if "mcdx_hot" in df_daily_ind.columns else 0.0
        mcdx_retail = float(df_daily_ind["mcdx_retail"].iloc[-1]) if "mcdx_retail" in df_daily_ind.columns else 0.0
        mcdx_fast = float(df_daily_ind["mcdx_fast"].iloc[-1]) if "mcdx_fast" in df_daily_ind.columns else 10.0
        prev_fast = float(df_daily_ind["mcdx_fast"].iloc[-2]) if "mcdx_fast" in df_daily_ind.columns and len(df_daily_ind) >= 2 else mcdx_fast
        mcdx_slow = float(df_daily_ind["mcdx_slow"].iloc[-1]) if "mcdx_slow" in df_daily_ind.columns and pd.notna(df_daily_ind["mcdx_slow"].iloc[-1]) else 10.0
        williams_r = float(df_daily_ind["williams_r"].iloc[-1]) if "williams_r" in df_daily_ind.columns else -50.0
        smc_high_60 = float(df_daily_ind["smc_high_60"].iloc[-1]) if "smc_high_60" in df_daily_ind.columns else curr_price * 1.05
        smc_low_60 = float(df_daily_ind["smc_low_60"].iloc[-1]) if "smc_low_60" in df_daily_ind.columns else curr_price * 0.95
        smc_pos_pct = float(df_daily_ind["smc_pos_pct"].iloc[-1]) if "smc_pos_pct" in df_daily_ind.columns else 50.0

        d_rsi = round(rsi_d - prev_rsi_d, 2)
        d_banker = round(mcdx_banker - prev_banker, 2)
        d_fast = round(mcdx_fast - prev_fast, 2)
        smc_disc_top = round(smc_low_60 + 0.30 * max(smc_high_60 - smc_low_60, 1.0), 0)

        # Tính RS Rating (1-99) & Minervini SEPA 8-Point + VCP
        rs_info = QuantEngine.compute_rs_rating(df_daily, df_vnindex)
        sepa_vcp = QuantEngine.evaluate_minervini_sepa_and_vcp(df_daily, rs_rating=rs_info["rs_rating"])

        recent_20_bars = df_daily_ind.tail(20)
        recent_range_pct = (recent_20_bars["high"].max() - recent_20_bars["low"].min()) / max(curr_price, 1) * 100.0

        # Volume Profile (120-day Institutional Cost Basis: POC, VAH, VAL)
        vp_window = df_daily.tail(120)
        p_min = float(vp_window["low"].min())
        p_max = float(vp_window["high"].max())
        poc_price = curr_price
        vah_price = curr_price * 1.05
        val_price = curr_price * 0.95
        if p_max > p_min:
            bins = np.linspace(p_min, p_max, 25)
            v_hist = np.zeros(24)
            typ_p = (vp_window["high"] + vp_window["low"] + vp_window["close"]) / 3.0
            for tp, v in zip(typ_p, vp_window["volume"]):
                b_idx = min(max(int(np.digitize(tp, bins)) - 1, 0), 23)
                v_hist[b_idx] += v
            poc_idx = int(np.argmax(v_hist))
            poc_price = float((bins[poc_idx] + bins[poc_idx + 1]) / 2.0)
            tot_v = np.sum(v_hist)
            acc_v = v_hist[poc_idx]
            lo_i, hi_i = poc_idx, poc_idx
            while acc_v < 0.70 * tot_v and (lo_i > 0 or hi_i < 23):
                v_dn = v_hist[lo_i - 1] if lo_i > 0 else -1
                v_up = v_hist[hi_i + 1] if hi_i < 23 else -1
                if v_up >= v_dn and hi_i < 23:
                    hi_i += 1
                    acc_v += v_hist[hi_i]
                elif lo_i > 0:
                    lo_i -= 1
                    acc_v += v_hist[lo_i]
                else:
                    break
            val_price = float(bins[lo_i])
            vah_price = float(bins[hi_i + 1])

        daily_score = 0
        market_stage = 1
        stage_name = "Stage 1: Tích Lũy Đáy (Wyckoff Basing)"

        is_stage_4 = (curr_price < sma200_d * 0.945 and sma50_d < sma200_d) or (curr_price < sma200_d * 0.90)
        is_post_peak_correction = bool(
            not is_stage_4
            and curr_price < sma20_d * 0.992
            and (mcdx_banker < mcdx_b_sma36 or d_banker < -1.0)
            and (mcdx_fast < mcdx_slow or d_fast < -0.5 or curr_price < prev_close_d)
        )
        is_confirmed_bottom_lps = bool(
            not is_stage_4
            and not is_post_peak_correction
            and (smc_pos_pct <= 45.0 or abs(curr_price - sma50_d) / max(sma50_d, 1) <= 0.025 or abs(curr_price - sma200_d) / max(sma200_d, 1) <= 0.03)
            and curr_price > prev_close_d
            and curr_price >= open_d
            and d_rsi > 0
            and (d_fast >= 0 or d_banker >= 0)
        )
        is_stage_2 = (
            not is_post_peak_correction
            and curr_price >= sma200_d * 0.99
            and sma50_d >= sma200_d * 0.99
            and curr_price >= sma50_d * 0.98
            and (curr_price >= sma20_d * 0.985 or is_confirmed_bottom_lps)
        )
        is_stage_3 = (not is_stage_4 and not is_stage_2 and (curr_price < sma50_d * 0.96 or is_post_peak_correction))

        if is_stage_4:
            market_stage = 4
            stage_name = "Giai Đoạn 4: DOWNTREND SUY THOÁI (WEINSTEIN STAGE 4 - ĐÈ GIÁ)"
            daily_score = -5
            daily_pattern = (
                f"DOWNTREND GIAI ĐOẠN 4: Giá ({curr_price:,.0f} đ) nằm dưới SMA200 ({sma200_d:,.0f} đ) & SMA50 ({sma50_d:,.0f} đ). "
                f"MCDX Banker = {mcdx_banker:.1f}, SEPA {sepa_vcp['sepa_score']}/8, RS Rating = {rs_info['rs_rating']}/99. Tuyệt đối cấm mua bắt đáy!"
            )
        elif is_post_peak_correction:
            market_stage = 3
            stage_name = "Giai Đoạn 2B/3: ĐANG ĐIỀU CHỈNH NGẮN HẠN SAU ĐỈNH (GÃY MA20 & MCDX RÚT RA - CHƯA CÓ ĐÁY)"
            daily_score = -3
            daily_pattern = (
                f"CẢNH BÁO CHƯA CÓ ĐÁY AN TOÀN: Cổ phiếu điều chỉnh từ đỉnh SMC Premium ({smc_high_60:,.0f} đ, kèm tín hiệu SELL/LPSY), "
                f"đã gãy dưới SMA20 ({sma20_d:,.0f} đ). MCDX Banker suy giảm mạnh xuống {mcdx_banker:.1f} (< SMA36 = {mcdx_b_sma36:.1f}), "
                f"đường xung lực MCDX Fast (Blue = {mcdx_fast:.1f}) lao dốc dưới Slow (White = {mcdx_slow:.1f}), RSI(14) = {rsi_d:.1f} ({d_rsi:+.1f}). "
                f"Tuyệt đối chưa bắt đáy sớm!"
            )
        elif is_stage_2:
            market_stage = 2
            stage_name = "Giai Đoạn 2: UPTREND TĂNG TRƯỞNG (WEINSTEIN STAGE 2 - ĐẨY GIÁ)"
            daily_score = 4
            if sepa_vcp["vcp_detected"]:
                daily_score += 2
                daily_pattern = (
                    f"SIÊU CỔ PHIẾU GIAI ĐOẠN 2 + MẪU HÌNH VCP: Đạt {sepa_vcp['sepa_score']}/8 tiêu chí Minervini SEPA, "
                    f"RS Rating = {rs_info['rs_rating']}/99, MCDX Banker = {mcdx_banker:.1f} (SMA36 = {mcdx_b_sma36:.1f}). "
                    f"Độ biến động thu hẹp {sepa_vcp['vcp_contractions']}% kèm cạn cung trước điểm nổ Pivot {sepa_vcp['pivot_price']:,.0f} đ!"
                )
            else:
                daily_pattern = (
                    f"UPTREND GIAI ĐOẠN 2: Giá duy trì vững chắc trên SMA20 ({sma20_d:,.0f} đ), SMA50 ({sma50_d:,.0f} đ) & SMA200 ({sma200_d:,.0f} đ). "
                    f"MCDX Banker = {mcdx_banker:.1f} (SMA36 = {mcdx_b_sma36:.1f}), Đạt {sepa_vcp['sepa_score']}/8 tiêu chí SEPA, RS Rating = {rs_info['rs_rating']}/99."
                )
        elif is_stage_3:
            market_stage = 3
            stage_name = "Giai Đoạn 3: PHÂN PHỐI ĐỈNH / SUY YẾU NGẮN HẠN (STAGE 3)"
            daily_score = -2
            daily_pattern = (
                f"CẢNH BÁO GIAI ĐOẠN 3: Giá gãy dưới SMA50 ({sma50_d:,.0f} đ), MCDX Banker = {mcdx_banker:.1f} (< SMA36 = {mcdx_b_sma36:.1f}). "
                f"Cần chờ lấy lại đường SMA50 và MCDX Blue cắt lên White trước khi giải ngân."
            )
        else:
            market_stage = 1
            stage_name = "Giai Đoạn 1: TÍCH LŨY TẠO NỀN (WYCKOFF BASE - STAGE 1)"
            daily_score = 1
            daily_pattern = (
                f"TÍCH LŨY GIAI ĐOẠN 1: Giá vận động quanh vùng giá vốn tổ chức POC ({poc_price:,.0f} đ). "
                f"MCDX Banker = {mcdx_banker:.1f}, SEPA đạt {sepa_vcp['sepa_score']}/8, RS Rating = {rs_info['rs_rating']}/99."
            )

        # =========================================================================
        # 4. TỔNG HỢP CẤU TRÚC ĐA KHUNG, QUẢN TRỊ RỦI RO FINRL & LÔ CHẴN T+2.5
        # =========================================================================
        total_structure_score = monthly_score + weekly_score + daily_score
        is_downtrend = (market_stage == 4 or (monthly_score <= -5 and weekly_score <= -5))

        swing_low_daily = float(df_daily["low"].tail(20).min())
        structural_stop_loss = swing_low_daily * 0.985
        max_allowed_sl = curr_price * 0.93  # Maximum 7% structural stop loss (Minervini Golden Rule)
        final_stop_loss = max(structural_stop_loss, max_allowed_sl)

        risk_per_share = curr_price - final_stop_loss
        if risk_per_share <= 0:
            risk_per_share = curr_price * 0.05
            final_stop_loss = curr_price * 0.95

        target_1 = curr_price + (risk_per_share * 2.5)
        target_2 = curr_price + (risk_per_share * 3.5)
        rr_ratio = (target_1 - curr_price) / risk_per_share if risk_per_share > 0 else 2.5

        # FinRL Quantitative Metrics & Position Sizing
        finrl_metrics = QuantEngine.compute_finrl_risk_and_sizing(
            df_daily=df_daily,
            curr_price=curr_price,
            stop_loss_price=final_stop_loss,
            target_price=target_1,
            nav_vnd=1_000_000_000.0,
            is_downtrend=(is_downtrend or is_post_peak_correction)
        )

        is_safe_entry = False
        if is_downtrend:
            is_safe_entry = False
            entry_recommendation = (
                f"⛔ CẢNH BÁO DOWNTREND (GIAI ĐOẠN 4 SUY THOÁI): Cổ phiếu {symbol} đang trong xu hướng giảm "
                f"trên cả khung Tháng, Tuần và Ngày (Giá {curr_price:,.0f} đ nằm dưới SMA200 {sma200_d:,.0f} đ và SMA50 {sma50_d:,.0f} đ). "
                f"Lượng cung kẹt hàng tại POC ({poc_price:,.0f} đ) vô cùng lớn. Mọi nhịp nảy nhẹ chỉ là hồi kỹ thuật (Dead Cat Bounce) để thoát hàng. "
                f"NGUYÊN TẮC QUỸ TỔ CHỨC: TUYỆT ĐỐI CẤM MUA BẮT ĐÁY!"
            )
        elif is_post_peak_correction:
            is_safe_entry = False
            entry_recommendation = (
                f"⚠️ CẢNH BÁO CHƯA CÓ ĐIỂM MUA BẮT ĐÁY AN TOÀN ({symbol} - ĐANG RƠI SAU ĐỈNH): "
                f"Trên đồ thị kỹ thuật, {symbol} vừa tạo đỉnh tại vùng cung SMC Premium ({smc_high_60:,.0f} đ) với tín hiệu phân phối SELL/LPSY, "
                f"hiện đã gãy dưới đường SMA20 ({sma20_d:,.0f} đ). Chỉ báo dòng tiền tạo lập MCDX Banker lao dốc về {mcdx_banker:.1f} "
                f"(thấp hơn hẳn đường trung bình SMA36 = {mcdx_b_sma36:.1f}), đường xung lực MCDX Fast (Blue = {mcdx_fast:.1f}) cắm xuống dưới Slow (White = {mcdx_slow:.1f}), "
                f"RSI(14) = {rsi_d:.1f} ({d_rsi:+.1f}) và %R = {williams_r:.1f} vẫn đang hướng xuống. "
                f"KHUYẾN NGHỊ: TUYỆT ĐỐI KHÔNG BẮT ĐÁY SỚM! Kiên nhẫn chờ giá lùi về vùng hỗ trợ cứng SMA200 ({sma200_d:,.0f} đ) / SMC Discount ({smc_low_60:,.0f} - {smc_disc_top:,.0f} đ) "
                f"kèm nến rút chân xanh và đường MCDX Blue cắt lên White mới giải ngân!"
            )
        elif total_structure_score >= 6 and market_stage == 2:
            # 1. Kiểm tra tiệm cận đỉnh cũ / kháng cự Pivot mà chưa Breakout dứt khoát
            pivot_p = sepa_vcp.get("pivot_price", curr_price * 1.05)
            is_near_peak_resistance = (
                curr_price < pivot_p * 0.995 
                and (curr_price >= pivot_p * 0.94 or sepa_vcp.get("pct_below_52w_high", 10.0) <= 6.0)
            )
            # 2. Kiểm tra xung lực ngắn hạn (MCDX Fast < Slow hoặc đang dốc xuống, RSI chưa bứt phá)
            is_momentum_lagging = (mcdx_fast < mcdx_slow or d_fast < 0.0 or rsi_d < 50.0)

            if is_near_peak_resistance:
                is_safe_entry = False
                entry_recommendation = (
                    f"CHƯA ĐẠT ĐIỂM MUA AN TOÀN / TIỆM CẬN KHÁNG CỰ ĐỈNH CŨ 🟡 ({symbol}): Thị giá ({curr_price:,.0f} đ) đang tiệm cận sát vùng cản đỉnh Pivot "
                    f"({pivot_p:,.0f} đ, chỉ cách {sepa_vcp.get('pct_below_52w_high', 0):.1f}%). Tại vùng này, cổ phiếu chưa có phiên Breakout bứt phá dứt khoát "
                    f"với khối lượng lớn xác nhận. Chỉ báo xung lực MCDX RSI SMA (đường Fast Blue = {mcdx_fast:.1f} vs Slow White = {mcdx_slow:.1f}) "
                    f"chưa hoàn tất tín hiệu giao cắt lên đồng thuận, rủi ro điều chỉnh đảo chiều tại vùng cản (Double Top / LPSY) là rất cao. "
                    f"KHUYẾN NGHỊ TỔ CHỨC: Đưa vào Watchlist quan sát, TUYỆT ĐỐI KHÔNG MUA ĐUỔI TRƯỚC CẢN! Chỉ mở vị thế khi giá vượt dứt khoát {pivot_p:,.0f} đ "
                    f"kèm thanh khoản bùng nổ, hoặc kiên nhẫn chờ nhịp chỉnh rũ bỏ về vùng hỗ trợ an toàn."
                )
            elif is_momentum_lagging and not is_confirmed_bottom_lps:
                is_safe_entry = False
                entry_recommendation = (
                    f"CHƯA ĐẠT ĐIỂM MUA AN TOÀN / XUNG LỰC NGẮN HẠN ĐANG SUY YẾU 🟡 ({symbol}): Cổ phiếu đang tích lũy lại, nhưng các đường xung lực kỹ thuật "
                    f"(MCDX Fast Blue = {mcdx_fast:.1f} vs Slow White = {mcdx_slow:.1f}, RSI = {rsi_d:.1f}) đang cắm xuống hoặc chưa cắt lên dứt khoát. "
                    f"KHUYẾN NGHỊ: Đứng ngoài quan sát, chờ đường xung lực Blue cắt lên White và dòng tiền lớn xác nhận mới giải ngân."
                )
            elif not sepa_vcp.get("vcp_detected", False) and curr_price < pivot_p * 0.995:
                is_safe_entry = False
                entry_recommendation = (
                    f"CHƯA ĐẠT ĐIỂM MUA AN TOÀN / CHỜ HOÀN TẤT NÉN VCP & ĐIỂM NỔ PIVOT 🟡 ({symbol}): Cổ phiếu đang trong nhịp tích lũy lại sau đỉnh, "
                    f"thị giá ({curr_price:,.0f} đ) vẫn nằm dưới đường Pivot cản ({pivot_p:,.0f} đ), "
                    f"mẫu hình VCP chưa nén hoàn chỉnh (độ biến động còn lớn). "
                    f"KHUYẾN NGHỊ: Đưa vào Watchlist quan sát, TUYỆT ĐỐI CHƯA MUA SỚM! Chờ điểm nổ Pivot vượt {pivot_p:,.0f} đ kèm khối lượng lớn xác nhận."
                )
            else:
                is_safe_entry = True
                entry_recommendation = (
                    f"ĐỒNG THUẬN UPTREND ĐA KHUNG THỜI GIAN (MTF ALIGNED) 🚀: Khung Tháng, Tuần và Ngày đều xác nhận sóng tăng Giai đoạn 2 "
                    f"(SEPA {sepa_vcp['sepa_score']}/8, RS Rating {rs_info['rs_rating']}/99, MCDX Banker = {mcdx_banker:.1f}). "
                    f"Điểm mua an toàn tối ưu trong vùng {final_stop_loss * 1.02:,.0f} - {curr_price:,.0f} VNĐ (Hỗ trợ POC: {poc_price:,.0f} đ). "
                    f"Tỷ lệ Lợi Nhuận / Rủi Ro (R:R) đạt chuẩn: {rr_ratio:.2f} : 1."
                )
        elif ((total_structure_score >= 3 and not is_downtrend and not is_post_peak_correction and curr_price >= sma20_d * 0.985) or is_confirmed_bottom_lps) and (mcdx_fast >= mcdx_slow or sepa_vcp.get("vcp_detected", False)):
            is_safe_entry = True
            entry_recommendation = (
                f"CẤU TRÚC TÍCH LŨY / ĐIỂM TRŨNG WYCKOFF LPS AN TOÀN 🟢: Mua thăm dò 30% vị thế quanh {curr_price:,.0f} VNĐ "
                f"(sát giá vốn tổ chức POC {poc_price:,.0f} đ, MCDX Fast = {mcdx_fast:.1f} đang hồi phục), "
                f"chờ gia tăng đủ vị thế khi bứt phá điểm Pivot {sepa_vcp['pivot_price']:,.0f} VNĐ kèm thanh khoản bùng nổ."
            )
        else:
            is_safe_entry = False
            entry_recommendation = (
                f"CHƯA XÁC NHẬN ĐỒNG THUẬN CẤU TRÚC / CHƯA CÓ ĐIỂM MUA AN TOÀN 🟡: Điểm số kỹ thuật ({total_structure_score}/10, SEPA {sepa_vcp['sepa_score']}/8, "
                f"MCDX Banker {mcdx_banker:.1f} / SMA36 {mcdx_b_sma36:.1f}, MCDX Blue {mcdx_fast:.1f} / White {mcdx_slow:.1f}). "
                f"Hội đồng khuyến nghị tiếp tục đứng ngoài quan sát, kiên nhẫn chờ tín hiệu dòng tiền bảo trợ rõ ràng."
            )

        mcdx_smc_audit = {
            "mcdx_banker": round(mcdx_banker, 2),
            "mcdx_banker_sma36": round(mcdx_b_sma36, 2),
            "mcdx_hot": round(mcdx_hot, 2),
            "mcdx_retail": round(mcdx_retail, 2),
            "mcdx_fast": round(mcdx_fast, 2),
            "mcdx_slow": round(mcdx_slow, 2),
            "d_banker": d_banker,
            "d_fast": d_fast,
            "d_rsi": d_rsi,
            "williams_r": round(williams_r, 1),
            "smc_high_60": round(smc_high_60, 0),
            "smc_low_60": round(smc_low_60, 0),
            "smc_discount_top": smc_disc_top,
            "smc_pos_pct": round(smc_pos_pct, 1),
            "is_post_peak_correction": is_post_peak_correction,
            "is_confirmed_bottom_lps": is_confirmed_bottom_lps,
        }

        return {
            "symbol": symbol,
            "status": "success",
            "current_price": curr_price,
            "curr_price": curr_price,
            "total_structure_score": total_structure_score,
            "is_safe_entry": is_safe_entry,
            "is_downtrend": is_downtrend,
            "is_post_peak_correction": is_post_peak_correction,
            "is_confirmed_bottom_lps": is_confirmed_bottom_lps,
            "mcdx_smc_audit": mcdx_smc_audit,
            "market_stage": market_stage,
            "stage_name": stage_name,
            "rs_info": rs_info,
            "sepa_vcp": sepa_vcp,
            "finrl_metrics": finrl_metrics,
            "volume_profile": {
                "poc": round(poc_price, 0),
                "vah": round(vah_price, 0),
                "val": round(val_price, 0),
                "price_vs_poc_pct": round(((curr_price - poc_price) / max(poc_price, 1)) * 100.0, 2)
            },
            "moving_averages": {
                "sma_20": sma20_d,
                "sma_50": sma50_d,
                "sma_150": sma150_d,
                "sma_200": sma200_d,
                "sma_30w": sma30_w,
                "sma_12m": sma12_m
            },
            "monthly": {
                "trend": monthly_trend,
                "score": monthly_score,
                "all_time_high": all_time_high,
                "discount_ath_pct": round(discount_from_ath, 1)
            },
            "weekly": {
                "structure": weekly_structure,
                "score": weekly_score,
                "support": major_weekly_support,
                "resistance": major_weekly_resistance
            },
            "daily": {
                "pattern": daily_pattern,
                "score": daily_score,
                "stage": stage_name,
                "range_20d_pct": round(recent_range_pct, 1),
                "rsi": round(rsi_d, 1),
                "vol_ratio": round(vol_ratio, 2)
            },
            "trade_plan": {
                "optimal_entry_zone": f"{final_stop_loss * 1.02:,.0f} - {curr_price:,.0f} VNĐ" if is_safe_entry else "KHÔNG KHUYẾN NGHỊ MUA (CẤM BẮT ĐÁY)",
                "pivot_breakout": sepa_vcp["pivot_price"],
                "structural_stop_loss": final_stop_loss,
                "stop_loss_pct": round(((final_stop_loss - curr_price) / curr_price) * 100.0, 2),
                "take_profit_target_1": target_1,
                "target_1_pct": round(((target_1 - curr_price) / curr_price) * 100.0, 2),
                "take_profit_target_2": target_2,
                "target_2_pct": round(((target_2 - curr_price) / curr_price) * 100.0, 2),
                "risk_reward_ratio": round(rr_ratio, 2),
                "recommended_shares_per_1b_nav": finrl_metrics["recommended_shares_lot100"],
                "recommended_nav_pct": finrl_metrics["recommended_nav_pct"]
            },
            "entry_recommendation": entry_recommendation
        }
