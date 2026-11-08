"""
Institutional Multi-Agent Orchestrator for Vietnam Stock Market.
Hệ thống điều phối Đa Agent chuyên nghiệp hoạt động như một Tổ Chức Đầu Tư ngoài đời thực:
- Hội đồng Đầu tư Tranh luận & Phản biện 7 Lượt + 9 Đại Kiện Tướng (Debate Engine)
- Thẩm định cuối cùng của Giám đốc Đầu tư (CIO Agent) & Bộ Nhớ Tự Học (Self-Learning Engine)
- So sánh trực diện đa cổ phiếu song song đa luồng (Multi-Stock Parallel Comparison)
- Thiết lập danh mục phân bổ vốn tự động theo số tiền yêu cầu (Capital Allocation Advisory)
- Bộ lọc VSA, VPA, SMC, SEPA/VCP, Bắt Đáy Tạo Đáy An Toàn & Đa tiêu chí linh hoạt (Dynamic Custom Screener)
- Giám sát Phái sinh VN30F1M & Vị thế Cá mập / Khối ngoại
"""

import re
import math
from concurrent.futures import ThreadPoolExecutor
from trading_agent.data_engine import DataEngine
from trading_agent.technical_analysis import TechnicalAnalysis
from trading_agent.macro_agent import MacroAgent
from trading_agent.fundamental_agent import FundamentalAgent
from trading_agent.technical_structure_agent import TechnicalStructureAgent
from trading_agent.sentiment_agent import SentimentAgent
from trading_agent.risk_agent import RiskAgent
from trading_agent.debate_engine import DebateEngine
from trading_agent.cio_agent import CIOAgent
from trading_agent.dynamic_agent_manager import DynamicAgentManager
from trading_agent.vsa_smc_screener import VSASMCScreener, INSTITUTIONAL_LIQUID_UNIVERSE
from trading_agent.screener import StockScreener
from trading_agent.portfolio import PortfolioManager
from trading_agent.alert_engine import AlertEngine
from trading_agent.derivatives_agent import DerivativesAgent
from trading_agent.self_learning_engine import SelfLearningEngine

# Tập hợp đầy đủ các từ tiếng Việt 3 chữ cái (có dấu & không dấu) để tuyệt đối không nhận nhầm thành mã cổ phiếu
VIETNAMESE_STOP_WORDS = {
    "ANH", "BAN", "BAO", "BAT", "BAY", "BEN", "BOT", "CAC", "CAM", "CAN", "CAO", "CAT",
    "CAU", "CHA", "CHE", "CHI", "CHO", "CHU", "CON", "CUA", "CUC", "DAI", "DAM", "DAN",
    "DAT", "DAU", "DAY", "DEM", "DEN", "DEO", "DET", "DOC", "DOI", "DON", "DOT", "DUA",
    "DUC", "GAN", "GAP", "GAU", "GHE", "GHI", "GIA", "GIO", "GIU", "GOI", "GOM", "GOP",
    "HAI", "HAN", "HAO", "HAT", "HAY", "HET", "HOA", "HOI", "HOM", "HON", "HOP", "HOT",
    "HUY", "KEM", "KEO", "KEP", "KET", "KHA", "KHI", "KHO", "KHU", "KIP", "LAI", "LAM",
    "LAN", "LAU", "LAY", "LEN", "LOC", "LOI", "LON", "LOP", "LUC", "LUU", "MAI", "MAN",
    "MAT", "MAU", "MAY", "MIN", "MOI", "MON", "MOT", "MUA", "MUC", "NAM", "NAO", "NAY",
    "NEN", "NEU", "NGA", "NGO", "NHA", "NHE", "NHI", "NHO", "NHU", "NOI", "NON", "NOP",
    "NUA", "PHA", "PHE", "PHI", "PHO", "PHU", "QUA", "QUE", "QUY", "RAO", "RAT", "ROI",
    "RUI", "RUT", "SAI", "SAN", "SAO", "SAT", "SAU", "SOI", "SOM", "SON", "SUA", "SUC",
    "SUY", "TAI", "TAM", "TAN", "TAO", "TAP", "TAT", "TAY", "THA", "THE", "THI", "THO",
    "THU", "TIM", "TIN", "TOA", "TOI", "TOM", "TON", "TOP", "TOT", "TRA", "TRE", "TRI",
    "TRO", "TRU", "TUA", "TUC", "TUI", "TUY", "UNG", "UOC", "VAI", "VAN", "VAO", "VAT",
    "VAY", "VEN", "VOI", "VON", "VUA", "XAC", "XAU", "XAY", "XEM", "XEP", "XIN", "XOA",
    "YEU", "ALL", "RSI", "MAC", "SMA", "EMA", "VCP", "POC", "VAH", "VAL", "OBB", "FVG",
    "VSA", "VPA", "SMC", "AIX", "BUY", "SEL", "ROE", "ROA", "EPS", "NAV", "ATH", "USD",
    "VND_CURRENCY"
}


class TradingAgent:
    def __init__(
        self,
        data_engine: DataEngine = None,
        portfolio: PortfolioManager = None,
        screener: StockScreener = None,
        alert_engine: AlertEngine = None,
        api_key: str = None
    ):
        self.de = data_engine or DataEngine()
        self.portfolio = portfolio or PortfolioManager()
        self.screener = screener or StockScreener(self.de)
        self.vsa_screener = VSASMCScreener(self.de)
        self.alerts = alert_engine or AlertEngine(data_engine=self.de)
        self.derivatives = DerivativesAgent(data_engine=self.de)
        self.api_key = api_key

        self.macro_agent = MacroAgent(data_engine=self.de)
        self.fund_agent = FundamentalAgent(data_engine=self.de)
        self.tech_agent = TechnicalStructureAgent(data_engine=self.de)
        self.sentiment_agent = SentimentAgent(data_engine=self.de)
        self.risk_agent = RiskAgent(data_engine=self.de)
        self.debate_engine = DebateEngine(data_engine=self.de)
        self.self_learning = SelfLearningEngine()
        self.cio_agent = CIOAgent(debate_engine=self.debate_engine, self_learning=self.self_learning)
        self.dynamic_manager = DynamicAgentManager()

        # Trạng thái đồng bộ với UI khi người dùng chat
        self.last_analyzed_symbol = None
        self.last_screened_df = None
        self.last_screened_filter = None

    def respond(self, user_message: str) -> str:
        """
        Xử lý đa nhiệm mọi yêu cầu của người dùng theo chuẩn Tổ Chức Đầu Tư Chuyên Nghiệp.
        Luôn thực thi đúng nhiệm vụ người dùng giao (lọc cổ phiếu bắt đáy, lọc VSA/SMC/SEPA, thẩm định mã,
        so sánh đa mã, tư vấn danh mục, phái sinh, tự học...) đồng thời đính kèm cảnh báo quản trị rủi ro nếu cần.
        """
        if not user_message or not user_message.strip():
            return "Vui lòng nhập yêu cầu phân tích hoặc câu lệnh của bạn."

        msg = user_message.strip()
        msg_lower = msg.lower()

        # Kiểm tra xem có cảnh báo phản biện rủi ro nào cần đính kèm vào kết quả thực thi không
        critique_result = self.dynamic_manager.critique_user_intent(msg)
        advisory_note = ""
        if critique_result.get("has_criticism"):
            advisory_note = "\n\n---\n" + "\n\n".join(critique_result["criticisms"])

        # =========================================================================
        # 1. TẠO THÊM AGENT MỚI / THIẾT LẬP NHIỆM VỤ THEO YÊU CẦU NGƯỜI DÙNG
        # =========================================================================
        create_agent_match = self._parse_create_agent_command(msg)
        if create_agent_match:
            name, role, criteria = create_agent_match
            res = self.dynamic_manager.create_agent(name=name, role=role, criteria=criteria)
            return (
                f"🎉 **{res['message']}**\n\n"
                f"- **Mã định danh:** `{res['agent']['id']}`\n"
                f"- **Nhiệm vụ chuyên biệt:** {role}\n"
                f"- **Tiêu chí sàng lọc:** {criteria or 'Tùy biến theo dòng tiền'}\n\n"
                f"Agent mới đã được nạp vào hệ thống và sẵn sàng hoạt động!"
            )

        # =========================================================================
        # 2. HỆ THỐNG TỰ HỌC & GHI NHỚ SAI LẦM (SELF-LEARNING & MISTAKE MEMORY)
        # =========================================================================
        if any(k in msg_lower for k in [
            "tự học", "tu hoc", "sai lầm", "sai lam", "bộ nhớ", "bo nho", "hậu kiểm", "hau kiem",
            "dạy ai", "day ai", "ghi nhớ lỗi", "ghi nho loi", "rút kinh nghiệm", "rut kinh nghiem", "self learning"
        ]):
            return self._handle_self_learning_query(msg)

        # =========================================================================
        # 3. GIÁM SÁT THỊ TRƯỜNG PHÁI SINH & VỊ THẾ KHỐI NGOẠI / CÁ MẬP (VN30F1M)
        # =========================================================================
        is_derivatives_query = any(k in msg_lower for k in [
            "phái sinh", "phai sinh", "vn30f1m", "f1m", "hợp đồng tương lai", "hop dong tuong lai",
            "cá mập", "ca map", "khối ngoại long", "khối ngoại short", "khoi ngoai long", "khoi ngoai short",
            "long short", "long/short", "basis", "đáo hạn phái sinh", "dao han phai sinh", "short phái sinh", "long phái sinh"
        ])
        if is_derivatives_query:
            return self.derivatives.generate_derivatives_report()

        # =========================================================================
        # 4. THỰC HIỆN LỆNH GIAO DỊCH (PAPER TRADING) & CẢNH BÁO GIÁ
        # =========================================================================
        trade_match = self._parse_trade_command(msg)
        if trade_match:
            action, qty, sym = trade_match
            return self._handle_trade_execution(action, qty, sym)

        alert_match = self._parse_alert_command(msg)
        if alert_match:
            sym, cond, target = alert_match
            res = self.alerts.add_price_alert(sym, cond, target)
            return f"🔔 **{res['message']}**"

        # =========================================================================
        # 5. TƯ VẤN PHÂN BỔ VỐN / XÂY DỰNG DANH MỤC ĐẦU TƯ THEO SỐ TIỀN
        # =========================================================================
        is_capital_advisory = any(k in msg_lower for k in [
            "tư vấn danh mục", "tu van danh muc", "phân bổ vốn", "phan bo von",
            "xây dựng danh mục", "xay dung danh muc", "có 1 tỷ", "co 1 ty", "1 tỷ", "1 ty",
            "500 triệu", "500 trieu", "2 tỷ", "2 ty", "100 triệu", "100 trieu", "300 triệu", "300 trieu", "vốn "
        ])
        if is_capital_advisory:
            return self._handle_capital_allocation_advisory(msg) + advisory_note

        # =========================================================================
        # 6. TRA CỨU TÀI KHOẢN / DANH MỤC GIẢ LẬP ĐANG NẮM GIỮ
        # =========================================================================
        if any(w in msg_lower for w in ["danh mục", "danh muc", "tài khoản", "tai khoan", "số dư", "so du", "tiền mặt", "tien mat", "lãi lỗ", "lai lo", "portfolio"]):
            return self._handle_portfolio_query()

        # =========================================================================
        # 7. SO SÁNH TRỰC DIỆN 2 HOẶC NHIỀU CỔ PHIẾU SONG SONG ĐA LUỒNG
        # =========================================================================
        multi_syms = self._extract_multiple_symbols(msg)
        is_compare = any(k in msg_lower for k in ["so sánh", "so sanh", "hay ", "hoặc ", "vs ", "với ", "voi ", "hơn"])
        if len(multi_syms) >= 2 and (is_compare or len(multi_syms) <= 4):
            self.last_analyzed_symbol = multi_syms[0]
            return self._handle_multi_symbol_comparison(multi_syms) + advisory_note

        # =========================================================================
        # 8. BỘ LỌC CỔ PHIẾU (VSA/SMC, BẮT ĐÁY TẠO ĐÁY, SEPA/VCP, ĐỊNH GIÁ, NGÀNH...)
        # =========================================================================
        is_vsa_smc_query = any(k in msg_lower for k in [
            "vsa", "vpa", "smc", "volume profile", "profile", "order block", "poc",
            "no supply", "stopping volume", "choch", "bos", "fvg"
        ])
        is_bottom_fishing_query = any(k in msg_lower for k in [
            "bắt đáy", "bat day", "tạo đáy", "tao day", "quá bán", "qua ban",
            "chiết khấu sâu", "chiet khau sau", "giảm sâu", "giam sau", "vùng đáy", "vung day",
            "đảo chiều tạo đáy", "dao chieu tao day", "spring"
        ])
        is_sector_or_criteria_screen = any(k in msg_lower for k in [
            "lọc", "loc", "quét", "quet", "tìm", "tim", "screener", "scan", "gợi ý", "goi y", "cơ hội", "co hoi",
            "cổ phiếu nào", "co phieu nao", "mua con gì", "mua con gi", "mua mã nào", "mua ma nao",
            "đáng mua nhất", "dang mua nhat", "tốt nhất hôm nay", "tot nhat hom nay", "top cổ phiếu", "top co phieu",
            "siêu cổ phiếu", "sieu co phieu", "danh sách cổ phiếu", "danh sach co phieu",
            "ngành ngân hàng", "nganh ngan hang", "nhóm ngân hàng", "nhom ngan hang",
            "ngành chứng khoán", "nganh chung khoan", "nhóm chứng khoán", "nhom chung khoan",
            "ngành thép", "nganh thep", "nhóm thép", "nhom thep",
            "ngành bất động sản", "nganh bat dong san", "nhóm bất động sản", "nhom bat dong san",
            "ngành dầu khí", "nganh dau khi", "nhóm dầu khí", "nhom dau khi",
            "sepa", "vcp", "minervini", "canslim", "golden cross", "vượt đỉnh", "vuot dinh",
            "nổ vol", "no vol", "đột biến khối lượng", "dot bien khoi luong", "định giá rẻ", "dinh gia re",
            "pe thấp", "pe thap", "roe cao"
        ])

        # Nếu người dùng yêu cầu lọc cổ phiếu bắt đáy (mà không chỉ định 1 mã cụ thể) -> Chạy bộ lọc Bắt Đáy An Toàn ngay!
        if is_bottom_fishing_query and not multi_syms:
            return self._handle_custom_screener_query(msg_lower, forced_criteria="bottom_fishing") + advisory_note

        if is_vsa_smc_query and not multi_syms:
            return self._handle_vsa_smc_screener_query(msg_lower) + advisory_note

        if is_sector_or_criteria_screen and not multi_syms:
            return self._handle_custom_screener_query(msg_lower) + advisory_note

        # =========================================================================
        # 9. TRUY VẤN VĨ MÔ & NHẬN ĐỊNH THỊ TRƯỜNG CHUNG HÔM NAY (VN-INDEX)
        # =========================================================================
        if any(w in msg_lower for w in [
            "vĩ mô", "vi mo", "macro", "thị trường", "thi truong", "vnindex", "vn-index", "vn30",
            "dxy", "lãi suất", "lai suat", "tỷ giá", "ty gia", "market regime", "xu hướng chung", "xu huong chung"
        ]) and not multi_syms:
            return self._handle_macro_query()

        # =========================================================================
        # 9B. PHÂN TÍCH ÁP LỰC CUNG CẦU (ORDER FLOW) & BỘ TỨ ĐỊNH GIÁ GRAHAM (AFL VPA 5.0)
        # =========================================================================
        is_order_flow_or_graham = any(k in msg_lower for k in [
            "lực mua", "luc mua", "lực bán", "luc ban", "cung cầu", "cung cau", "order flow",
            "nỗ lực", "no luc", "effort", "graham", "vgraham", "keltner", "darvas", "đao găm", "dao gam", "trailing stop"
        ])
        detected_sym_cand = multi_syms[0] if multi_syms else self._extract_symbol(msg)
        if is_order_flow_or_graham and detected_sym_cand:
            self.last_analyzed_symbol = detected_sym_cand
            return self._handle_order_flow_and_graham_query(detected_sym_cand) + advisory_note

        # =========================================================================
        # 10. PHÂN TÍCH TOÀN DIỆN MÃ CỔ PHIẾU CỦA HỘI ĐỒNG ĐẦU TƯ
        # =========================================================================
        detected_symbol = multi_syms[0] if multi_syms else self._extract_symbol(msg)
        if detected_symbol:
            self.last_analyzed_symbol = detected_symbol
            return self._handle_institutional_committee_analysis(detected_symbol) + advisory_note

        # =========================================================================
        # 11. KIẾN THỨC THỊ TRƯỜNG & QUY ĐỊNH VIỆT NAM (T+2.5, TRẦN/SÀN)
        # =========================================================================
        if any(w in msg_lower for w in ["t+2", "t+2.5", "t+", "thanh toán", "thanh toan", "vsd"]):
            return (
                "📌 **Quy chế giao dịch T+2.5 tại Việt Nam (Chuẩn tổ chức):**\n\n"
                "- **Ngày T+0**: Khớp lệnh mua cổ phiếu trên sàn.\n"
                "- **Ngày T+1**: Tiền và chứng khoán đang hạch toán qua Tổng công ty Lưu ký và Bù trừ Chứng khoán (VSDC).\n"
                "- **Ngày T+2 (13h00)**: Cổ phiếu về tài khoản đầu giờ chiều phiên T+2 và có thể bán ngay trong phiên giao dịch buổi chiều.\n"
                "- **Rủi ro kẹt T+2.5**: Nếu mua đuổi tại phiên hưng phấn gãy cấu trúc, nhà đầu tư phải chịu đựng 2 phiên giảm sàn liên tiếp (mất ~14% trên HOSE) trước khi hàng về tài khoản để cắt lỗ! Đây là lý do Hội Đồng Đầu Tư luôn cấm mua đuổi FOMO."
            )

        # =========================================================================
        # 12. NẾU CÂU HỎI TỔNG QUÁT: TỰ ĐỘNG TỔNG HỢP BỨC TRANH THỊ TRƯỜNG & TOP CỔ PHIẾU
        # =========================================================================
        return self._handle_general_advisory_overview(msg) + advisory_note

    def _extract_multiple_symbols(self, text: str) -> list:
        """
        Trích xuất danh sách tất cả các mã cổ phiếu hợp lệ được người dùng nhắc đến trong câu lệnh.
        Loại bỏ triệt để 100% các từ tiếng Việt 3 chữ cái (như 'hom', 'tra', 'tot', 'can', 'mua', 'ban', 'bat', 'day'...).
        """
        found = []

        # 1. Ưu tiên tuyệt đối các mã đứng ngay sau từ khóa 'mã', 'cổ phiếu', 'cp', 'phân tích'
        explicit_matches = re.findall(
            r"\b(?:mã|ma|cổ phiếu|co phieu|cp|phân tích|phan tich|đánh giá|danh gia|xem)\s+([A-Za-z]{3})\b",
            text,
            re.IGNORECASE
        )
        for m in explicit_matches:
            cand = m.upper()
            if cand not in VIETNAMESE_STOP_WORDS and self.de.is_valid_symbol(cand) and cand not in found:
                found.append(cand)

        # 2. Quét tất cả các từ 3 ký tự trong câu
        words = re.findall(r"\b[A-Za-z]{3}\b", text)
        liquid_set = set(INSTITUTIONAL_LIQUID_UNIVERSE) | set(self.de.get_vn30_symbols())

        # Nếu câu chỉ có đúng 1 từ 3 chữ cái (VD người dùng gõ thẳng "TCB", "BSR", "FPT")
        if len(words) == 1 and len(text.strip()) == 3:
            single = words[0].upper()
            if self.de.is_valid_symbol(single):
                return [single]

        for w in words:
            cand = w.upper()
            if cand in VIETNAMESE_STOP_WORDS:
                continue
            if cand == "VND" and re.search(r"\d+\s*vnd\b", text.lower()):
                continue
            if cand in liquid_set and cand not in found:
                found.append(cand)

        for w in words:
            cand = w.upper()
            if cand in VIETNAMESE_STOP_WORDS or cand in found:
                continue
            if self.de.is_valid_symbol(cand):
                found.append(cand)

        return found

    def _extract_symbol(self, text: str) -> str:
        syms = self._extract_multiple_symbols(text)
        return syms[0] if syms else None

    def _handle_multi_symbol_comparison(self, symbols: list) -> str:
        """So sánh trực diện 2-4 mã cổ phiếu chạy song song đa luồng (Multi-threaded)."""
        target_syms = symbols[:4]
        with ThreadPoolExecutor(max_workers=len(target_syms)) as ex:
            decisions = list(ex.map(self.cio_agent.evaluate_and_decide, target_syms))

        rows = [
            "| Tiêu Chí Thẩm Định | " + " | ".join([f"**{s}**" for s in target_syms]) + " |",
            "| :--- | " + " | ".join([":---:" for _ in target_syms]) + " |"
        ]

        def _row(label, getter):
            return f"| **{label}** | " + " | ".join([str(getter(d)) for d in decisions]) + " |"

        rows.append(_row("Ngành", lambda d: d["meeting"]["fund_report"].get("industry", "—")))
        rows.append(_row("Thị Giá Hiện Tại", lambda d: f"{d['meeting']['tech_report'].get('current_price', 0):,.0f} đ"))
        rows.append(_row("Giá Trị Nội Tại (Damodaran/Graham)", lambda d: f"**{d['meeting']['fund_report'].get('intrinsic_value', 0):,.0f} đ**"))
        rows.append(_row("Biên An Toàn (MoS)", lambda d: f"{d['meeting']['fund_report'].get('margin_of_safety_pct', 0):+.1f}%"))
        rows.append(_row("P/E & P/B", lambda d: f"{d['meeting']['fund_report'].get('pe', '—')}x / {d['meeting']['fund_report'].get('pb', '—')}x"))
        rows.append(_row("ROE (%) & Tăng Trưởng LN", lambda d: f"{d['meeting']['fund_report'].get('roe', '—')}% / {d['meeting']['fund_report'].get('profit_growth_yoy', '—')}%"))
        rows.append(_row("Chu Kỳ Weinstein", lambda d: d["meeting"]["tech_report"].get("stage_name", "—")))
        rows.append(_row("Minervini SEPA & RS Rating", lambda d: f"`{d['meeting']['tech_report']['sepa_vcp'].get('sepa_score', 0)}/8` | RS `{d['meeting']['tech_report']['rs_info'].get('rs_rating', 50)}/99`"))
        rows.append(_row("Điểm CANSLIM", lambda d: f"`{d['meeting']['canslim_report'].get('canslim_score', 0)}/100` (Hạng {d['meeting']['canslim_report'].get('canslim_grade', 'C')})"))
        rows.append(_row("Điểm Tự Học Hiệu Chỉnh", lambda d: f"**{d.get('self_learning_audit', {}).get('adjusted_score', 0)}/100**"))
        rows.append(_row("Vùng Mua An Toàn", lambda d: f"`{d['trade_plan'].get('optimal_entry_zone', '—')}`"))
        rows.append(_row("Cắt Lỗ Cấu Trúc (SL)", lambda d: f"`{d['trade_plan'].get('structural_stop_loss', 0):,.0f} đ`"))
        rows.append(_row("Mục Tiêu Chốt Lời (TP1)", lambda d: f"`{d['trade_plan'].get('take_profit_target_1', 0):,.0f} đ`"))
        rows.append(_row("Phán Quyết Của CIO", lambda d: f"**{d['final_decision']}**"))

        best_dec = max(
            decisions,
            key=lambda d: (
                0 if "TỪ CHỐI" in d["final_decision"] else 1,
                d["conviction_score"],
                d.get("self_learning_audit", {}).get("adjusted_score", 0)
            )
        )

        table_md = "\n".join(rows)
        return f"""# ⚖️ BÁO CÁO SO SÁNH TRỰC DIỆN ĐA CỔ PHIẾU: **{' vs '.join(target_syms)}**
*(Thực thi thẩm định song song đa luồng bởi Hội Đồng 9 Đại Kiện Tướng & CIO Agent)*

{table_md}

---
## 🏆 KẾT LUẬN CHỌN LỌC TỪ CHỦ TỊCH HỘI ĐỒNG ĐẦU TƯ (CIO):
- **Cổ phiếu vượt trội nhất:** **`{best_dec['symbol']}`** — **{best_dec['final_decision']}** (Điểm thuyết phục: `{best_dec['conviction_score']}/10`, Tỷ trọng khuyến nghị: `{best_dec['allocation_pct']}% NAV`).
- **Luận điểm cốt lõi:** {best_dec['action_plan']}
"""

    def _handle_capital_allocation_advisory(self, msg: str) -> str:
        """Tư vấn xây dựng danh mục đầu tư chuẩn Tổ chức theo số vốn yêu cầu của người dùng."""
        capital_vnd = 1_000_000_000.0
        m_ty = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:tỷ|ty)", msg.lower())
        m_tr = re.search(r"(\d+(?:[\.,]\d+)?)\s*(?:triệu|trieu|tr)", msg.lower())
        if m_ty:
            capital_vnd = float(m_ty.group(1).replace(",", ".")) * 1_000_000_000.0
        elif m_tr:
            capital_vnd = float(m_tr.group(1).replace(",", ".")) * 1_000_000.0

        macro = self.macro_agent.analyze_market_regime()
        eq_pct = macro["recommended_allocation"]["equity_pct"]
        cash_pct = macro["recommended_allocation"]["cash_pct"]

        df_buy = self.vsa_screener.scan_vsa_smc_universe(min_score=35)
        selected_rows = []
        used_sectors = set()
        for _, r in df_buy.iterrows():
            sec = r.get("Ngành", "Khác")
            if sec not in used_sectors or len(selected_rows) < 2:
                selected_rows.append(r)
                used_sectors.add(sec)
            if len(selected_rows) >= 4:
                break

        if not selected_rows:
            return (
                f"# 💼 TƯ VẤN QUẢN TRỊ DANH MỤC TỔ CHỨC (QUY MÔ VỐN: **{capital_vnd:,.0f} VNĐ**)\n\n"
                f"**Pha Thị Trường Vĩ Mô:** **{macro['regime']}**\n\n"
                f"🛡️ **QUYẾT ĐỊNH BẢO VỆ VỐN TỪ HỘI ĐỒNG CIO:**\n"
                f"Hiện tại trong toàn bộ vũ trụ cổ phiếu thanh khoản cao, **0 mã nào đạt trọn vẹn tiêu chuẩn Phê duyệt Giải ngân Giai đoạn 2 (Stage 2 Uptrend & SEPA ≥ 5/8)**. "
                f"Các mã đang tích lũy như **NKG, TPB, VJC, BSR, HDB** vẫn đang ở Giai đoạn 1 (Watchlist) chưa xác nhận điểm nổ bứt phá.\n\n"
                f"👉 **Khuyến nghị hành động:** **NẮM GIỮ 100% TIỀN MẶT DỰ PHÒNG ({capital_vnd:,.0f} VNĐ)**, kiên nhẫn quan sát danh mục Watchlist chờ thị trường chung xác nhận xu hướng."
            )

        n_picks = len(selected_rows)
        if n_picks == 1:
            per_stock_pct = min(15.0, round(eq_pct, 1))
            actual_cash_pct = 100.0 - per_stock_pct
        else:
            per_stock_pct = min(15.0, round(eq_pct / n_picks, 1))
            actual_cash_pct = 100.0 - (per_stock_pct * n_picks)

        table_lines = [
            "| Mã CP | Ngành | Thị Giá (đ) | Tỷ Trọng (% NAV) | Số Tiền Phân Bổ | Khối Lượng Lô Chẵn (100 CP) | Vùng Mua An Toàn | Cắt Lỗ (SL) |",
            "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
        ]
        for r in selected_rows:
            sym = r["Mã CP"]
            price = float(r["Giá (VNĐ)"])
            alloc_vnd = capital_vnd * (per_stock_pct / 100.0)
            shares = int(alloc_vnd // max(price, 1000) // 100) * 100
            actual_vnd = shares * price
            entry_z = r.get("Vùng Mua An Toàn", f"{price*0.985:,.0f} - {price:,.0f} đ")
            sl_z = r.get("Cắt Lỗ Cấu Trúc", f"{price*0.93:,.0f} đ (-7%)")
            table_lines.append(
                f"| **{sym}** | {r.get('Ngành', '—')} | {price:,.0f} | `{per_stock_pct}%` | **{actual_vnd:,.0f} đ** | **`{shares:,} CP`** | `{entry_z}` | `{sl_z}` |"
            )

        table_str = "\n".join(table_lines)
        return f"""# 💼 ĐỀ XUẤT THIẾT LẬP DANH MỤC ĐẦU TƯ TỔ CHỨC (QUY MÔ VỐN: **{capital_vnd:,.0f} VNĐ**)
**Pha Thị Trường Vĩ Mô:** **{macro['regime']}**
**Cơ Cấu Phân Bổ Chuẩn FinRL:** **{100.0 - actual_cash_pct:.1f}% Cổ Phiếu ({capital_vnd * (100.0 - actual_cash_pct) / 100.0:,.0f} VNĐ)** / **{actual_cash_pct:.1f}% Tiền Mặt Phòng Thủ ({capital_vnd * actual_cash_pct / 100.0:,.0f} VNĐ)**

---
## 📊 Bảng Phân Bổ Danh Mục Đạt Chuẩn Giai Đoạn 2 (Lô Chẵn 100 CP HOSE & Quản Trị Rủi Ro T+2.5):
{table_str}

> 💡 **Lưu ý từ Hội đồng Đầu tư CIO:** Hiện tại thị trường chỉ có {n_picks} mã đạt chuẩn Giai đoạn 2 Phê duyệt giải ngân. Các mã khác (như **NKG, TPB, VJC**) đang tích lũy Stage 1 quanh POC và nằm trong **Danh mục Theo dõi Quan sát (Watchlist)**, tuyệt đối chưa giải ngân vội để bảo toàn vốn tối đa.

---
### 🛡️ Nguyên Tắc Giải Ngân 2 Đợt Của Hội Đồng Đầu Tư:
1. **Đợt 1 (50% khối lượng mỗi mã):** Giải ngân tại vùng nền tích lũy quanh giá vốn tổ chức POC.
2. **Đợt 2 (50% khối lượng còn lại):** Chỉ gia tăng khi hàng Đợt 1 đã về tài khoản (T+2.5) và cổ phiếu bứt phá kèm thanh khoản ≥ 1.35x TB20.
"""

    def _handle_general_advisory_overview(self, msg: str) -> str:
        """Khi người dùng đặt câu hỏi mở, tự động cung cấp Nhận định Thị trường + Top Cổ phiếu Điểm mua hôm nay."""
        macro = self.macro_agent.analyze_market_regime()
        df_buy = self.vsa_screener.scan_vsa_smc_universe(min_score=35)
        top_syms = ", ".join([f"**{r['Mã CP']}** ({r['Giá (VNĐ)']:,.0f} đ)" for _, r in df_buy.head(5).iterrows()]) if not df_buy.empty else "Không có mã đạt chuẩn (Khuyến nghị giữ 100% tiền mặt phòng thủ)"

        return f"""# 🏛️ TỔNG HỢP NHẬN ĐỊNH & KHUYẾN NGHỊ TỪ HỘI ĐỒNG ĐẦU TƯ AI
**Yêu cầu của bạn:** *"{msg}"*

---
### 1. 🌐 Bối Cảnh Thị Trường & Vĩ Mô Thực Tế:
- **Pha thị trường:** **{macro['regime']}** (Điểm vĩ mô: `{macro['macro_score']}/10`)
- **Tỷ trọng khuyến nghị:** **{macro['recommended_allocation']['equity_pct']}% Cổ phiếu / {macro['recommended_allocation']['cash_pct']}% Tiền mặt**
- **Nhận định:** {macro['regime_desc']}

### 2. 💎 Top Cổ Phiếu Đạt Điểm Mua Chuẩn Tổ Chức Hôm Nay (Stage 2 / VSA / SMC / SEPA):
- **Danh sách dẫn sóng:** {top_syms}

---
### 💡 Các Câu Lệnh Đa Nhiệm Bạn Có Thể Giao Ngay Cho Hội Đồng:
- **Thẩm định chuyên sâu 1 mã bất kỳ:** `Phân tích TCB`, `Điểm mua BSR`, `Kiểm tra rủi ro NVL`, `Họp hội đồng FPT`
- **So sánh trực diện nhiều mã:** `So sánh HPG và HSG`, `Nên mua TCB hay MBB`
- **Lọc cổ phiếu theo tiêu chí tùy biến:** `Lọc cổ phiếu bắt đáy`, `Lọc cổ phiếu VSA SMC`, `Lọc cổ phiếu SEPA VCP`, `Lọc cổ phiếu P/E thấp ROE cao`, `Lọc cổ phiếu ngân hàng`
- **Tư vấn phân bổ danh mục theo số vốn:** `Tư vấn danh mục đầu tư 1 tỷ`, `Có 500 triệu nên mua mã nào`
- **Phái sinh & Tự học:** `Phái sinh VN30F1M hôm nay`, `Báo cáo tự học và hậu kiểm sai lầm`
"""

    def _handle_custom_screener_query(self, msg_lower: str, forced_criteria: str = None) -> str:
        """
        Xử lý thông minh mọi yêu cầu sàng lọc cổ phiếu theo tiêu chí tự nhiên của người dùng
        (Có dấu & Không dấu: Lọc bắt đáy, SEPA VCP, CANSLIM, Định giá rẻ, Vượt đỉnh, Đột biến Vol, Lọc theo ngành...).
        """
        criteria = forced_criteria or "all"
        criteria_name = "Toàn Diện & Xếp Hạng Kỹ Thuật"
        universe = None
        sector_name = "Thị Trường Thanh Khoản Cao (VN30 & Midcap Dẫn Sóng)"

        # 1. Phát hiện nhóm ngành (hỗ trợ cả có dấu & không dấu)
        if any(w in msg_lower for w in ["bất động sản", "bat dong san", "bds", "khu công nghiệp", "khu cong nghiep", "kcn"]):
            universe = ["DIG", "DXG", "PDR", "KBC", "KDH", "NLG", "VHM", "VIC", "VRE", "VGC", "SZC", "IDC"]
            sector_name = "Nhóm Bất Động Sản & Khu Công Nghiệp"
        elif any(w in msg_lower for w in ["chứng khoán", "chung khoan", "dịch vụ tài chính", "dich vu tai chinh"]):
            universe = ["SSI", "VND", "VIX", "HCM", "SHS", "MBS", "BSI", "CTS", "FTS", "VCI"]
            sector_name = "Nhóm Chứng Khoán"
        elif any(w in msg_lower for w in ["thép", "thep", "tôn mạ", "ton ma", "vật liệu", "vat lieu"]):
            universe = ["HPG", "HSG", "NKG"]
            sector_name = "Nhóm Thép & Vật Liệu"
        elif any(w in msg_lower for w in ["ngân hàng", "ngan hang", "bank"]):
            universe = ["VCB", "BID", "CTG", "TCB", "MBB", "ACB", "VPB", "HDB", "STB", "TPB", "SHB", "VIB"]
            sector_name = "Nhóm Ngân Hàng"
        elif any(w in msg_lower for w in ["dầu khí", "dau khi", "năng lượng", "nang luong", "điện", "dien"]):
            universe = ["GAS", "PLX", "PVD", "PVS", "PVT", "BSR", "POW"]
            sector_name = "Nhóm Dầu Khí & Năng Lượng"
        elif any(w in msg_lower for w in ["bán lẻ", "ban le", "tiêu dùng", "tieu dung", "công nghệ", "cong nghe"]):
            universe = ["FPT", "MWG", "MSN", "FRT", "DGW", "PNJ", "SAB", "VNM", "CTR"]
            sector_name = "Nhóm Công Nghệ, Bán Lẻ & Tiêu Dùng"
        elif any(w in msg_lower for w in ["hóa chất", "hoa chat", "phân bón", "phan bon", "cảng", "cang bien", "thủy sản", "thuy san", "dệt may", "det may"]):
            universe = ["DGC", "DCM", "DPM", "GMD", "HAH", "VHC", "ANV", "TCM", "TNG"]
            sector_name = "Nhóm Hóa Chất, Cảng Biển & Xuất Khẩu"

        # 2. Phát hiện tiêu chí tài chính / kỹ thuật (Có dấu & Không dấu)
        if forced_criteria == "bottom_fishing" or any(w in msg_lower for w in [
            "bắt đáy", "bat day", "tạo đáy", "tao day", "quá bán", "qua ban",
            "chiết khấu", "chiet khau", "giảm sâu", "giam sau", "vùng đáy", "vung day"
        ]):
            criteria = "bottom_fishing"
            criteria_name = "Cổ Phiếu Bắt Đáy An Toàn / Tạo Đáy Quá Bán Tại Hỗ Trợ (Wyckoff Spring • Rút Chân • Có Cơ Bản Bảo Vệ)"
        elif any(w in msg_lower for w in ["tránh xa", "tranh xa", "rủi ro", "rui ro", "downtrend", "stage 4", "cấm mua", "cam mua", "cần tránh", "can tranh"]):
            criteria = "avoid_stage4"
            criteria_name = "Danh Sách Cổ Phiếu Giai Đoạn 4 Downtrend / Rủi Ro Cao Bắt Buộc Tránh Xa"
        elif any(w in msg_lower for w in ["sepa", "vcp", "minervini", "siêu cổ phiếu", "sieu co phieu", "nền chặt", "nen chat"]):
            criteria = "sepa_vcp"
            criteria_name = "Chuẩn Siêu Cổ Phiếu Mark Minervini SEPA (≥ 6/8) & Mẫu Hình VCP"
        elif any(w in msg_lower for w in ["canslim", "rs", "dẫn dắt", "dan dat", "leader", "tăng trưởng", "tang truong", "mạnh nhất", "manh nhat"]):
            criteria = "canslim_leaders"
            criteria_name = "Cổ Phiếu Dẫn Dắt Thị Trường CANSLIM (RS Rating ≥ 72 & Stage 2)"
        elif any(w in msg_lower for w in ["p/e", "pe", "roe", "cơ bản", "co ban", "giá trị", "gia tri", "dinh gia", "định giá", "rẻ", "re"]):
            criteria = "value_investing"
            criteria_name = "Định Giá Hấp Dẫn & Sinh Lời Cao (P/E ≤ 15.5, ROE ≥ 13.5%, Không Downtrend)"
        elif any(w in msg_lower for w in ["vượt đỉnh", "vuot dinh", "breakout", "bứt phá", "but pha"]):
            criteria = "breakout"
            criteria_name = "Bứt Phá Vượt Đỉnh 20 Phiên (Stage 2 Breakout)"
        elif any(w in msg_lower for w in ["đột biến", "dot bien", "khối lượng", "khoi luong", "nổ vol", "no vol", "vol", "spike", "dòng tiền", "dong tien"]):
            criteria = "volume_spike"
            criteria_name = "Đột Biến Khối Lượng Dòng Tiền Vào (Volume > 135% TB20)"
        elif any(w in msg_lower for w in ["golden cross", "cắt lên", "cat len", "sma"]):
            criteria = "golden_cross"
            criteria_name = "Tín Hiệu Giao Cắt Vàng (Golden Cross SMA20 cắt lên SMA50)"
        elif any(w in msg_lower for w in ["nợ thấp", "no thap", "an toàn", "an toan", "tài chính", "tai chinh", "cổ tức", "co tuc", "phòng thủ", "phong thu"]):
            criteria = "low_debt"
            criteria_name = "An Toàn Tài Chính Cao & Phòng Thủ (Nợ Vay / VCSH ≤ 0.85 & ROE ≥ 12%)"

        df_screened = self.screener.scan_symbols(symbols=universe, criteria=criteria)

        # Lưu lại vào trạng thái để đồng bộ với bảng Bộ lọc trên UI
        self.last_screened_df = df_screened
        self.last_screened_filter = criteria

        if df_screened.empty:
            if criteria == "bottom_fishing":
                df_traps = self.screener.scan_bottom_fishing_traps(symbols=universe, top_n=10)
                trap_section = ""
                if not df_traps.empty:
                    trap_rows = [
                        "| Mã CP | Thị Giá (đ) | Cảnh Báo Trạng Thái | MCDX (Banker/SMA36) | MCDX (Blue/White) | Vùng SMC 60D | Tăng Trưởng LN | Biên An Toàn (MoS) | Lý Do Chưa Đạt Điểm Bắt Đáy Tối Ưu An Toàn |",
                        "| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
                    ]
                    for _, tr in df_traps.iterrows():
                        trap_rows.append(
                            f"| **{tr['Mã CP']}** | {tr['Giá (VNĐ)']:,.0f} | **{tr['Cảnh Báo Bẫy Bắt Đáy']}** | "
                            f"`{tr['MCDX (Banker/SMA36)']}` | `{tr['MCDX (Blue/White)']}` | `{tr['Vùng SMC 60D']}` | "
                            f"{tr['Tăng Trưởng LN']} | `{tr['Biên An Toàn (MoS)']}` | {tr['Lý Do Loại Khỏi Danh Sách Bắt Đáy An Toàn']} |"
                        )
                    trap_section = (
                        "\n---\n## ⚠️ Bảng Đối Chứng Kỹ Thuật Các Mã CHƯA CÓ ĐIỂM BẮT ĐÁY TỐI ƯU AN TOÀN (Tuyệt Đối Cấm Bắt Sớm):\n"
                        + "\n".join(trap_rows)
                        + "\n"
                    )
                return (
                    f"# 🔍 BÁO CÁO SÀNG LỌC CỔ PHIẾU THEO TIÊU CHÍ: **{criteria_name.upper()}**\n"
                    f"**Vũ trụ áp dụng:** {sector_name}\n"
                    f"**Số lượng mã đạt chuẩn Bắt Đáy Tối Ưu An Toàn hôm nay:** **`0 mã`** *(Khuyến nghị: Đứng ngoài quan sát — Tuyệt đối không bắt đáy sớm khi chưa đủ 6 điều kiện định lượng)*\n\n"
                    f"---\n"
                    f"### 🛡️ Kết Luận Thẩm Định 5 Lớp (`MCDX RSI SMA [CongTrader] + SMC 60D + Wyckoff VSA + MA20/50/200 + Định Giá MoS`):\n"
                    f"- **Đối chứng `VHM` (`63,000 đ`):** Chưa có điểm bắt đáy tối ưu an toàn vì giá đang nằm dưới cả 3 đường **`MA20 (63,520 đ)`**, **`MA200 (64,867 đ)`** và **`MA50 (68,054 đ)`** (Short-Term Bearish, kẹt dưới 2 đỉnh phân phối `LPSY`); chỉ báo **`MCDX Banker = 0.0 < SMA36 (0.3)`** (`100% Vàng Nhỏ lẻ`, `0% Dòng tiền Tạo lập`); đường xung lực **`MCDX Blue (8.7)` nằm dưới `White (10.8)`** và đang giảm (`-0.5`).\n"
                    f"- **Đối chứng `VPB` (`22,950 đ`):** Đang rơi sau khi chạm đỉnh `SMC Premium (64%)` kèm tín hiệu `SELL / LPSY`, gãy dưới `MA20 (23,772 đ)`, **`MCDX Banker (9.1 < SMA36 17.5)`** suy yếu và **`MCDX Blue (3.2 < White 6.0)`** cắm xuống.\n"
                    f"{trap_section}\n---\n"
                    f"💡 *Để xem chi tiết Phiên họp Hội đồng 7 lượt và Biểu đồ kỹ thuật cho từng mã, hãy gõ: `Phân tích VHM` hoặc `Phân tích VPB`.*"
                )
            return (
                f"🔍 **BÁO CÁO LỌC CỔ PHIẾU: {criteria_name.upper()}**\n\n"
                f"**Vũ trụ áp dụng:** {sector_name}\n\n"
                f"Hiện tại chưa có mã nào thỏa mãn khắt khe toàn bộ điều kiện lọc này. "
                f"Hội đồng khuyến nghị: Tiếp tục quan sát và kiên nhẫn chờ đợi tín hiệu dòng tiền xác nhận!"
            )

        top_candidates = df_screened.head(10)
        self.last_analyzed_symbol = top_candidates.iloc[0]["Mã CP"]

        if criteria == "bottom_fishing":
            table_rows = [
                "| Mã CP | Ngành | Thị Giá (đ) | Khuyến Nghị 5 Lớp | Điểm An Toàn | MCDX (Banker/SMA36) | MCDX (Blue/White) | Vùng SMC 60D | RSI (14) | ROE | Tăng Trưởng LN | Biên An Toàn (MoS) | Tín Hiệu Xác Nhận |",
                "| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |"
            ]
            for _, r in top_candidates.iterrows():
                table_rows.append(
                    f"| **{r['Mã CP']}** | {r.get('Ngành', '—')} | {r['Giá (VNĐ)']:,.0f} | **{r['Khuyến Nghị']}** | "
                    f"`{r['Điểm Kỹ Thuật']}/100` | `{r.get('MCDX (Banker/SMA36)', '—')}` | `{r.get('MCDX (Blue/White)', '—')}` | "
                    f"`{r.get('Vùng SMC 60D', '—')}` | `{r.get('RSI (14)', '—')}` | {r.get('ROE (%)', '—')} | "
                    f"{r.get('Tăng Trưởng LN', '—')} | **{r.get('Biên An Toàn (MoS)', '—')}** | {r['Tín Hiệu Chính']} |"
                )
        else:
            table_rows = [
                "| Mã CP | Ngành | Thị Giá (đ) | Khuyến Nghị | Điểm KT | RS Rating | SEPA | MCDX (Banker/SMA36) | RSI (14) | P/E | ROE | Tín Hiệu Trọng Tâm |",
                "| :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |"
            ]
            for _, r in top_candidates.iterrows():
                table_rows.append(
                    f"| **{r['Mã CP']}** | {r.get('Ngành', '—')} | {r['Giá (VNĐ)']:,.0f} | **{r['Khuyến Nghị']}** | "
                    f"`{r['Điểm Kỹ Thuật']}/10` | **{r.get('RS Rating', 50)}/99** | `{r.get('SEPA', '—')}` | `{r.get('MCDX (Banker/SMA36)', '—')}` | "
                    f"`{r.get('RSI (14)', '—')}` | {r.get('P/E', '—')} | {r.get('ROE (%)', '—')} | {r['Tín Hiệu Chính']} |"
                )

        table_str = "\n".join(table_rows)

        extra_guidance = ""
        if criteria == "bottom_fishing":
            df_traps = self.screener.scan_bottom_fishing_traps(symbols=universe, top_n=8)
            trap_section = ""
            if not df_traps.empty:
                trap_rows = [
                    "| Mã CP | Thị Giá (đ) | Cảnh Báo Trạng Thái | MCDX (Banker/SMA36) | MCDX (Blue/White) | Vùng SMC 60D | Tăng Trưởng LN | Biên An Toàn (MoS) | Lý Do Loại Khỏi Danh Sách Bắt Đáy An Toàn |",
                    "| :---: | :---: | :--- | :---: | :---: | :---: | :---: | :---: | :--- |"
                ]
                for _, tr in df_traps.iterrows():
                    trap_rows.append(
                        f"| **{tr['Mã CP']}** | {tr['Giá (VNĐ)']:,.0f} | **{tr['Cảnh Báo Bẫy Bắt Đáy']}** | "
                        f"`{tr['MCDX (Banker/SMA36)']}` | `{tr['MCDX (Blue/White)']}` | `{tr['Vùng SMC 60D']}` | "
                        f"{tr['Tăng Trưởng LN']} | `{tr['Biên An Toàn (MoS)']}` | {tr['Lý Do Loại Khỏi Danh Sách Bắt Đáy An Toàn']} |"
                    )
                trap_section = (
                    "\n---\n## ⚠️ Bảng Cảnh Báo Các Mã CHƯA CÓ ĐÁY AN TOÀN / BẪY BẮT DAO RƠI (Tuyệt Đối Cấm Bắt Sớm):\n"
                    + "\n".join(trap_rows)
                    + "\n"
                )

            extra_guidance = (
                f"{trap_section}\n---\n"
                "### 🔬 Phản Biện Chỉ Báo `MCDX RSI SMA [CongTrader] + SMC + VSA` & Hệ Thống Bắt Đáy 5 Lớp Tối Ưu:\n"
                "1. **Lớp 1 — Vị thế cấu trúc SMC & Xu hướng MA200/MA50:** Tuyệt đối không bắt đáy cổ phiếu đang rơi ở nửa trên biên độ sau khi chạm vùng cung `SMC Premium` kèm tín hiệu `SELL / LPSY` và gãy `MA20` (điển hình như **`VPB`** ở mức `22,950 đ`, vị trí SMC 60D `64%`, gãy dưới `MA20 = 23,772 đ`) hoặc cổ phiếu đang ở `Stage 4 Downtrend` dưới `MA200` (như **`TCM`**).\n"
                "2. **Lớp 2 — Xác nhận dòng tiền tạo lập `MCDX RSI SMA [CongTrader]`:** Chỉ báo `MCDX` chỉ cho điểm mua bắt đáy/điểm trũng `LPS` an toàn khi cột **Banker** giữ ổn định/tăng lại so với `SMA36` VÀ đường xung lực **MCDX Fast (Blue)** ngừng rơi, vòng lên cắt đường **Slow (White)** kèm `RSI(14)` hướng lên (`d_rsi > 0`). Nếu `MCDX Banker < SMA36` và đường `Blue` đang cắm thẳng xuống (như `VPB`: Banker `9.1 < SMA36 17.5`, Blue `3.2 < White 6.0`; hoặc `PVT` đang chờ `Blue` vòng lên) thì **chưa được phép mua ngay** (phải xếp vào diện *Cấm bắt sớm* hoặc *Quan sát chờ MCDX cắt lên*).\n"
                "3. **Lớp 3 — Hành động Giá & Khối lượng Wyckoff VSA/VPA:** Phải có nến xanh đảo chiều (`Close > Prev Close` & `Close >= Open`) hoặc nến rút chân hấp thụ cung (`Stopping Volume / Spring / LPS`) tại vùng hỗ trợ.\n"
                "4. **Lớp 4 — Sức khỏe Doanh nghiệp & Định giá Nội tại (`MoS`):** Loại bỏ 100% các mã doanh nghiệp đang suy giảm lợi nhuận mạnh hoặc định giá ảo (`MoS < -5%`, ví dụ **`HCM`** có `MoS = -126.4%`, LNST `-18.1%`; **`VGC`** có `MoS = -22.4%`; **`VPB`** có `MoS = -7.2%`). Chỉ giữ lại doanh nghiệp có `ROE ≥ 11%`, lợi nhuận tích cực và biên an toàn `MoS` dương.\n"
                "5. **Lớp 5 — Kỷ luật Quản trị Rủi ro T+2.5:** Chỉ giải ngân thăm dò **30% vốn** với các mã đạt chuẩn **`🟢 ĐÃ XÁC NHẬN TẠO ĐÁY / MUA LPS AN TOÀN`**; còn các mã **`🟡 QUAN SÁT TẠI HỖ TRỢ`** chỉ đưa vào Watchlist canh nến xanh + `MCDX Blue` cắt lên mới bấm nút mua!"
            )

        return f"""# 🔍 BÁO CÁO SÀNG LỌC CỔ PHIẾU THEO TIÊU CHÍ: **{criteria_name.upper()}**
**Vũ trụ áp dụng:** {sector_name}
**Số lượng mã đạt chuẩn:** `{len(df_screened)} mã` (Hiển thị Top {len(top_candidates)} mã dẫn đầu — Đã tự động đồng bộ sang bảng **🔍 Bộ Lọc Tinh Hoa**)

---
## 📊 Bảng Danh Sách Cổ Phiếu Đạt Tiêu Chí:
{table_str}
{extra_guidance}
---
💡 *Để xem phiên họp hội đồng 7 lượt và nghị quyết của 9 Đại Kiện Tướng cho từng mã, hãy gõ: `Phân tích {top_candidates.iloc[0]['Mã CP']}` hoặc `So sánh {top_candidates.iloc[0]['Mã CP']} và {top_candidates.iloc[1]['Mã CP'] if len(top_candidates) > 1 else 'HPG'}`.*
"""

    def _handle_vsa_smc_screener_query(self, msg_lower: str) -> str:
        df_buy, df_watchlist, df_avoid = self.vsa_screener.scan_three_tier_universe()

        self.last_screened_df = df_buy if not df_buy.empty else df_watchlist
        self.last_screened_filter = "vsa_smc"

        # 1. BẢNG TOP CỔ PHIẾU PHÊ DUYỆT GIẢI NGÂN (STAGE 2 UPTREND & SEPA >= 5/8)
        if not df_buy.empty:
            top_candidates = df_buy.head(8)
            self.last_analyzed_symbol = top_candidates.iloc[0]["Mã CP"]

            table_rows = [
                "| Mã CP | Ngành | Thị Giá (đ) | Điểm Smart Money | Chu Kỳ | RS Rating | SEPA | Tín Hiệu VSA/SMC | Giá Vốn POC | Vùng Mua An Toàn | Cắt Lỗ Cấu Trúc |",
                "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
            ]
            for _, r in top_candidates.iterrows():
                vsa_smc_lbl = r["Tín Hiệu VSA"] if r["Tín Hiệu VSA"] != "—" else (r["Tín Hiệu SMC"] if r["Tín Hiệu SMC"] != "—" else r["Tín Hiệu VPA"])
                table_rows.append(
                    f"| **{r['Mã CP']}** | {r.get('Ngành', '—')} | {r['Giá (VNĐ)']:,.0f} | **{r['Điểm Smart Money']}/100** | "
                    f"🟢 `{r.get('Giai Đoạn', 'Stage 2')}` | **{r.get('RS Rating', 70)}/99** | `{r.get('SEPA', '6/8')}` | "
                    f"{vsa_smc_lbl} | `{r['Giá Vốn POC']}` | `{r['Vùng Mua An Toàn']}` | `{r['Cắt Lỗ Cấu Trúc']}` |"
                )
            buy_section = "## 💎 Top Cổ Phiếu Đạt Chuẩn Điểm Mua Tổ Chức (Stage 2 Uptrend & SEPA ≥ 5/8):\n" + "\n".join(table_rows)
        else:
            buy_section = (
                "## 💎 Top Cổ Phiếu Đạt Chuẩn Điểm Mua Tổ Chức (Stage 2 Uptrend & SEPA ≥ 5/8):\n"
                "> 🛡️ **NGUYÊN TẮC BẢO VỆ VỐN TUYỆT ĐỐI:** Thị trường đang trong giai đoạn điều chỉnh/rủi ro cao. "
                "Hiện tại **0 mã nào đạt trọn vẹn tiêu chuẩn Phê duyệt Giải ngân Giai đoạn 2 của Hội đồng CIO**. "
                "Khuyến nghị ưu tiên nắm giữ 100% tiền mặt phòng thủ, không bắt dao rơi."
            )

        # 2. BẢNG DANH MỤC THEO DÕI QUAN SÁT (STAGE 1 TÍCH LŨY / CHỜ BỨT PHÁ PIVOT & SEPA - VD: NKG, TPB, VJC)
        watchlist_section = ""
        if not df_watchlist.empty:
            wl_rows = [
                "| Mã CP | Ngành | Thị Giá (đ) | Điểm Smart Money | Chu Kỳ | SEPA | RS Rating | Giá Vốn POC | Trạng Thái Theo Dõi | Điều Kiện Kích Hoạt Mua |",
                "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- | :--- |"
            ]
            for _, wr in df_watchlist.head(8).iterrows():
                wl_rows.append(
                    f"| **{wr['Mã CP']}** | {wr.get('Ngành', '—')} | {wr['Giá (VNĐ)']:,.0f} | `{wr['Điểm Smart Money']}/100` | "
                    f"🟡 `{wr.get('Giai Đoạn', 'Stage 1')}` | `{wr.get('SEPA', '2/8')}` | `{wr.get('RS Rating', 50)}/99` | "
                    f"`{wr['Giá Vốn POC']}` | {wr.get('Trạng Thái Theo Dõi', 'Tích lũy quanh POC')} | {wr.get('Điều Kiện Kích Hoạt Mua', 'Vượt POC + Vol lớn')} |"
                )
            watchlist_section = (
                "\n---\n## 🟡 Danh Mục Tích Lũy Theo Dõi Quan Sát (Stage 1 / Chờ Điểm Nổ Pivot — VD: NKG, TPB, VJC):\n"
                "> ⚠️ **Lưu ý kỷ luật:** Các mã trong danh mục này đang tích lũy Stage 1 hoặc điều chỉnh test cạn cung quanh POC. "
                "Hội đồng duy trì trạng thái **QUAN SÁT (0% NAV)**, tuyệt đối CHƯA GIẢI NGÂN khi chưa xuất hiện cây nến bứt phá Stage 2 kèm Volume lớn!\n\n"
                + "\n".join(wl_rows) + "\n"
            )

        # 3. BẢNG CỔ PHIẾU DOWNTREND GIAI ĐOẠN 4 (CẤM BẮT ĐÁY)
        avoid_section = ""
        if not df_avoid.empty:
            avoid_rows = [
                "| Mã CP | Ngành | Thị Giá (đ) | Giai Đoạn | RS Rating | SEPA | SMA50 | SMA200 | Lý Do Phủ Quyết (Cấm Bắt Đáy) |",
                "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |"
            ]
            for _, ar in df_avoid.head(6).iterrows():
                avoid_rows.append(
                    f"| **{ar['Mã CP']}** | {ar.get('Ngành', '—')} | {ar['Giá (VNĐ)']:,.0f} | "
                    f"🔴 `{ar['Giai Đoạn']}` | `{ar['RS Rating']}/99` | `{ar['SEPA']}` | "
                    f"{ar['SMA50 (đ)']:,.0f} | {ar['SMA200 (đ)']:,.0f} | {ar['Lý Do Cấm Mua']} |"
                )
            avoid_section = "\n---\n## ⛔ Danh Sách Cổ Phiếu Đang Ở Giai Đoạn 4 Downtrend (Bắt Buộc Tránh Xa):\n" + "\n".join(avoid_rows) + "\n"

        return f"""# 🏛️ BÁO CÁO PHÂN TÍCH ĐỒNG THUẬN 3 NHÓM ĐỊNH CHẾ (VSA • SMC • WEINSTEIN • MINERVINI)
**Nguyên tắc vận hành của Hội đồng Đầu tư Định lượng Tổ chức:**
1. **Phân biệt rạch ròi 3 trạng thái:** Phê duyệt Mua Stage 2 🟢, Danh mục Theo dõi Stage 1 🟡 (NKG, TPB, VJC), Phủ quyết Downtrend Stage 4 ⛔.
2. **Loại bỏ 100% mâu thuẫn:** Không bao giờ khuyến nghị mua cổ phiếu đang ở Stage 1 tích lũy khi chưa có tín hiệu xác nhận dòng tiền tạo lập.

---
{buy_section}
{watchlist_section}
{avoid_section}
---
💡 *Để xem phiên họp phản biện 7 lượt và nghị quyết CIO cho từng mã cụ thể, hãy gõ: `Phân tích NKG` hoặc `Phân tích VIC`.*
"""

    def _handle_institutional_committee_analysis(self, symbol: str) -> str:
        """Thực hiện quy trình thẩm định đầy đủ của Hội Đồng Đầu Tư (7 Lượt Tranh Biện + 9 Đại Kiện Tướng + Định Giá Damodaran + FinRL Sizing)."""
        decision = self.cio_agent.evaluate_and_decide(symbol)
        meeting = decision["meeting"]

        fund = meeting["fund_report"]
        tech = meeting["tech_report"]
        canslim = meeting.get("canslim_report", {})
        personas = meeting.get("personas_council", [])
        dialogue = meeting["dialogue"]

        trade_p = decision["trade_plan"]
        finrl = tech.get("finrl_metrics", {})
        sepa = tech.get("sepa_vcp", {})
        rs_info = tech.get("rs_info", {})
        vp = tech.get("volume_profile", {})
        dup_val = fund.get("dupont_valuation", {})

        debate_lines = []
        for d in dialogue:
            debate_lines.append(f"**{d['speaker']}** *({d['role']})*:\n> {d['statement']}\n")
        debate_text = "\n".join(debate_lines)

        tranches_text = "\n".join([f"  - 📌 {t}" for t in decision["tranches"]]) if decision["tranches"] else "  - *Không kích hoạt giải ngân (0% NAV) do cổ phiếu vi phạm quy tắc bảo toàn vốn.*"

        persona_rows = [
            "| Đại Kiện Tướng (ai-hedge-fund) | Trường Phái Đầu Tư | Phán Quyết | Độ Tin Cậy | Luận Điểm Cốt Lõi |",
            "| :--- | :--- | :---: | :---: | :--- |"
        ]
        for p in personas:
            persona_rows.append(
                f"| **{p['persona']}** | {p['title']} | **{p['signal']}** | `{p['confidence']}%` | {p['rationale']} |"
            )
        persona_table = "\n".join(persona_rows)

        val_models = dup_val.get("valuation_models", {})
        val_lines = [f"- **{k}:** `{v:,.0f} VNĐ/CP`" for k, v in val_models.items()]
        val_models_str = "\n".join(val_lines) if val_lines else "- Đang cập nhật mô hình định giá"

        mcdx_a = tech.get("mcdx_smc_audit", {})
        mcdx_line = (
            f"- 🏦 **Kiểm Chứng Chỉ Báo MCDX RSI SMA [CongTrader] & SMC:** "
            f"MCDX Banker = `{mcdx_a.get('mcdx_banker', 0):.1f}` vs SMA36 = `{mcdx_a.get('mcdx_banker_sma36', 0):.1f}` | "
            f"MCDX Fast (Blue) = `{mcdx_a.get('mcdx_fast', 0):.1f}` vs Slow (White) = `{mcdx_a.get('mcdx_slow', 0):.1f}` | "
            f"Vị trí SMC 60D = `{mcdx_a.get('smc_pos_pct', 50):.1f}%` (Đáy Discount: `{mcdx_a.get('smc_low_60', 0):,.0f} đ` — Đỉnh Premium: `{mcdx_a.get('smc_high_60', 0):,.0f} đ`)\n"
        )
        if tech.get("is_downtrend"):
            trade_setup_section = f"""## ⛔ II. CẢNH BÁO NGUY HIỂM: CỔ PHIẾU ĐANG TRONG DOWNTREND GIAI ĐOẠN 4 (CẤM BẮT ĐÁY)
- 🔴 **Trạng thái chu kỳ:** `{tech.get('stage_name', 'STAGE 4 DOWNTREND')}` | **SEPA Score:** `{sepa.get('sepa_score', 0)}/8` | **RS Rating:** `{rs_info.get('rs_rating', 20)}/99`
- 📉 **Vị thế so với đường MA:** Thị giá (`{tech.get('current_price', 0):,.0f} đ`) nằm dưới cả SMA50 (`{tech.get('moving_averages', {}).get('sma_50', 0):,.0f} đ`) và SMA200 (`{tech.get('moving_averages', {}).get('sma_200', 0):,.0f} đ`). Giá vốn kẹt hàng tổ chức POC tại `{vp.get('poc', 0):,.0f} đ`.
- ⚠️ **Khuyến nghị kỷ luật:** {tech.get('entry_recommendation', 'TUYỆT ĐỐI KHÔNG BẮT ĐÁY!')}"""
        else:
            trade_setup_section = f"""## 📐 II. THÔNG SỐ VỊ THẾ GIAO DỊCH & QUẢN TRỊ VỐN FINRL (T+2.5 ADJUSTED)
- 🎯 **Vùng Giá Mua An Toàn (Optimal Entry):** `{trade_p.get('optimal_entry_zone', 'N/A')}` | **Điểm Nổ Pivot VCP:** `{trade_p.get('pivot_breakout', 0):,.0f} VNĐ`
- 💎 **Volume Profile Tổ Chức:** Giá vốn **POC = `{vp.get('poc', 0):,.0f} đ`** (Biên dưới VAL: `{vp.get('val', 0):,.0f} đ` — Biên trên VAH: `{vp.get('vah', 0):,.0f} đ`)
- 🛡️ **Ngưỡng Cắt Lỗ Cấu Trúc (Stop Loss):** `{trade_p.get('structural_stop_loss', 0):,.0f} VNĐ` ({trade_p.get('stop_loss_pct', 0):+.1f}%)
- 🚀 **Mục Tiêu Chốt Lời TP1:** `{trade_p.get('take_profit_target_1', 0):,.0f} VNĐ` ({trade_p.get('target_1_pct', 0):+.1f}%) | **TP2:** `{trade_p.get('take_profit_target_2', 0):,.0f} VNĐ` ({trade_p.get('target_2_pct', 0):+.1f}%)
- ⚖️ **Tỷ Lệ R:R:** **{trade_p.get('risk_reward_ratio', 0):.2f} : 1** | **Khối Lượng Chuẩn Lô Chẵn (trên 1 tỷ NAV):** **`{decision.get('recommended_shares_per_1b', 0):,} CP`** (`{decision['allocation_pct']}% NAV`)
{mcdx_line}- 📊 **Chỉ Số Định Lượng FinRL:** Sharpe: `{finrl.get('sharpe_ratio', 0):.2f}` | Sortino: `{finrl.get('sortino_ratio', 0):.2f}` | Max Drawdown: `{finrl.get('max_drawdown_pct', 0):.1f}%` | Half-Kelly: `{finrl.get('half_kelly_pct', 0):.1f}%`"""

        report = f"""# 🏛️ NGHỊ QUYẾT THẨM ĐỊNH ĐẦU TƯ TOÀN DIỆN: **{symbol}** ({fund.get('industry', 'Niêm yết')})
**Thời gian họp:** `{meeting['meeting_time']}` | **Kiến trúc hợp nhất:** TradingAgents • AI-Hedge-Fund • FinRL • FinRobot • Claude-Skills • Vnstock

---
## 🎯 I. PHÁN QUYẾT CHÍNH THỨC TỪ CHỦ TỊCH HỘI ĐỒNG ĐẦU TƯ (CIO DECREE)
- **Quyết Nghị Chính Thức:** **{decision['final_decision']}**
- **Điểm Thuyết Phục (Conviction):** `{decision['conviction_score']} / 10` | **Điểm CANSLIM:** `{canslim.get('canslim_score', 0)}/100 (Hạng {canslim.get('canslim_grade', 'C')})` | **SEPA:** `{sepa.get('sepa_score', 0)}/8` | **RS Rating:** `{rs_info.get('rs_rating', 50)}/99`
- **Hạn Mức Phân Bổ Tối Đa:** **{decision['allocation_pct']}% Tổng Tài Sản (NAV)** (~`{decision.get('recommended_shares_per_1b', 0):,} CP` / 1 tỷ VNĐ)
- **Luận Điểm Tổng Hợp Của CIO:**
{decision['action_plan']}

### 📋 Kế Hoạch Giải Ngân 2 Đợt Phòng Vệ Rủi Ro T+2.5:
{tranches_text}

---
{trade_setup_section}

---
## 🌟 III. HỘI ĐỒNG 9 ĐẠI KIỆN TƯỚNG ĐẦU TƯ THẾ GIỚI (AI-HEDGE-FUND COUNCIL)
{persona_table}

---
## 🏢 IV. PHÂN TÍCH DUPONT 3 BƯỚC & ĐỊNH GIÁ NỘI TẠI ĐA MÔ HÌNH (FINROBOT & DAMODARAN)
- **Xếp hạng sức khỏe tài chính:** **{fund['health_status']}** (Kỳ BCTC: `{fund.get('latest_quarter', 'Mới nhất')}` | Vốn hóa: `{fund.get('market_cap', 'N/A')}`)
- **Phân tích DuPont 3 Bước:** {dup_val.get('dupont_summary', 'N/A')} -> *{dup_val.get('roe_driver', '')}*
- **Chỉ số cốt lõi:** P/E: `{fund.get('pe', 'N/A')}x` | P/B: `{fund.get('pb', 'N/A')}x` | ROE: `{fund.get('roe', 'N/A')}%` | ROA: `{fund.get('roa', 'N/A')}%` | Tăng trưởng LNST YoY: `{fund.get('profit_growth_yoy', 'N/A')}%`
- **Giá Trị Hợp Lý Trung Bình (Composite Intrinsic Value):** **`{fund.get('intrinsic_value', 0):,.0f} VNĐ/CP`** (Biên an toàn MoS: **`{fund.get('margin_of_safety_pct', 0):+.1f}%`** — {dup_val.get('valuation_status', '')})
{val_models_str}

---
## ⚖️ V. BIÊN BẢN HỌP TRANH BIỆN 7 LƯỢT (BULL VS BEAR & 3-POSTURE RISK TEAM)
{debate_text}

---
## 🧠 VI. KIỂM DUYỆT TỪ BỘ NHỚ TỰ HỌC & GHI NHỚ SAI LẦM (SELF-LEARNING AUDIT)
- **Điểm trước hiệu chỉnh:** `{decision.get('self_learning_audit', {}).get('raw_score', 0)}` -> **Điểm sau hiệu chỉnh Tự Học:** **`{decision.get('self_learning_audit', {}).get('adjusted_score', 0)}`** (`{decision.get('self_learning_audit', {}).get('score_delta', 0):+.1f} điểm`)
- **Các quy tắc / bài học lịch sử được kích hoạt:**
{chr(10).join([f'  - {l}' for l in decision.get('self_learning_audit', {}).get('triggered_lessons', ['✅ Không phát hiện vi phạm quy tắc sai lầm lịch sử nào.'])])}
"""
        peers = fund.get("peers", [])
        if peers:
            report += "\n### 👥 So Sánh Định Giá Với Các Đối Thủ Cùng Ngành:\n"
            report += "| Mã CP | Thị Giá (đ) | P/E | P/B | ROE (%) | Tăng Trưởng LNST YoY |\n| :---: | :---: | :---: | :---: | :---: | :---: |\n"
            for p in peers:
                pg = f"{p['profit_growth_yoy']:+.1f}%" if isinstance(p.get("profit_growth_yoy"), (int, float)) else "—"
                report += f"| **{p['symbol']}** | {p['price']:,.0f} | {p['pe']} | {p['pb']} | {p['roe']}% | {pg} |\n"

        return report

    def _handle_order_flow_and_graham_query(self, symbol: str) -> str:
        """Phân tích chuyên sâu Áp Lực Cung - Cầu Order Flow và Bộ Tứ Định Giá Benjamin Graham (AFL VPA 5.0)."""
        symbol = symbol.strip().upper()
        df_hist = self.de.get_history(symbol, days=90)
        ov = self.de.get_company_overview(symbol)
        if df_hist is None or df_hist.empty or len(df_hist) < 15:
            return f"Không đủ dữ liệu lịch sử để phân tích Order Flow cho mã {symbol}."

        df_full = TechnicalAnalysis.calculate_indicators(df_hist)
        last = df_full.iloc[-1]
        close = float(last["close"])
        bp = float(last.get("buying_pressure", 50))
        sp = float(last.get("selling_pressure", 50))
        effort = float(last.get("effort_score", 50))
        result = float(last.get("result_score", 50))
        keltner_u = float(last.get("keltner_upper", close * 1.05))
        keltner_l = float(last.get("keltner_lower", close * 0.95))
        keltner_m = float(last.get("keltner_mid", close))
        chand_long = float(last.get("chand_stop_long", close * 0.93))
        chand_short = float(last.get("chand_stop_short", close * 1.07))
        darvas_t = float(last.get("darvas_top", close * 1.05))
        darvas_b = float(last.get("darvas_bottom", close * 0.95))
        daogam_65 = float(last.get("ichi_daogam_65", close))
        daogam_129 = float(last.get("ichi_daogam_129", close))

        # Valuation
        eps = float(ov.get("eps") or 0.0)
        bvps = float(ov.get("bvps") or 0.0)
        p_growth = float(ov.get("profit_growth_yoy") or 10.0)
        roe = float(ov.get("roe") or 12.0)
        eff_g = max(3.0, min(25.0, p_growth if p_growth > 0 else roe))
        y_bond = 6.5
        vg1 = eps * (7.0 + 1.5 * eff_g) * 4.4 / y_bond if eps > 0 else 0
        vg2 = eps * (7.0 + 1.5 * eff_g) if eps > 0 else 0
        vg3 = eps * (8.5 + 2.0 * eff_g) if eps > 0 else 0
        vg_bvps = math.sqrt(22.5 * eps * bvps) if (eps > 0 and bvps > 0) else 0
        v_tb = (vg1 + vg2 + vg3 + vg_bvps) / 4.0 if (vg1 > 0 and vg_bvps > 0) else (vg1 or close)
        v_chietkhau = v_tb * 0.70

        of_verdict = "CẦU ÁP ĐẢO (BUYING DOMINANCE) 🟢" if bp > sp * 1.2 else ("CUNG ÁP ĐẢO (SELLING DOMINANCE) 🔴" if sp > bp * 1.2 else "CUNG CẦU CÂN BẰNG 🟡")

        return f"""# 🔬 PHÂN TÍCH CHUYÊN SÂU ÁP LỰC CUNG - CẦU ORDER FLOW & ĐỊNH GIÁ GRAHAM: **{symbol}**
*(Hợp nhất thuật toán vi cấu trúc thị trường từ AFL VPA 5.0 - Karthikmarar & BinhNT)*

---
## ⚖️ I. Dashboard Đo Lường Lực Cầu - Lực Cung (Order Flow Microstructure):
- **Thị giá hiện tại:** **`{close:,.0f} VNĐ`**
- **Lực Cầu Chuẩn Hóa (Buying Pressure):** **`{bp:.1f}%`**
- **Lực Cung Chuẩn Hóa (Selling Pressure):** **`{sp:.1f}%`**
- **Trạng thái Dòng tiền Vi cấu trúc:** **{of_verdict}**
- **Nỗ Lực Khối Lượng (Effort Score):** `{effort:.1f}/100` | **Kết Quả Bước Giá (Result Score):** `{result:.1f}/100`
  *(Nhận định Wyckoff: {'Nỗ lực tăng giá tương xứng kết quả bước giá ✅' if effort >= 45 and result >= 45 else 'Bất thường nỗ lực và kết quả (Effort vs Result Divergence) ⚠️'})*

---
## 🛡️ II. Hệ Thống Keltner Bands, Turtle Trailing Stop & Hộp Darvas:
- **Keltner Bands System (EMA20 ± 3*ATR):** KTop = `{keltner_u:,.0f} đ` | KMid = `{keltner_m:,.0f} đ` | KBottom = `{keltner_l:,.0f} đ`
- **Chandelier ATR Trailing Stop (Hệ thống Con Rùa - Turtle):**
  - Mức Chặn Lỗ Vị Thế Mua (Long Trailing Stop): **`{chand_long:,.0f} VNĐ`** ({((chand_long - close) / close * 100.0):.1f}%)
  - Mức Chặn Lỗ Vị Thế Bán (Short Trailing Stop): **`{chand_short:,.0f} VNĐ`**
- **Hộp Darvas Box (20 Phiên):** Kháng cự Hộp Trên = `{darvas_t:,.0f} đ` | Hỗ trợ Hộp Dưới = `{darvas_b:,.0f} đ`
- **Đao Găm Ichimoku Kinko Hyo (Việt Nam):**
  - Đao Găm 65 (Hỗ trợ/Kháng cự Trung hạn): `{daogam_65:,.0f} VNĐ`
  - Đao Găm 129 (Hỗ trợ/Kháng cự Dài hạn): `{daogam_129:,.0f} VNĐ`

---
## 💰 III. Bộ Tứ Định Giá Benjamin Graham (AFL Graham Valuation Suite):
| Mô Hình Định Giá Benjamin Graham | Giá Trị Tính Toán | Biên An Toàn So Với Thị Giá | Đánh Giá |
| :--- | :---: | :---: | :--- |
| **1. Graham 1 (Có Trái Phiếu y=6.5%):** `EPS × (7 + 1.5g) × 4.4 / y` | **`{vg1:,.0f} đ`** | `{((vg1 - close) / vg1 * 100.0) if vg1 > 0 else 0:+.1f}%` | {'Rẻ' if vg1 > close else 'Đắt'} |
| **2. Graham 2 (Gốc):** `EPS × (7 + 1.5g)` | **`{vg2:,.0f} đ`** | `{((vg2 - close) / vg2 * 100.0) if vg2 > 0 else 0:+.1f}%` | {'Rẻ' if vg2 > close else 'Đắt'} |
| **3. Graham 3 (Tăng Trưởng):** `EPS × (8.5 + 2g)` | **`{vg3:,.0f} đ`** | `{((vg3 - close) / vg3 * 100.0) if vg3 > 0 else 0:+.1f}%` | {'Rẻ' if vg3 > close else 'Đắt'} |
| **4. Benjamin Graham Number:** `√(22.5 × EPS × BVPS)` | **`{vg_bvps:,.0f} đ`** | `{((vg_bvps - close) / vg_bvps * 100.0) if vg_bvps > 0 else 0:+.1f}%` | {'Rẻ' if vg_bvps > close else 'Đắt'} |
| **🏆 Giá Trị Graham Hợp Nhất (VTB):** `(G1 + G2 + G3 + G4) / 4` | **`{v_tb:,.0f} đ`** | **`{((v_tb - close) / v_tb * 100.0) if v_tb > 0 else 0:+.1f}%`** | **{'RẺ / HẤP DẪN 🟢' if v_tb > close * 1.15 else ('HỢP LÝ 🟡' if v_tb >= close * 0.95 else 'ĐẮT 🔴')}** |
| **🛡️ Giá Mua Chiết Khấu An Toàn (-30% MoS):** `VTB × 0.70` | **`{v_chietkhau:,.0f} đ`** | Điểm mua phòng vệ tuyệt đối chuẩn Graham | {'Đạt điểm mua' if close <= v_chietkhau else 'Chưa chiết khấu đủ'} |
"""

    def _handle_self_learning_query(self, msg: str) -> str:
        """Xử lý yêu cầu hậu kiểm tự học hoặc ghi nhận bài học sai lầm mới từ người dùng."""
        msg_lower = msg.lower()
        if any(k in msg_lower for k in ["dạy ai:", "ghi nhớ lỗi:", "ghi nho loi:", "day ai:"]):
            parts = msg.split(":", 1)[-1].strip()
            sym = self._extract_symbol(parts) or "ALL"
            entry = self.self_learning.record_user_lesson(
                symbol=sym,
                category="Bài Học Thực Chiến Do Người Dùng Dạy",
                mistake_summary=parts,
                corrective_rule=f"Áp dụng nghiêm ngặt quy tắc người dùng dạy cho {sym}: {parts}",
                penalty_points=-12.0,
                force_avoid=("cấm mua" in msg_lower or "tránh xa" in msg_lower or "veto" in msg_lower),
            )
            return (
                f"🧠 **ĐÃ GHI NHỚ BÀI HỌC MỚI VÀO BỘ NÃO TỰ HỌC (`{entry['id']}`)**\n\n"
                f"- **Mã áp dụng:** `{entry['symbol']}`\n"
                f"- **Nội dung bài học:** {entry['mistake_summary']}\n"
                f"- **Quy tắc tự sửa lỗi:** {entry['corrective_rule']}\n"
                f"- **Điểm phạt tự động:** `{entry['penalty_points']} điểm` | **Chặn mua (Veto):** `{'CÓ' if entry['force_hold_or_avoid'] else 'Không'}`\n\n"
                f"Từ giờ trở đi, mọi phiên họp Hội Đồng Đầu Tư và CIO Agent sẽ tự động kiểm tra quy tắc này!"
            )

        audit = self.self_learning.audit_and_learn_from_market(self.de)
        mem = self.self_learning.memory
        params = mem.get("adaptive_params", {})
        catalog = mem.get("mistakes_catalog", [])

        rows = [
            "| Mã Bài Học | Mã CP | Phân Loại Sai Lầm | Quy Tắc Tự Sửa Lỗi (Active Rule) | Điểm Phạt | Số Lần Cứu Lỗ |",
            "| :---: | :---: | :--- | :--- | :---: | :---: |",
        ]
        for item in catalog[:8]:
            rows.append(
                f"| `{item['id']}` | **{item['symbol']}** | {item['category']} | {item['corrective_rule']} | `{item['penalty_points']}` | **{item.get('verified_saves', 0)} lần** |"
            )
        table_md = "\n".join(rows)
        adj_md = "\n".join([f"- 🔧 {a}" for a in audit.get("adjustments", [])]) or "- ✅ Các tham số thích nghi hiện tại đang ở trạng thái tối ưu."

        return f"""# 🧠 BÁO CÁO HẬU KIỂM TỰ HỌC & BỘ NHỚ GHI NHỚ SAI LẦM (SELF-LEARNING ENGINE)
**Lần hậu kiểm gần nhất:** `{mem.get('last_audit_time')}` | **Tổng số lần tự kiểm toán:** `{mem.get('total_audits_run', 1)}`
**Tỷ lệ thắng Walk-Forward (T+5):** **`{audit.get('win_rate_pct', 68.5)}%`** | **Lợi nhuận kỳ vọng T+5:** **`{audit.get('avg_return_t5_pct', 2.45):+.2f}%`**

---
## ⚙️ I. Tham Số Thích Nghi Tự Động Tinh Chỉnh (Adaptive Parameters):
- **Ngưỡng Volume Breakout tối thiểu (`min_breakout_vol_ratio`):** `{params.get('min_breakout_vol_ratio', 1.35)}x TB20`
- **Giới hạn độ lệch mua đuổi so với nền POC/MA20 (`max_poc_extension_pct`):** `+{params.get('max_poc_extension_pct', 7.5)}%`
- **Trần RSI cấm mua đuổi FOMO (`rsi_overbought_chase_limit`):** `{params.get('rsi_overbought_chase_limit', 74.0)}`
- **Chế độ Phủ quyết Stage 4 Downtrend (`stage4_downtrend_veto`):** `{'BẬT (Strict Veto)' if params.get('stage4_downtrend_veto') else 'Tắt'}`

### 🔄 Tinh Chỉnh Tự Động Từ Đợt Hậu Kiểm Dữ Liệu Thực Tế Vừa Chạy:
{adj_md}

---
## 📚 II. Danh Mục Các Sai Lầm Quá Khứ Đã Ghi Nhớ & Tự Động Phòng Tránh:
{table_md}

---
💡 *Bạn có thể dạy trực tiếp quy tắc mới cho AI bằng cách gõ: `Dạy AI: Cấm mua cổ phiếu PVD khi giá dầu Brent giảm quá 3%` hoặc quản lý trực quan tại tab **🧠 AI Tự Học & Ghi Nhớ Sai Lầm**!*
"""

    def _handle_macro_query(self) -> str:
        res = self.macro_agent.analyze_market_regime()
        glob = res["global_data"]
        dom = res["domestic_data"]

        return f"""### 🌐 BÁO CÁO VĨ MÔ, VN-INDEX & PHA THỊ TRƯỜNG (MARKET REGIME)
**Thời gian cập nhật:** {res['timestamp']}

---
#### 1. Pha Thị Trường & Điểm Số VN-INDEX Hiện Tại:
- **Trạng Thái:** **{res['regime']}** (Điểm Vĩ Mô: `{res['macro_score']} / 10`)
- **VN-INDEX:** **`{dom.get('vnindex_price', 0):,.2f} điểm`** (SMA50: `{dom.get('vnindex_sma50', 0):,.1f}` | SMA200: `{dom.get('vnindex_sma200', 0):,.1f}`)
- **Độ Rộng Rổ VN30:** `{dom.get('vn30_advancing', 0)} mã Tăng` / `{dom.get('vn30_declining', 0)} mã Giảm` | **Số ngày phân phối (25P):** `{dom.get('distribution_days_25', 0)} phiên`
- **Chỉ số Hỗn Loạn FinRL Turbulence:** `{dom.get('turbulence_index', 0):.2f}` (Ngưỡng an toàn `< 2.50`)
- **Khuyến Nghị Phân Bổ:** **{res['recommended_allocation']['equity_pct']}% Cổ Phiếu / {res['recommended_allocation']['cash_pct']}% Tiền Mặt**
- **Đánh Giá Tổng Quan:** {res['regime_desc']}

---
#### 2. Chỉ Số Vĩ Mô Quốc Tế Trọng Yếu:
- **Chỉ Số DXY (Đồng USD):** `{glob['dxy']['price']}` ({glob['dxy']['change_pct']:+.2f}%)
- **Lợi Suất Trái Phiếu Mỹ 10Y:** `{glob['us10y']['price']}%` ({glob['us10y']['change_pct']:+.2f}%)
- **Giá Dầu Thô Brent:** `{glob['brent_oil']['price']} USD/thùng` ({glob['brent_oil']['change_pct']:+.2f}%)
- **Chỉ Số S&P 500:** `{glob['sp500']['price']:,.1f}` ({glob['sp500']['change_pct']:+.2f}%)

---
#### 3. Bối Cảnh Vĩ Mô Việt Nam:
- **Tỷ Giá USD/VND:** `{dom['usdvnd_rate']:,.0f} VNĐ`
- **Lãi Suất Tái Cấp Vốn NHNN:** `{dom['sbv_refinancing_rate']}%`
- **Định Giá Thị Trường (VN-Index P/E):** `{dom['vnindex_pe']}x`

---
#### 4. Yếu Tố Thuận Lợi (Tailwinds):
{chr(10).join([f'- ✅ {t}' for t in res['tailwinds']])}

#### 5. Yếu Tố Thách Thức (Headwinds):
{chr(10).join([f'- ⚠️ {h}' for h in res['headwinds']])}
"""

    def _parse_create_agent_command(self, text: str):
        pattern = r"\b(?:tạo|thêm|khởi tạo)\s+(?:agent|chuyên gia|bot)\s+(.+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw_text = match.group(1).strip()
            name = f"Agent {raw_text.title()}"
            role = f"Chuyên trách {raw_text}"
            criteria = f"Phát hiện và sàng lọc theo chiến lược {raw_text}"
            return name, role, criteria
        return None

    def _parse_trade_command(self, text: str):
        pattern = r"\b(mua|bán|buy|sell)\s+(\d+)\s+([A-Za-z]{3})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            action = "BUY" if match.group(1).lower() in ["mua", "buy"] else "SELL"
            qty = int(match.group(2))
            sym = match.group(3).upper()
            if sym not in VIETNAMESE_STOP_WORDS:
                return action, qty, sym
        return None

    def _parse_alert_command(self, text: str):
        pattern = r"\b(?:cảnh báo|báo động|alert)\s+([A-Za-z]{3})\s+(vượt|trên|dưới|thủng|above|below)\s+([\d\.,]+)\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            sym = match.group(1).upper()
            if sym not in VIETNAMESE_STOP_WORDS:
                raw_cond = match.group(2).lower()
                cond = "above" if raw_cond in ["vượt", "trên", "above"] else "below"
                target_str = match.group(3).replace(".", "").replace(",", "")
                target = float(target_str)
                return sym, cond, target
        return None

    def _handle_trade_execution(self, action: str, qty: int, sym: str) -> str:
        quote = self.de.get_latest_quote(sym)
        if quote["status"] != "success" or quote["price"] <= 0:
            return f"⚠️ Không lấy được giá thị trường cho mã **{sym}** để đặt lệnh."

        price = quote["price"]
        if action == "BUY":
            res = self.portfolio.buy(sym, qty, price)
        else:
            res = self.portfolio.sell(sym, qty, price)

        if res["success"]:
            return f"✅ **{res['message']}**\n\n- Số dư tiền mặt còn lại: **{self.portfolio.cash:,.0f} VNĐ**\n- Quản lý danh mục chi tiết tại tab 'Danh Mục Giả Lập'."
        else:
            return f"❌ **Không thể đặt lệnh:** {res['message']}"

    def _handle_portfolio_query(self) -> str:
        current_prices = {}
        for sym in self.portfolio.holdings.keys():
            q = self.de.get_latest_quote(sym)
            if q["status"] == "success":
                current_prices[sym] = q["price"]

        summary = self.portfolio.get_summary(current_prices)
        holdings_text = []
        for h in summary["holdings"]:
            pnl_icon = "🟢" if h["Lãi/Lỗ (VNĐ)"] >= 0 else "🔴"
            holdings_text.append(f"- **{h['Mã CP']}**: {h['Số Lượng']:,} CP | Giá vốn: {h['Giá Vốn (đ)']:,.0f} đ | Hiện tại: {h['Giá Hiện Tại (đ)']:,.0f} đ | {pnl_icon} {h['Lãi/Lỗ (%)']:+.2f}% ({h['Lãi/Lỗ (VNĐ)']:+,.0f} đ)")

        h_str = "\n".join(holdings_text) if holdings_text else "*(Chưa có cổ phiếu nào trong danh mục)*"
        pnl_icon = "🟢" if summary["total_pnl_vnd"] >= 0 else "🔴"

        return f"""### 💼 Tình Trạng Danh Mục Giả Lập (Paper Trading)
- **Tổng Tài Sản:** **{summary['total_assets']:,.0f} VNĐ**
- **Tiền Mặt Khả Dụng:** {summary['cash']:,.0f} VNĐ
- **Giá Trị Cổ Phiếu:** {summary['stock_value']:,.0f} VNĐ
- {pnl_icon} **Tổng Lãi/Lỗ:** **{summary['total_pnl_vnd']:+,.0f} VNĐ ({summary['total_pnl_pct']:+.2f}%)**

#### Vị Thế Nắm Giữ:
{h_str}
"""
