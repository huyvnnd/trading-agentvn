"""
Chief Investment Officer (CIO) & Reflection Memory Agent for Vietnam Stock Market.
Chủ tịch Hội đồng Đầu tư - Thẩm định cuối cùng sau phiên họp tranh biện 7 lượt và Hội đồng 9 Đại Kiện Tướng:
1. Ra Nghị Quyết Đầu Tư Chính Thức (Approved High Conviction / Conditional Probe / Watchlist / Strict Veto).
2. Phân bổ tỷ trọng theo Half-Kelly & Volatility-Targeting (FinRL) quy đổi ra Lô chẵn 100 CP trên sàn HOSE.
3. Thiết lập Kế hoạch Giải ngân 2 Đợt phòng vệ rủi ro T+2.5 (Tranche 1 & Tranche 2).
4. Lưu trữ Nhật ký Phản tư (Reflection Memory Loop - TradingAgents-Vn) để tự động đối chiếu hiệu quả khuyến nghị.
"""

import os
import json
from datetime import datetime
from trading_agent.debate_engine import DebateEngine
from trading_agent.self_learning_engine import SelfLearningEngine


class CIOAgent:
    def __init__(self, debate_engine: DebateEngine = None, self_learning: SelfLearningEngine = None):
        self.debate_engine = debate_engine or DebateEngine()
        self.self_learning = self_learning or SelfLearningEngine()
        self.memory_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "reflection_memory.json"))

    def cross_audit_departmental_consensus(self, symbol: str, meeting: dict = None) -> dict:
        """
        Ma Trận Kiểm Tra Rà Soát Chéo Đa Phòng Ban (Cross-Departmental Institutional Audit Matrix):
        1. Phòng Vĩ Mô & Quản Trị Rủi Ro (Macro & Risk Management)
        2. Phòng Phân Tích Cơ Bản & Định Giá (Fundamental & Valuation)
        3. Phòng Cấu Trúc Kỹ Thuật Đa Khung (Technical Structure & VSA/SMC/VCP)
        4. Hội Đồng 9 Đại Kiện Tướng Đầu Tư Thế Giới (Legendary Personas Council)
        5. Tổng Hợp & Phán Quyết Rà Soát Chéo CIO (CIO Synthesis Verdict)
        """
        if meeting is None:
            meeting = self.debate_engine.conduct_committee_meeting(symbol)

        macro = meeting.get("macro_report", {})
        fund = meeting.get("fund_report", {})
        tech = meeting.get("tech_report", {})
        risk = meeting.get("risk_report", {})
        canslim = meeting.get("canslim_report", {})
        personas = meeting.get("personas_council", [])

        sepa = tech.get("sepa_vcp", {})
        trade_p = tech.get("trade_plan", {})
        mcdx = tech.get("mcdx_smc_audit", {})
        
        curr_price = float(tech.get("current_price", 0))
        iv = float(fund.get("intrinsic_value", 0))
        mos_pct = float(fund.get("margin_of_safety_pct", 0.0))
        canslim_score = float(canslim.get("canslim_score", 50))
        stage = tech.get("market_stage", 1)
        sepa_score = sepa.get("sepa_score", 0)
        vcp_ok = sepa.get("vcp_detected", False)
        pivot = float(trade_p.get("pivot_breakout", sepa.get("pivot_price", 0)))
        
        mcdx_fast = float(mcdx.get("mcdx_fast", 15))
        mcdx_slow = float(mcdx.get("mcdx_slow", 15))

        bull_count = sum(1 for p in personas if "BULLISH" in p.get("signal", ""))
        bear_count = sum(1 for p in personas if "BEARISH" in p.get("signal", ""))

        # 1. Audit Vĩ Mô & Rủi Ro
        risk_passed = True
        risk_reasons = []
        if fund.get("delisting_risk"):
            risk_passed = False
            risk_reasons.append("Nguy cơ hủy niêm yết")
        if fund.get("is_junk"):
            risk_passed = False
            risk_reasons.append("Cổ phiếu rác đầu cơ")
        if risk.get("risk_score", 0) >= 8:
            risk_passed = False
            risk_reasons.append(f"Điểm rủi ro tổng hợp quá cao ({risk.get('risk_score', 0)}/10)")
        risk_detail = "🟢 THÔNG QUA: Không rủi ro hủy niêm yết, đệm trượt giá T+2.5 an toàn" if risk_passed else f"🔴 PHỦ QUYẾT: {', '.join(risk_reasons)}"

        # 2. Audit Cơ Bản & Định Giá
        fund_passed = True
        fund_reasons = []
        if mos_pct < -20.0 and canslim_score < 70:
            fund_passed = False
            fund_reasons.append(f"Thị giá ({curr_price:,.0f} đ) đắt hơn giá trị nội tại ({iv:,.0f} đ), MoS: {mos_pct:+.1f}% (< -20%)")
        pe = fund.get("pe_ratio")
        roe = fund.get("roe")
        if pe is not None and pe > 20.0 and roe is not None and roe < 10.0:
            fund_passed = False
            fund_reasons.append(f"P/E cao ({pe:.1f}x) trong khi ROE thấp ({roe:.1f}%)")
        fund_detail = f"🟢 THÔNG QUA: Định giá hợp lý (MoS: {mos_pct:+.1f}%), CANSLIM {canslim_score:.0f}/100" if fund_passed else f"🔴 PHỦ QUYẾT: {', '.join(fund_reasons)}"

        # 3. Audit Cấu Trúc Kỹ Thuật & VCP/Pivot
        tech_passed = True
        tech_reasons = []
        is_safe_entry = tech.get("is_safe_entry", True)
        pct_below_high = float(sepa.get("pct_below_52w_high", 10.0))
        is_near_peak_resistance = (
            curr_price < pivot * 0.995 
            and (curr_price >= pivot * 0.94 or pct_below_high <= 6.0)
        )
        if stage != 2:
            tech_passed = False
            tech_reasons.append(f"Đang ở Giai đoạn {stage} ({'Downtrend' if stage==4 else 'Tích lũy nền đáy'}) - Không phải Stage 2")
        elif sepa_score < 5 and not vcp_ok:
            tech_passed = False
            tech_reasons.append(f"SEPA chỉ đạt {sepa_score}/8 (chuẩn tối thiểu 5/8)")
        elif is_near_peak_resistance:
            tech_passed = False
            tech_reasons.append(
                f"Giá ({curr_price:,.0f} đ) đang tiệm cận sát vùng cản đỉnh Pivot ({pivot:,.0f} đ, chỉ cách {pct_below_high:.1f}%), "
                f"chưa bứt phá Breakout dứt khoát kèm thanh khoản lớn, rủi ro điều chỉnh đảo chiều tại cản"
            )
        elif not is_safe_entry:
            tech_passed = False
            tech_reasons.append("Chưa xác nhận điểm mua an toàn (xung lực MCDX/RSI chưa đồng thuận cắt lên hoặc chưa nổ Pivot)")
        elif not vcp_ok and curr_price < pivot * 0.995 and mcdx_fast < mcdx_slow:
            tech_passed = False
            tech_reasons.append(f"Giá ({curr_price:,.0f} đ) nằm dưới Pivot ({pivot:,.0f} đ), VCP chưa nén xong, MCDX Blue ({mcdx_fast:.1f}) < White ({mcdx_slow:.1f})")
        tech_detail = f"🟢 THÔNG QUA: Stage 2 Uptrend, SEPA {sepa_score}/8, RS {tech.get('rs_info', {}).get('rs_rating', 50)}/99" if tech_passed else f"🔴 TẠM DỪNG: {', '.join(tech_reasons)}"

        # 4. Audit Hội Đồng 9 Đại Kiện Tướng
        council_passed = True
        council_reasons = []
        if bear_count >= 4:
            council_passed = False
            council_reasons.append(f"Đa số áp đảo phản đối ({bear_count}/9 Kiện tướng Bearish: Buffett, Munger, Graham, Lynch, Damodaran)")
        elif bear_count > bull_count and mos_pct < 0:
            council_passed = False
            council_reasons.append(f"Phe Bear ({bear_count}) áp đảo phe Bull ({bull_count}) trong khi MoS âm ({mos_pct:+.1f}%)")
        council_detail = f"🟢 THÔNG QUA: {bull_count}/9 Kiện tướng ủng hộ, chỉ {bear_count} phản đối" if council_passed else f"🔴 PHỦ QUYẾT: {', '.join(council_reasons)}"

        # 5. Tổng Hợp Rà Soát Chéo CIO (Synthesis Verdict)
        all_passed = risk_passed and fund_passed and tech_passed and council_passed

        if all_passed:
            target_tier = 1
            verdict = "PHÊ DUYỆT ĐẦU TƯ MUA (TIER 1 CHUẨN ĐIỂM MUA)"
            verdict_color = "#00c853"
            summary = "100% các phòng ban (Vĩ mô, Định giá, Kỹ thuật VCP, Hội đồng 9 Kiện tướng) đều đồng thuận thông qua không có phủ quyết."
        elif stage == 4 or not risk_passed:
            target_tier = 3
            verdict = "PHỦ QUYẾT TUYỆT ĐỐI / CẤM MUA (TIER 3 DOWNTREND RỦI RO)"
            verdict_color = "#d50000"
            summary = "Vi phạm nghiêm trọng nguyên tắc bảo toàn vốn tổ chức (Downtrend Stage 4 hoặc rủi ro hủy niêm yết)."
        else:
            target_tier = 2
            verdict = "BÁC BỎ ĐỀ XUẤT MUA -> ĐƯA VÀO DANH MỤC THEO DÕI QUAN SÁT (TIER 2 WATCHLIST - 0% NAV)"
            verdict_color = "#ffa726"
            fails = []
            if not fund_passed: fails.append("Cơ bản & Định giá quá đắt")
            if not tech_passed: fails.append("Kỹ thuật kẹt dưới Pivot/Chưa nén VCP")
            if not council_passed: fails.append(f"Hội đồng 9 Kiện tướng bất đồng ({bear_count} Bearish)")
            summary = f"Chưa đạt đồng thuận liên phòng ban: {', '.join(fails)}. Bắt buộc đứng ngoài 100% tiền mặt theo dõi."

        return {
            "symbol": symbol,
            "is_buy_approved": all_passed,
            "target_tier": target_tier,
            "verdict": verdict,
            "verdict_color": verdict_color,
            "summary": summary,
            "departments": {
                "macro_risk": {"passed": risk_passed, "title": "🌐 Vĩ Mô & Quản Trị Rủi Ro", "detail": risk_detail},
                "fundamental_valuation": {"passed": fund_passed, "title": "🏢 Phân Tích Cơ Bản & Định Giá", "detail": fund_detail},
                "technical_structure": {"passed": tech_passed, "title": "📐 Cấu Trúc Kỹ Thuật Đa Khung & VCP", "detail": tech_detail},
                "personas_council": {"passed": council_passed, "title": "🌟 Hội Đồng 9 Đại Kiện Tướng", "detail": council_detail},
            }
        }

    def evaluate_and_decide(self, symbol: str) -> dict:
        meeting = self.debate_engine.conduct_committee_meeting(symbol)

        macro = meeting["macro_report"]
        fund = meeting["fund_report"]
        tech = meeting["tech_report"]
        sentiment = meeting["sentiment_report"]
        risk = meeting["risk_report"]
        canslim = meeting.get("canslim_report", {})
        personas = meeting.get("personas_council", [])

        finrl = tech.get("finrl_metrics", {})
        sepa = tech.get("sepa_vcp", {})
        rs_info = tech.get("rs_info", {})
        vp = tech.get("volume_profile", {})
        trade_p = tech.get("trade_plan", {})

        bull_count = sum(1 for p in personas if "BULLISH" in p.get("signal", ""))
        bear_count = sum(1 for p in personas if "BEARISH" in p.get("signal", ""))
        canslim_score = canslim.get("canslim_score", 50)
        mos_pct = fund.get("margin_of_safety_pct", 0.0)
        iv = fund.get("intrinsic_value", 0.0)

        # 0. MA TRẬN RÀ SOÁT CHÉO ĐA PHÒNG BAN (CROSS-AUDIT CONSENSUS)
        cross_audit = self.cross_audit_departmental_consensus(symbol, meeting=meeting)

        # 0B. KIỂM DUYỆT QUA BỘ NHỚ TỰ HỌC & GHI NHỚ SAI LẦM (SELF-LEARNING MEMORY ENGINE)
        sl_audit = self.self_learning.apply_learned_rules_to_decision(
            symbol=symbol,
            fund_report=fund,
            tech_report=tech,
            sentiment_report=sentiment,
            raw_composite_score=float(canslim_score),
        )
        sl_lessons_text = (
            " " + " | ".join(sl_audit["triggered_lessons"])
            if sl_audit.get("triggered_lessons")
            else ""
        )

        # 1. KIỂM TRA QUYỀN PHỦ QUYẾT TUYỆT ĐỐI (STRICT VETO POWER)
        if tech.get("is_downtrend") or tech.get("market_stage") == 4:
            final_decision = "TỪ CHỐI ĐẦU TƯ / CẢNH BÁO DOWNTREND GIAI ĐOẠN 4 ❌"
            decision_color = "#d50000"
            conviction_score = 0
            allocation_pct = 0
            lot100_shares = 0
            action_plan = (
                f"Chủ tịch Hội đồng Đầu tư (CIO) PHỦ QUYẾT TUYỆT ĐỐI đề xuất giải ngân cho mã {symbol}. "
                f"Lý do: Cổ phiếu đang nằm trong chu kỳ suy thoái Giai đoạn 4 theo lý thuyết Stan Weinstein & Mark Minervini "
                f"(Thị giá {tech.get('current_price', 0):,.0f} đ nằm dưới SMA50 {tech.get('moving_averages', {}).get('sma_50', 0):,.0f} đ "
                f"và SMA200 {tech.get('moving_averages', {}).get('sma_200', 0):,.0f} đ; SEPA chỉ đạt {sepa.get('sepa_score', 0)}/8; "
                f"RS Rating = {rs_info.get('rs_rating', 20)}/99; {bear_count}/9 Đại kiện tướng phản đối). "
                f"Lượng cung treo lơ lửng tại vùng giá vốn POC ({vp.get('poc', 0):,.0f} đ) vô cùng lớn. "
                f"NGUYÊN TẮC SỐNG CÒN CỦA QUỸ TỔ CHỨC: TUYỆT ĐỐI KHÔNG BẮT ĐÁY DAO RƠI!{sl_lessons_text}"
            )
            tranches = []

        elif fund.get("is_junk") or fund.get("delisting_risk") or risk.get("risk_score", 0) >= 7 or sl_audit.get("veto_buy"):
            veto_tag = " (VETO TỪ BỘ NHỚ TỰ HỌC)" if sl_audit.get("veto_buy") else ""
            if tech.get("market_stage") == 1 and not fund.get("delisting_risk") and not fund.get("is_junk"):
                final_decision = f"TẠM DỪNG GIẢI NGÂN / THEO DÕI CHẶT CHẼ TRONG WATCHLIST{veto_tag} 🟡"
                decision_color = "#ffa726"
                conviction_score = 2
                allocation_pct = 0
                lot100_shares = 0
                action_plan = (
                    f"Hội đồng Đầu tư (CIO) QUYẾT ĐỊNH ĐỨNG NGOÀI / ĐƯA VÀO DANH MỤC THEO DÕI QUAN SÁT (WATCHLIST) cho mã {symbol}. "
                    f"Lý do: Cổ phiếu đang tích lũy Giai đoạn 1 nhưng các chỉ số an toàn vốn chưa đạt chuẩn "
                    f"({', '.join(risk.get('critical_warnings', ['Cấu trúc cơ bản/kỹ thuật cần thêm thời gian tích lũy']))}). "
                    f"Ưu tiên số 1 là bảo toàn vốn, phân bổ 0% NAV cho đến khi xuất hiện phiên bùng nổ xác nhận Giai đoạn 2.{sl_lessons_text}"
                )
            else:
                final_decision = f"TỪ CHỐI ĐẦU TƯ / BẢO VỆ VỐN TUYỆT ĐỐI{veto_tag} ❌"
                decision_color = "#d50000"
                conviction_score = 0
                allocation_pct = 0
                lot100_shares = 0
                action_plan = (
                    f"Chủ tịch Hội đồng Đầu tư PHỦ QUYẾT đề xuất giải ngân cho mã {symbol}. "
                    f"Lý do: Cổ phiếu vi phạm tiêu chuẩn an toàn vốn tổ chức "
                    f"({', '.join(risk.get('critical_warnings', ['Rủi ro cơ bản/kỹ thuật cao']))}). "
                    f"Ưu tiên số 1 là bảo toàn vốn, đứng ngoài 100%.{sl_lessons_text}"
                )
            tranches = []

        # 3. GIAI ĐOẠN 1 TÍCH LŨY (STAN WEINSTEIN & MARK MINERVINI STAGE 1)
        # Bắt buộc đưa vào Watchlist, TUYỆT ĐỐI KHÔNG GIẢI NGÂN (0% NAV) khi chưa có điểm nổ bứt phá Stage 2!
        elif tech.get("market_stage") == 1:
            final_decision = "TẠM DỪNG / ĐƯA VÀO DANH MỤC THEO DÕI QUAN SÁT (STAGE 1 TÍCH LŨY) 🟡"
            decision_color = "#ffa726"
            conviction_score = 4
            allocation_pct = 0
            lot100_shares = 0
            action_plan = (
                f"Cổ phiếu {symbol} đang trong Giai đoạn 1 Tích lũy (Stage 1 Base Accumulation) theo Stan Weinstein & Mark Minervini. "
                f"Giá trị nội tại ước tính {iv:,.0f} đ (MoS: {mos_pct:+.1f}%), CANSLIM {canslim_score}/100, SEPA {sepa.get('sepa_score', 0)}/8. "
                f"HỘI ĐỒNG ĐẦU TƯ ĐỒNG THUẬN: Đưa mã {symbol} vào DANH MỤC THEO DÕI QUAN SÁT (WATCHLIST), CHƯA PHÊ DUYỆT GIẢI NGÂN (0% NAV). "
                f"Nhà đầu tư kiên nhẫn quan sát, chờ giá bứt phá vượt cản POC ({vp.get('poc', 0):,.0f} đ) kèm dòng tiền tạo lập xác nhận mới mở vị thế.{sl_lessons_text}"
            )
            tranches = []

        elif not tech.get("is_safe_entry") or tech.get("is_post_peak_correction") or tech.get("total_structure_score", 0) <= 0:
            mcdx_audit = tech.get("mcdx_smc_audit", {})
            b_val = mcdx_audit.get("mcdx_banker", 0.0)
            b_sma36 = mcdx_audit.get("mcdx_banker_sma36", 0.0)
            f_val = mcdx_audit.get("mcdx_fast", 0.0)
            s_val = mcdx_audit.get("mcdx_slow", 0.0)
            smc_hi = mcdx_audit.get("smc_high_60", 0.0)
            smc_lo = mcdx_audit.get("smc_low_60", 0.0)
            smc_disc = mcdx_audit.get("smc_discount_top", 0.0)
            sma20_v = tech.get("moving_averages", {}).get("sma_20", 0.0)
            sma200_v = tech.get("moving_averages", {}).get("sma_200", 0.0)

            if tech.get("is_post_peak_correction"):
                final_decision = "TẠM DỪNG GIẢI NGÂN / CHƯA CÓ ĐIỂM MUA BẮT ĐÁY AN TOÀN (ĐANG ĐIỀU CHỈNH SAU ĐỈNH) 🟠"
                decision_color = "#f97316"
                conviction_score = 3
                allocation_pct = 0
                lot100_shares = 0
                action_plan = (
                    f"Chủ tịch Hội đồng Đầu tư (CIO) KHUYẾN NGHỊ ĐỨNG NGOÀI / TUYỆT ĐỐI CHƯA BẮT ĐÁY SỚM đối với mã {symbol}. "
                    f"Đối chứng biểu đồ kỹ thuật thực tế: Cổ phiếu vừa tạo đỉnh tại vùng cung SMC Premium ({smc_hi:,.0f} đ) kèm tín hiệu phân phối SELL/LPSY, "
                    f"hiện giá ({tech.get('current_price', 0):,.0f} đ) đã gãy dưới đường SMA20 ({sma20_v:,.0f} đ). "
                    f"Chỉ báo dòng tiền tạo lập MCDX Banker tụt xuống {b_val:.1f} (nằm dưới đường trung bình SMA36 = {b_sma36:.1f}), "
                    f"đường xung lực MCDX Fast (Blue = {f_val:.1f}) lao dốc dưới Slow (White = {s_val:.1f}), RSI(14) = {tech.get('daily', {}).get('rsi', 50):.1f}. "
                    f"Về cơ bản & định giá: Giá trị hợp lý {iv:,.0f} đ (Biên an toàn MoS: {mos_pct:+.1f}%), Điểm CANSLIM {canslim_score}/100. "
                    f"KẾT LUẬN: Hoàn toàn chưa có điểm mua bắt đáy an toàn! Kiên nhẫn chờ giá lùi về vùng hỗ trợ cứng SMA200 ({sma200_v:,.0f} đ) / SMC Discount ({smc_lo:,.0f} - {smc_disc:,.0f} đ) "
                    f"kèm nến rút chân xanh và đường MCDX Blue cắt lên White mới giải ngân.{sl_lessons_text}"
                )
            else:
                final_decision = "TẠM DỪNG / ĐƯA VÀO WATCHLIST CHỜ XÁC NHẬN TẠO ĐÁY 🟡"
                decision_color = "#ffa726"
                conviction_score = 4
                allocation_pct = 0
                lot100_shares = 0
                action_plan = (
                    f"Cổ phiếu {symbol} có Giá trị nội tại ước tính {iv:,.0f} đ (MoS: {mos_pct:+.1f}%), Điểm CANSLIM {canslim_score}/100, "
                    f"nhưng cấu trúc kỹ thuật ngắn hạn chưa đồng thuận (SEPA {sepa.get('sepa_score', 0)}/8, MCDX Banker {b_val:.1f}/SMA36 {b_sma36:.1f}, MCDX Blue {f_val:.1f}/White {s_val:.1f}). "
                    f"Hội đồng quyết định CHƯA GIẢI NGÂN vội, chờ giá lấy lại đường SMA20 ({sma20_v:,.0f} đ) / POC ({vp.get('poc', 0):,.0f} đ) và MCDX Blue vòng lên kèm thanh khoản xác nhận.{sl_lessons_text}"
                )
            tranches = []

        # 4. KIỂM TRA BẤT ĐỒNG Ý KIẾN HỘI ĐỒNG & BẪY ĐỊNH GIÁ CAO (PERSONAS MAJORITY BEARISH & NEGATIVE MOS)
        elif bear_count >= 4 or (bear_count > bull_count and mos_pct < 0):
            final_decision = "TẠM DỪNG GIẢI NGÂN / THEO DÕI QUAN SÁT (HỘI ĐỒNG BẤT ĐỒNG & ĐỊNH GIÁ CAO) 🟡"
            decision_color = "#ffa726"
            conviction_score = 4
            allocation_pct = 0
            lot100_shares = 0
            action_plan = (
                f"Chủ tịch Hội đồng Đầu tư (CIO) PHẢN BIỆN & ĐỒNG THUẬN VỚI HỘI ĐỒNG 9 ĐẠI KIỆN TƯỚNG: TẠM DỪNG GIẢI NGÂN cho mã {symbol} (0% NAV). "
                f"Lý do cốt lõi: Đa số áp đảo Hội đồng thẩm định phản đối ({bear_count}/9 Đại kiện tướng Bearish, {bull_count}/9 Bullish). "
                f"Các bậc thầy giá trị & định giá (Buffett, Munger, Graham, Lynch, Damodaran) cảnh báo định giá đã quá cao so với giá trị thực "
                f"(Thị giá {tech.get('current_price', 0):,.0f} đ vs Giá trị nội tại {iv:,.0f} đ, Biên an toàn MoS: {mos_pct:+.1f}%, CANSLIM {canslim_score}/100). "
                f"Về kỹ thuật: Cổ phiếu chưa nén xong mẫu hình VCP và thị giá vẫn nằm dưới điểm nổ Pivot ({trade_p.get('pivot_breakout', 0):,.0f} đ). "
                f"QUY TẮC BẢO VỆ VỐN TỔ CHỨC: Tuyệt đối không giải ngân khi Hội đồng chưa đạt đồng thuận và định giá đã căng cứng. Đưa vào Watchlist tiếp tục theo dõi.{sl_lessons_text}"
            )
            tranches = []

        # 5. KIỂM TRA TRẦN ĐỊNH GIÁ CĂNG CỨNG (SEVERELY OVERVALUED: MOS <= -25%)
        elif mos_pct <= -25.0 and not (sepa.get("vcp_detected") and tech.get("current_price", 0) >= trade_p.get("pivot_breakout", 0) * 0.995):
            final_decision = "TẠM DỪNG GIẢI NGÂN / ĐỊNH GIÁ QUÁ CAO SO VỚI NỘI TẠI (MoS < -25%) 🟡"
            decision_color = "#ffa726"
            conviction_score = 4
            allocation_pct = 0
            lot100_shares = 0
            action_plan = (
                f"Chủ tịch Hội đồng Đầu tư (CIO) QUYẾT ĐỊNH ĐỨNG NGOÀI (0% NAV) cho mã {symbol}. "
                f"Lý do: Định giá thị trường ({tech.get('current_price', 0):,.0f} đ) đã chạy vượt xa giá trị nội tại ước tính ({iv:,.0f} đ) "
                f"với Biên an toàn âm nặng (MoS = {mos_pct:+.1f}%). Đồng thời mẫu hình VCP chưa hoàn tất điểm nổ Pivot ({trade_p.get('pivot_breakout', 0):,.0f} đ). "
                f"Hội đồng kiên quyết không mua đuổi ở vùng định giá đắt đỏ rủi ro cao, đưa mã vào Watchlist kiên nhẫn quan sát.{sl_lessons_text}"
            )
            tranches = []

        elif (tech.get("total_structure_score", 0) >= 5 or sepa.get("sepa_score", 0) >= 6) and fund.get("fundamental_score", 0) >= 2 and mos_pct >= -15.0 and tech.get("market_stage") == 2 and bull_count >= 3 and bear_count <= 2:
            final_decision = "PHÊ DUYỆT ĐẦU TƯ MẠNH (HIGH CONVICTION STAGE 2) 🚀"
            decision_color = "#00c853"
            conviction_score = min(10, 7 + (1 if sepa.get("sepa_score", 0) >= 7 else 0) + (1 if bull_count >= 5 else 0) + (1 if mos_pct >= 10 else 0))
            rec_nav = finrl.get("recommended_nav_pct", 20.0)
            allocation_pct = int(min(macro["recommended_allocation"]["equity_pct"] // 3, max(15, round(rec_nav))))
            lot100_shares = int((1_000_000_000 * (allocation_pct / 100.0)) // max(tech.get("current_price", 10000), 1000) // 100) * 100
            action_plan = (
                f"Hội đồng Đầu tư đồng thuận cao ({bull_count}/9 Đại kiện tướng ủng hộ, CANSLIM {canslim_score}/100 - Hạng {canslim.get('canslim_grade', 'B')}, "
                f"SEPA {sepa.get('sepa_score', 0)}/8, RS Rating {rs_info.get('rs_rating', 50)}/99). "
                f"Giá trị hợp lý đa mô hình đạt {iv:,.0f} đ/CP (MoS {mos_pct:+.1f}%). "
                f"Chấp thuận giải ngân tối đa {allocation_pct}% NAV (~{lot100_shares:,} CP trên mỗi 1 tỷ VNĐ vốn) chia làm 2 đợt chuẩn T+2.5."
            )
            tranches = [
                f"Đợt 1 (50% vị thế ~ {lot100_shares // 2:,} CP): Mua gom tại nền an toàn {trade_p.get('optimal_entry_zone', 'N/A')} (quanh hỗ trợ POC {vp.get('poc', 0):,.0f} đ).",
                f"Đợt 2 (50% vị thế ~ {lot100_shares - lot100_shares // 2:,} CP): Giải ngân nốt sau khi hàng Đợt 1 về tài khoản (T+2.5) và giá bứt phá vượt điểm nổ Pivot {trade_p.get('pivot_breakout', 0):,.0f} đ kèm Vol ≥ 1.4x TB20.",
                f"Kỷ luật Bảo vệ vốn: Đặt Stop Loss cứng tại {trade_p.get('structural_stop_loss', 0):,.0f} đ ({trade_p.get('stop_loss_pct', -7):+.1f}%). Chốt lời TP1 tại {trade_p.get('take_profit_target_1', 0):,.0f} đ (+{trade_p.get('target_1_pct', 15):.1f}%)."
            ]

        elif tech.get("market_stage") == 2 and tech.get("is_safe_entry") and bull_count >= 1 and bear_count <= 2 and mos_pct >= -25.0:
            final_decision = "PHÊ DUYỆT MUA THĂM DÒ NỀN GIÁ (PROBATIONARY BUY) 🟢"
            decision_color = "#66bb6a"
            conviction_score = 6
            allocation_pct = 12
            lot100_shares = int((1_000_000_000 * (allocation_pct / 100.0)) // max(tech.get("current_price", 10000), 1000) // 100) * 100
            action_plan = (
                f"Hội đồng Đầu tư phê duyệt giải ngân thăm dò có điều kiện ({bull_count}/9 Đại kiện tướng tích cực, CANSLIM {canslim_score}/100, "
                f"R:R = {trade_p.get('risk_reward_ratio', 2.5):.2f} : 1). "
                f"Phân bổ thận trọng {allocation_pct}% NAV (~{lot100_shares:,} CP / 1 tỷ NAV), tuân thủ nghiêm ngặt ngưỡng dừng lỗ cấu trúc."
            )
            tranches = [
                f"Đợt 1 (Thăm dò {allocation_pct}% NAV ~ {lot100_shares:,} CP): Giải ngân trong vùng {trade_p.get('optimal_entry_zone', 'N/A')} sát vùng giá vốn POC ({vp.get('poc', 0):,.0f} đ).",
                f"Kỷ luật Bảo vệ vốn: Cắt lỗ khi thủng {trade_p.get('structural_stop_loss', 0):,.0f} đ (-{trade_p.get('stop_loss_pct', 7.0):.1f}%)."
            ]

        else:
            final_decision = "TẠM DỪNG / ĐƯA VÀO DANH MỤC THEO DÕI QUAN SÁT (WATCHLIST) 🟡"
            decision_color = "#ffa726"
            conviction_score = 4
            allocation_pct = 0
            lot100_shares = 0
            action_plan = (
                f"Cổ phiếu {symbol} chưa đáp ứng đầy đủ tiêu chuẩn bứt phá Giai đoạn 2 của Hội đồng Đầu tư. "
                f"Hội đồng quyết định phân bổ 0% NAV, đưa vào Watchlist tiếp tục quan sát tại hỗ trợ POC ({vp.get('poc', 0):,.0f} đ).{sl_lessons_text}"
            )
            tranches = []

        result = {
            "symbol": symbol,
            "final_decision": final_decision,
            "decision_color": decision_color,
            "conviction_score": conviction_score,
            "allocation_pct": allocation_pct,
            "recommended_shares_per_1b": lot100_shares,
            "action_plan": action_plan,
            "tranches": tranches,
            "trade_plan": trade_p,
            "self_learning_audit": sl_audit,
            "cross_audit": cross_audit,
            "meeting": meeting
        }

        self._record_reflection_memory(result)
        return result

    def _record_reflection_memory(self, decision_res: dict):
        """Ghi nhận quyết định của CIO vào bộ nhớ phản tư (Reflection Memory) để đánh giá hậu kiểm."""
        try:
            os.makedirs(os.path.dirname(self.memory_file), exist_ok=True)
            history = []
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            if not isinstance(history, list):
                history = []

            tech = decision_res["meeting"]["tech_report"]
            fund = decision_res["meeting"]["fund_report"]
            canslim = decision_res["meeting"].get("canslim_report", {})

            entry = {
                "timestamp": decision_res["meeting"]["meeting_time"],
                "symbol": decision_res["symbol"],
                "price_at_decision": tech.get("current_price", 0),
                "stage": tech.get("stage_name", ""),
                "sepa_score": tech.get("sepa_vcp", {}).get("sepa_score", 0),
                "rs_rating": tech.get("rs_info", {}).get("rs_rating", 50),
                "canslim_score": canslim.get("canslim_score", 0),
                "intrinsic_value": fund.get("intrinsic_value", 0),
                "final_decision": decision_res["final_decision"],
                "conviction_score": decision_res["conviction_score"],
                "allocation_pct": decision_res["allocation_pct"],
                "stop_loss": decision_res["trade_plan"].get("structural_stop_loss", 0),
                "target_tp1": decision_res["trade_plan"].get("take_profit_target_1", 0)
            }

            # Update existing recent entry for same symbol on same day or prepend
            today_prefix = entry["timestamp"][:10]
            history = [
                h for h in history
                if not (h.get("symbol") == entry["symbol"] and str(h.get("timestamp", "")).startswith(today_prefix))
            ]
            history.insert(0, entry)
            history = history[:50]

            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_reflection_log(self, data_engine=None) -> list:
        """Đọc nhật ký phản tư và tự động cập nhật hiệu suất thực tế so với giá hiện tại."""
        if not os.path.exists(self.memory_file):
            return []
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            if data_engine is not None and history:
                syms = list(set([h.get("symbol") for h in history if h.get("symbol")]))
                pb = data_engine.get_batch_price_board(syms)
                for h in history:
                    sym = h.get("symbol")
                    p_dec = float(h.get("price_at_decision", 0))
                    p_now = float(pb.get(sym, {}).get("price", p_dec)) if sym in pb else p_dec
                    h["current_price"] = p_now
                    if p_dec > 0:
                        diff_pct = round((p_now - p_dec) / p_dec * 100.0, 2)
                        h["return_since_decision_pct"] = diff_pct
                        if "TỪ CHỐI" in h.get("final_decision", ""):
                            h["reflection_audit"] = f"✅ Đã bảo vệ vốn thành công ({diff_pct:+.2f}%)" if diff_pct <= 0 else f"Quan sát ({diff_pct:+.2f}%)"
                        else:
                            h["reflection_audit"] = f"🟢 Đang sinh lời ({diff_pct:+.2f}%)" if diff_pct >= 0 else f"🟡 Đang rung lắc ({diff_pct:+.2f}%)"
            return history
        except Exception:
            return []
