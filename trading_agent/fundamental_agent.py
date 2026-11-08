"""
Fundamental & Corporate Audit Agent for Vietnam Stock Market.
Thẩm định BCTC chuyên sâu theo chuẩn FinRobot + Damodaran + Graham + Lynch:
1. Phân tích DuPont 3 Bước (Biên lợi nhuận ròng × Vòng quay tài sản × Đòn bẩy tài chính).
2. Phân nhánh chuyên biệt Ngân hàng (NIM, CIR, LDR, Tăng trưởng tín dụng, P/B-ROE) vs Phi Tài Chính (Gross/Net Margin, EV/EBITDA, D/E, Interest Coverage).
3. Định giá Giá trị Nội tại Đa Mô Hình (Football Field: Damodaran Excess Return / DCF, Benjamin Graham Number, Peter Lynch GARP) & Biên An Toàn (Margin of Safety %).
4. Kiểm toán Chất lượng Lợi nhuận & Dòng tiền HĐKD (Cash Flow Forensics) & Bộ lọc Cổ phiếu Rác / Rủi ro Hủy niêm yết.
"""

from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import numpy as np
from trading_agent.data_engine import DataEngine
from trading_agent.quant_engine import QuantEngine


SECTOR_PEERS = {
    "HPG": ["HSG", "NKG", "VGS"],
    "HSG": ["HPG", "NKG", "VGS"],
    "NKG": ["HPG", "HSG", "VGS"],
    "SSI": ["VND", "VCI", "HCM", "MBS"],
    "VND": ["SSI", "VCI", "HCM", "SHS"],
    "VCI": ["SSI", "VND", "HCM", "FTS"],
    "HCM": ["SSI", "VND", "VCI", "MBS"],
    "VCB": ["BID", "CTG", "TCB", "MBB"],
    "BID": ["VCB", "CTG", "TCB", "ACB"],
    "CTG": ["VCB", "BID", "TCB", "MBB"],
    "TCB": ["MBB", "ACB", "VPB", "VCB"],
    "MBB": ["TCB", "ACB", "CTG", "STB"],
    "ACB": ["TCB", "MBB", "VIB", "HDB"],
    "STB": ["TCB", "MBB", "VPB", "SHB"],
    "VPB": ["TCB", "MBB", "HDB", "TPB"],
    "FPT": ["CMG", "CTR", "DGW"],
    "MWG": ["FRT", "DGW", "PNJ"],
    "FRT": ["MWG", "DGW", "PNJ"],
    "DGW": ["MWG", "FRT", "FPT"],
    "VHM": ["KDH", "NLG", "NVL", "DIG"],
    "DIG": ["DXG", "PDR", "CEO", "NVL"],
    "DXG": ["DIG", "PDR", "NLG", "KDH"],
    "KBC": ["IDC", "SZC", "VGC", "GVR"],
    "GAS": ["PVS", "PVD", "PLX", "BSR"],
    "PVD": ["PVS", "GAS", "PVT", "BSR"],
    "PVS": ["PVD", "GAS", "PVT", "BSR"],
    "DGC": ["DCM", "DPM", "CSV"],
    "TCM": ["TNG", "MSH", "GIL", "VHC"],
    "TNG": ["TCM", "MSH", "GIL", "VHC"],
    "VHC": ["ANV", "IDI", "TCM", "FMC"]
}


class FundamentalAgent:
    def __init__(self, data_engine: DataEngine = None):
        self.de = data_engine or DataEngine()

    def audit_financial_health(self, symbol: str) -> dict:
        symbol = symbol.strip().upper()
        ov = self.de.get_company_overview(symbol)
        df_hist = self.de.get_history(symbol, days=90)

        curr_price = float(ov.get("current_price") or 0.0)
        if curr_price <= 0 and not df_hist.empty:
            curr_price = float(df_hist["close"].iloc[-1])
            ov["current_price"] = curr_price

        avg_vol_20 = 0.0
        avg_val_vnd = 0.0
        if not df_hist.empty:
            avg_vol_20 = float(df_hist["volume"].tail(20).mean())
            avg_val_vnd = avg_vol_20 * curr_price

        pe = ov.get("pe")
        pb = ov.get("pb")
        roe = ov.get("roe")
        roa = ov.get("roa")
        de = ov.get("debt_to_equity")
        is_bank = bool(ov.get("is_bank"))
        p_growth = ov.get("profit_growth_yoy")
        r_growth = ov.get("revenue_growth_yoy")
        gross_margin = ov.get("gross_margin")
        net_margin = ov.get("net_margin")
        interest_cov = ov.get("interest_coverage")
        cps = ov.get("cps")

        # 1. DuPont 3-Step & Multi-Model Valuation
        dupont_val = QuantEngine.compute_dupont_and_valuation(ov)
        intrinsic_val = dupont_val["intrinsic_value"]
        mos_pct = dupont_val["margin_of_safety_pct"]

        fund_score = 0
        red_flags = []
        positives = []
        is_junk = False
        delisting_risk = False

        # --- KIỂM ĐỊNH 1: THANH KHOẢN TỔ CHỨC (LIQUIDITY AUDIT) ---
        if avg_vol_20 < 50_000 or avg_val_vnd < 1_000_000_000:
            is_junk = True
            fund_score -= 5
            red_flags.append(
                f"RỦI RO THANH KHOẢN CỰC ĐỘ: Khối lượng GD TB 20 phiên chỉ đạt {avg_vol_20:,.0f} CP "
                f"(~{avg_val_vnd/1e9:.2f} tỷ VNĐ/phiên). Quỹ tổ chức không thể giải ngân hoặc thoát hàng!"
            )
        elif avg_val_vnd >= 30_000_000_000:
            fund_score += 2
            positives.append(
                f"Thanh khoản chuẩn Quỹ Tổ chức ({avg_val_vnd/1e9:.1f} tỷ VNĐ/phiên ~ {avg_vol_20:,.0f} CP/phiên), hấp thụ vốn lớn dễ dàng."
            )
        elif avg_val_vnd >= 8_000_000_000:
            fund_score += 1
            positives.append(f"Thanh khoản khá ({avg_val_vnd/1e9:.1f} tỷ VNĐ/phiên), đảm bảo giao dịch an toàn.")
        else:
            red_flags.append(f"Thanh khoản trung bình thấp ({avg_val_vnd/1e9:.1f} tỷ VNĐ/phiên), chỉ phù hợp giải ngân tỷ trọng nhỏ.")

        # --- KIỂM ĐỊNH 2: THỊ GIÁ PENNY & NGUY CƠ HỦY NIÊM YẾT ---
        if 0 < curr_price < 7_000:
            is_junk = True
            delisting_risk = True
            fund_score -= 4
            red_flags.append(
                f"CẢNH BÁO CỔ PHIẾU PENNY / RÁC: Thị giá ({curr_price:,.0f} đ) nằm sâu dưới mệnh giá 10,000 đ, rủi ro đầu cơ đội lái hoặc hủy niêm yết."
            )

        # --- KIỂM ĐỊNH 3: HIỆU QUẢ SINH LỜI ROE / ROA & TĂNG TRƯỞNG LỢI NHUẬN ---
        if roe is not None:
            if roe < 0:
                delisting_risk = True
                is_junk = True
                fund_score -= 4
                red_flags.append(f"DOANH NGHIỆP THUA LỖ: ROE âm ({roe:.1f}%), bào mòn vốn chủ sở hữu, nguy cơ bị đưa vào diện cảnh báo/kiểm soát.")
            elif roe >= 18.0:
                fund_score += 3
                positives.append(f"Hiệu suất sinh lời trên vốn chủ sở hữu xuất sắc (ROE = {roe:.1f}%, ROA = {roa or 0:.1f}% - {dupont_val['roe_driver']}).")
            elif roe >= 13.0:
                fund_score += 2
                positives.append(f"Hiệu quả sinh lời tốt (ROE = {roe:.1f}%, vượt chi phí vốn cổ phần Ke = {dupont_val['cost_of_equity_pct']:.1f}%).")
            elif roe < 7.0:
                fund_score -= 1
                red_flags.append(f"Hiệu suất sinh lời ROE thấp ({roe:.1f}%), thấp hơn chi phí sử dụng vốn cổ phần ({dupont_val['cost_of_equity_pct']:.1f}%).")

        if p_growth is not None:
            if p_growth >= 20.0:
                fund_score += 2
                positives.append(f"Tăng trưởng lợi nhuận sau thuế bứt phá mạnh mẽ (+{p_growth:.1f}% YoY trong kỳ {ov.get('latest_quarter', 'gần nhất')}).")
            elif p_growth >= 5.0:
                fund_score += 1
                positives.append(f"Lợi nhuận duy trì đà tăng trưởng dương (+{p_growth:.1f}% YoY).")
            elif p_growth <= -15.0:
                fund_score -= 2
                red_flags.append(f"SUY GIẢM LỢI NHUẬN NGHIÊM TRỌNG: Lợi nhuận sau thuế sụt giảm {p_growth:+.1f}% YoY trong kỳ BCTC mới nhất ({ov.get('latest_quarter', '')}).")
            elif p_growth < 0:
                fund_score -= 1
                red_flags.append(f"Tăng trưởng lợi nhuận chững lại ({p_growth:+.1f}% YoY).")

        # --- KIỂM ĐỊNH 4: ĐẶC THÙ NGÀNH NGÂN HÀNG VS PHI TÀI CHÍNH ---
        if is_bank:
            cir = ov.get("cir")
            ldr = ov.get("ldr")
            cred_g = ov.get("credit_growth")
            if cir is not None and cir <= 33.0:
                fund_score += 1
                positives.append(f"Kiểm soát chi phí hoạt động ngân hàng tối ưu (CIR = {cir:.1f}% - thuộc nhóm tốt nhất ngành).")
            if cred_g is not None and cred_g >= 14.0:
                positives.append(f"Tăng trưởng dư nợ tín dụng tích cực (+{cred_g:.1f}%), động lực mở rộng thu nhập lãi thuần.")
            if ldr is not None and ldr > 90.0:
                red_flags.append(f"Tỷ lệ Dư nợ / Huy động (LDR = {ldr:.1f}%) ở mức cao, cần theo dõi thanh khoản huy động.")
        else:
            if de is not None:
                if de > 2.0:
                    fund_score -= 2
                    red_flags.append(f"Đòn bẩy nợ vay / VCSH quá cao (D/E = {de:.2f}x), rủi ro chi phí lãi vay ăn mòn lợi nhuận.")
                elif de <= 0.6:
                    fund_score += 1
                    positives.append(f"Cấu trúc tài chính lành mạnh, tỷ lệ Nợ vay / VCSH thấp (D/E = {de:.2f}x).")
            if interest_cov is not None and 0 < interest_cov < 2.0:
                fund_score -= 2
                red_flags.append(f"Khả năng thanh toán lãi vay yếu (Interest Coverage = {interest_cov:.1f}x < 2.0x).")
            if cps is not None and cps < -1500:
                red_flags.append(f"CẢNH BÁO DÒNG TIỀN HĐKD ÂM: Lưu chuyển tiền thuần HĐKD trên mỗi CP âm ({cps:,.0f} đ/CP), chất lượng lợi nhuận thấp.")

        # --- KIỂM ĐỊNH 5: ĐỊNH GIÁ & BIÊN AN TOÀN (DAMODARAN / GRAHAM / LYNCH) ---
        if pe is not None:
            if pe < 0:
                delisting_risk = True
                fund_score -= 3
                red_flags.append("EPS âm dẫn đến P/E âm: Doanh nghiệp kinh doanh thua lỗ.")
            elif mos_pct >= 18.0:
                fund_score += 2
                positives.append(
                    f"Định giá hấp dẫn (P/E = {pe:.1f}x, P/B = {pb or 0:.2f}x): Thị giá thấp hơn Giá trị nội tại ({intrinsic_val:,.0f} đ) với Biên an toàn +{mos_pct:.1f}%."
                )
            elif mos_pct <= -25.0 and pe > 25.0:
                fund_score -= 1
                red_flags.append(f"Định giá khá đắt so với nội tại (P/E = {pe:.1f}x, vượt giá trị hợp lý {intrinsic_val:,.0f} đ).")

        if is_junk or delisting_risk or fund_score <= -2:
            health_status = "CỔ PHIẾU RỦI RO CAO / CẢNH BÁO CƠ BẢN ⛔"
        elif fund_score >= 4:
            health_status = "DOANH NGHIỆP ĐẦU NGÀNH - TÀI CHÍNH VỮNG MẠNH 💎"
        elif fund_score >= 2:
            health_status = "TÀI CHÍNH LÀNH MẠNH - ĐẠT CHUẨN ĐẦU TƯ 🟢"
        else:
            health_status = "TÀI CHÍNH TRUNG BÌNH - CẦN CHỌN LỌC KỸ 🟡"

        # So sánh đối thủ cùng ngành (Song song hóa để chạy < 0.4s)
        peer_list = SECTOR_PEERS.get(symbol, ["HPG", "FPT", "VCB", "SSI"][:3])
        peers_comparison = []
        self.de.get_batch_price_board(peer_list[:3])

        def _fetch_peer(p_sym):
            try:
                p_ov = self.de.get_company_overview(p_sym)
                return {
                    "symbol": p_sym,
                    "price": p_ov.get("current_price", 0),
                    "pe": p_ov.get("pe", "N/A"),
                    "pb": p_ov.get("pb", "N/A"),
                    "roe": p_ov.get("roe", "N/A"),
                    "profit_growth_yoy": p_ov.get("profit_growth_yoy", "N/A")
                }
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=3) as ex:
            for res in ex.map(_fetch_peer, peer_list[:3]):
                if res:
                    peers_comparison.append(res)

        return {
            "symbol": symbol,
            "organ_name": ov.get("organ_name", symbol),
            "industry": ov.get("industry", "N/A"),
            "exchange": ov.get("exchange", "HOSE"),
            "market_cap": ov.get("market_cap", "N/A"),
            "latest_quarter": ov.get("latest_quarter", "N/A"),
            "current_price": curr_price,
            "avg_vol_20": avg_vol_20,
            "avg_liquidity_vnd": avg_val_vnd,
            "pe": pe,
            "pb": pb,
            "ps": ov.get("ps"),
            "ev_ebitda": ov.get("ev_ebitda"),
            "eps": ov.get("eps"),
            "bvps": ov.get("bvps"),
            "roe": roe,
            "roa": roa,
            "gross_margin": gross_margin,
            "net_margin": net_margin,
            "debt_to_equity": de,
            "profit_growth_yoy": p_growth,
            "revenue_growth_yoy": r_growth,
            "is_bank": is_bank,
            "nim": ov.get("nim"),
            "cir": ov.get("cir"),
            "ldr": ov.get("ldr"),
            "credit_growth": ov.get("credit_growth"),
            "dupont_valuation": dupont_val,
            "intrinsic_value": intrinsic_val,
            "margin_of_safety_pct": mos_pct,
            "fundamental_score": fund_score,
            "health_status": health_status,
            "is_junk": is_junk,
            "delisting_risk": delisting_risk,
            "positives": positives,
            "red_flags": red_flags,
            "peers": peers_comparison,
            "raw_overview": ov
        }
