"""
3-Posture Risk Management Team & Chief Risk Officer (CRO) Agent (TauricResearch/TradingAgents + FinRL).
Triển khai mô hình Quản trị Rủi ro 3 Tư Thế (3-Posture Risk Debate) kết hợp Đặc thù T+2.5 Việt Nam:
1. Aggressive Risk Analyst (Tư thế Tấn công): Tối ưu hóa động lượng & lãi kép Kelly khi hội tụ SEPA/VCP.
2. Neutral Risk Analyst (Tư thế Cân bằng): Cân đối tỷ lệ Sharpe, Sortino, R:R và trượt giá T+2.5.
3. Conservative Risk Analyst / CRO (Tư thế Phòng thủ Bảo toàn vốn): Quyền phủ quyết tuyệt đối (Veto) với Stage 4 Downtrend, Cổ phiếu Rác, Thanh khoản kém hoặc Turbulence cao.
"""


class RiskAgent:
    def __init__(self, data_engine=None):
        self.de = data_engine

    def assess_investment_risk(self, symbol: str, fund_data: dict, tech_data: dict, macro_data: dict) -> dict:
        symbol = symbol.strip().upper()
        risk_score = 0
        critical_warnings = []
        bearish_arguments = []

        finrl = tech_data.get("finrl_metrics", {})
        sepa = tech_data.get("sepa_vcp", {})
        rs_info = tech_data.get("rs_info", {})
        trade_plan = tech_data.get("trade_plan", {})

        # 1. Thẩm định rủi ro Cổ phiếu Rác & Thanh khoản
        if fund_data.get("is_junk"):
            risk_score += 5
            critical_warnings.append("CẢNH BÁO CỔ PHIẾU RÁC: Thanh khoản quá kém hoặc thị giá Penny, không đáp ứng tiêu chuẩn quản trị rủi ro tổ chức.")

        if fund_data.get("delisting_risk"):
            risk_score += 5
            critical_warnings.append("CẢNH BÁO HỦY NIÊM YẾT: Doanh nghiệp thua lỗ bào mòn vốn, có nguy cơ bị đình chỉ hoặc hủy niêm yết bắt buộc.")

        # 2. Thẩm định rủi ro Xu hướng Downtrend Giai đoạn 4 (Stan Weinstein & Minervini)
        if tech_data.get("is_downtrend") or tech_data.get("market_stage") == 4 or tech_data.get("total_structure_score", 0) <= -3:
            risk_score += 7
            critical_warnings.append(
                f"CẢNH BÁO DOWNTREND GIAI ĐOẠN 4: Cổ phiếu {symbol} đang trong chu kỳ giảm giá dài hạn "
                f"({tech_data.get('stage_name', 'Stage 4 Downtrend')}). "
                f"Nằm dưới các đường trung bình lớn (SMA50, SMA200), SEPA chỉ đạt {sepa.get('sepa_score', 0)}/8, RS Rating = {rs_info.get('rs_rating', 20)}/99. "
                f"TUYỆT ĐỐI CẤM MUA BẮT ĐÁY!"
            )
            bearish_arguments.append("Bắt dao rơi trong Giai đoạn 4 Downtrend vi phạm kỷ luật sống còn của quỹ tổ chức; rủi ro kẹt hàng T+2.5 cực đại.")

        # 3. Thẩm định KQKD suy giảm & Định giá
        p_growth = fund_data.get("profit_growth_yoy")
        if p_growth is not None and p_growth < -15.0:
            risk_score += 2
            bearish_arguments.append(f"Lợi nhuận sau thuế suy giảm mạnh ({p_growth:+.1f}% YoY), thiếu động lực cơ bản nâng đỡ giá.")

        mos_pct = fund_data.get("margin_of_safety_pct", 0.0)
        pe = fund_data.get("pe")
        if pe is not None and pe > 25.0 and mos_pct < -15.0:
            risk_score += 2
            bearish_arguments.append(f"Định giá P/E ({pe:.1f}x) vượt xa giá trị nội tại Damodaran/Graham (MoS = {mos_pct:+.1f}%).")

        sl_pct = abs(trade_plan.get("stop_loss_pct", 7.0))
        rr_ratio = trade_plan.get("risk_reward_ratio", 2.5)
        if not tech_data.get("is_safe_entry", True) and not tech_data.get("is_downtrend"):
            risk_score += 3
            bearish_arguments.append("Cấu trúc kỹ thuật chưa xác nhận đồng thuận đa khung thời gian; vào lệnh sớm dễ bị chôn vốn hoặc quét Stop Loss T+2.5.")

        # 4. Thẩm định Vĩ mô & Chỉ số Hỗn loạn FinRL
        macro_score = macro_data.get("macro_score", 0)
        turb = macro_data.get("domestic_data", {}).get("turbulence_index", 1.0)
        if macro_score < 0 or turb >= 2.5:
            risk_score += 2
            bearish_arguments.append(f"Bối cảnh thị trường chung tiềm ẩn biến động (Turbulence Index = {turb:.2f}), cần dự phòng thanh khoản tiền mặt.")

        # 5. Đánh giá 3 Tư Thế Quản Trị Rủi Ro (TauricResearch/TradingAgents 3-Posture Risk Team)
        is_dt = tech_data.get("is_downtrend", False)
        rec_nav = finrl.get("recommended_nav_pct", 0.0)
        rec_shares = finrl.get("recommended_shares_per_1b_nav", finrl.get("recommended_shares_lot100", 0))

        posture_debates = {
            "aggressive": (
                f"🔥 **Chuyên Gia Rủi Ro Tấn Công (Aggressive Posture):** "
                + (
                    f"Cổ phiếu đang ở Giai đoạn 4 Downtrend (RS = {rs_info.get('rs_rating', 0)}/99). Ngay cả khẩu vị rủi ro cao nhất cũng TỪ CHỐI GIẢI NGÂN 0% vì xác suất thắng quá thấp!"
                    if is_dt
                    else f"Với SEPA đạt {sepa.get('sepa_score', 0)}/8 và R:R = {rr_ratio:.2f}:1, đề xuất phân bổ tối đa theo Half-Kelly ({finrl.get('half_kelly_pct', 15.0):.1f}% NAV ~ {rec_shares:,} CP/1 tỷ NAV) để tối đa hóa lãi kép khi vượt Pivot {sepa.get('pivot_price', 0):,.0f} đ."
                )
            ),
            "neutral": (
                f"⚖️ **Chuyên Gia Rủi Ro Cân Bằng (Neutral Posture):** "
                + (
                    "Đồng thuận đứng ngoài 100% tiền mặt với mã này, chuyển vốn sang các cổ phiếu dẫn dắt Giai đoạn 2."
                    if is_dt
                    else f"Xét đến độ trễ thanh toán T+2.5 tại Việt Nam (rủi ro hiệu dụng {finrl.get('t25_effective_risk_pct', 6.5):.1f}%/lệnh, Sharpe = {finrl.get('sharpe_ratio', 0):.2f}, Max Drawdown = {finrl.get('max_drawdown_pct', 0):.1f}%), khuyến nghị chia làm 2 đợt giải ngân với tổng tỷ trọng chuẩn {rec_nav:.1f}% NAV."
                )
            ),
            "conservative": (
                f"🛡️ **Giám Đốc Bảo Toàn Vốn (Conservative CRO Posture):** "
                + (
                    f"KÍCH HOẠT QUYỀN PHỦ QUYẾT (VETO): Nghiêm cấm mua bắt đáy khi giá nằm dưới SMA200 và SMA50. Bảo vệ vốn tuyệt đối!"
                    if is_dt or risk_score >= 7
                    else f"Yêu cầu đặt lệnh dừng lỗ cứng tại {trade_plan.get('structural_stop_loss', 0):,.0f} đ (-{sl_pct:.1f}%). Tuyệt đối không bình quân giá xuống nếu thủng vùng giá vốn POC ({tech_data.get('volume_profile', {}).get('poc', 0):,.0f} đ)."
                )
            )
        }

        if risk_score >= 7:
            risk_level = "RỦI RO CỰC KỲ CAO (EXTREME RISK - VETO) ⛔"
            verdict = "PHẢN ĐỐI ĐẦU TƯ - RỦI RO VƯỢT QUÁ KHẢ NĂNG BẢO TOÀN VỐN"
            max_position_size = "0% (CẤM GIẢI NGÂN)"
        elif risk_score >= 4:
            risk_level = "RỦI RO TRUNG BÌNH (MODERATE RISK) ⚠️"
            verdict = "CHẤP NHẬN THĂM DÒ CÓ ĐIỀU KIỆN - BẮT BUỘC TUÂN THỦ STOP LOSS"
            max_position_size = f"10% - 15% TỔNG DANH MỤC (~{max(100, rec_shares // 2):,} CP / 1 tỷ NAV)"
        else:
            risk_level = "RỦI RO TRONG TẦM KIỂM SOÁT (LOW RISK) 🛡️"
            verdict = "ỦNG HỘ ĐẦU TƯ - ĐỦ ĐIỀU KIỆN AN TOÀN THEO CHUẨN TỔ CHỨC"
            max_position_size = f"{max(15.0, rec_nav):.1f}% TỔNG DANH MỤC (~{rec_shares:,} CP / 1 tỷ NAV)"

        return {
            "symbol": symbol,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "bear_verdict": verdict,
            "max_position_size": max_position_size,
            "critical_warnings": critical_warnings,
            "bearish_arguments": bearish_arguments,
            "posture_debates": posture_debates,
            "stop_loss_pct": sl_pct
        }
