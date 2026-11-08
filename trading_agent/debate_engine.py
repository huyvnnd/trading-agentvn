"""
Institutional Investment Committee & Adversarial Debate Engine (TauricResearch/TradingAgents + virattt/ai-hedge-fund).
Mô phỏng hoàn chỉnh quy trình Họp Hội Đồng Thẩm Định Quỹ Đầu Tư Đa Tầng:
1. Chạy song song (Multi-threaded) 4 Phòng ban Phân tích: Macro, Fundamental/DuPont/Valuation, MTF Technical/SEPA/VCP, Sentiment/Foreign Flow.
2. Chấm điểm CANSLIM (0-100) & Triệu tập Hội Đồng 9 Đại Kiện Tướng Đầu Tư (Buffett, Munger, Graham, Lynch, Druckenmiller, Damodaran, O'Neil/Minervini, Burry, Ackman).
3. Tranh biện đối kháng trực diện giữa Trưởng Nhóm Nghiên Cứu Phe Bò (Bull Researcher) và Phe Gấu (Bear Researcher).
4. Kiểm định sức chịu đựng 3 Tư thế Rủi ro (Aggressive, Neutral, Conservative CRO) theo chuẩn FinRL & T+2.5.
"""

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from trading_agent.macro_agent import MacroAgent
from trading_agent.fundamental_agent import FundamentalAgent
from trading_agent.technical_structure_agent import TechnicalStructureAgent
from trading_agent.sentiment_agent import SentimentAgent
from trading_agent.risk_agent import RiskAgent
from trading_agent.quant_engine import QuantEngine


class DebateEngine:
    def __init__(self, data_engine=None):
        self.de = data_engine
        self.macro_agent = MacroAgent(data_engine=self.de)
        self.fund_agent = FundamentalAgent(data_engine=self.de)
        self.tech_agent = TechnicalStructureAgent(data_engine=self.de)
        self.sentiment_agent = SentimentAgent(data_engine=self.de)
        self.risk_agent = RiskAgent(data_engine=self.de)

    def conduct_committee_meeting(self, symbol: str) -> dict:
        symbol = symbol.strip().upper()

        # 1. Chạy song song các phòng ban phân tích để đạt tốc độ phản hồi < 0.8s
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_macro = ex.submit(self.macro_agent.analyze_market_regime)
            f_fund = ex.submit(self.fund_agent.audit_financial_health, symbol)
            f_tech = ex.submit(self.tech_agent.analyze_multi_timeframe_structure, symbol)
            f_sent = ex.submit(self.sentiment_agent.analyze_sentiment_and_flow, symbol)

            macro_report = f_macro.result()
            fund_report = f_fund.result()
            tech_report = f_tech.result()
            sentiment_report = f_sent.result()

        risk_report = self.risk_agent.assess_investment_risk(symbol, fund_report, tech_report, macro_report)

        # 2. Tính điểm CANSLIM (0-100) & Hội đồng 9 Đại Kiện Tướng Đầu Tư
        df_daily = self.de.get_history(symbol, days=90) if self.de else None
        sepa_vcp = tech_report.get("sepa_vcp", {})
        rs_info = tech_report.get("rs_info", {})
        dupont_val = fund_report.get("dupont_valuation", {})

        canslim_report = QuantEngine.evaluate_canslim_score(
            fund_info=fund_report,
            sepa_info=sepa_vcp,
            rs_info=rs_info,
            df_daily=df_daily
        )

        personas_council = QuantEngine.evaluate_legendary_personas(
            symbol=symbol,
            ov=fund_report.get("raw_overview", fund_report),
            dupont_val=dupont_val,
            sepa_vcp=sepa_vcp,
            canslim=canslim_report,
            rs_info=rs_info,
            tech_report=tech_report
        )

        bull_personas = [p["persona"] for p in personas_council if "BULLISH" in p["signal"]]
        bear_personas = [p["persona"] for p in personas_council if "BEARISH" in p["signal"]]

        # 3. Xây dựng Biên bản Họp Tranh Luận 7 Lượt (Debate Dialogue)
        dialogue = []

        # --- LƯỢT 1: VĨ MÔ, ĐỘ RỘNG VN-INDEX & CHỈ SỐ HỖN LOẠN FINRL ---
        dom = macro_report.get("domestic_data", {})
        dialogue.append({
            "speaker": "🌐 Chuyên Gia Vĩ Mô & Pha Thị Trường (Macro & FinRL Turbulence Agent)",
            "role": "Bối Cảnh Vĩ Mô • Market Direction (M) • Turbulence Index",
            "statement": (
                f"Thị trường chung đang ở trạng thái **{macro_report['regime']}** (Điểm vĩ mô: `{macro_report['macro_score']}/10`). "
                f"VN-INDEX tại `{dom.get('vnindex_price', 0):,.1f}` điểm (MA50: `{dom.get('vnindex_sma50', 0):,.1f}`, MA200: `{dom.get('vnindex_sma200', 0):,.1f}` | "
                f"Số ngày phân phối: `{dom.get('distribution_days_25', 0)}/25 phiên` | Chỉ số hỗn loạn FinRL: `{dom.get('turbulence_index', 0):.2f}`). "
                f"Khuyến nghị phân bổ tổng danh mục: **{macro_report['recommended_allocation']['equity_pct']}% Cổ phiếu / "
                f"{macro_report['recommended_allocation']['cash_pct']}% Tiền mặt**."
            )
        })

        # --- LƯỢT 2: THẨM ĐỊNH DOANH NGHIỆP, DUPONT 3 BƯỚC & ĐỊNH GIÁ DAMODARAN/GRAHAM ---
        iv = fund_report.get("intrinsic_value", 0)
        mos = fund_report.get("margin_of_safety_pct", 0)
        dialogue.append({
            "speaker": "🏢 Chuyên Gia Kiểm Toán BCTC & Định Giá (FinRobot & Damodaran Agent)",
            "role": "Phân Tích DuPont 3 Bước • Định Giá Nội Tại • Lọc Rác",
            "statement": (
                f"Xếp hạng nội tại: **{fund_report['health_status']}** (Điểm cơ bản: `{fund_report['fundamental_score']}/10` | Ngành: `{fund_report.get('industry', 'N/A')}`). "
                f"{dupont_val.get('dupont_summary', '')} "
                f"Tăng trưởng LNST YoY: `{fund_report.get('profit_growth_yoy') if fund_report.get('profit_growth_yoy') is not None else 'N/A'}%`. "
                f"Giá trị hợp lý đa mô hình (Damodaran/Graham/Lynch): **`{iv:,.0f} VNĐ/CP`** "
                f"(Biên an toàn MoS: **`{mos:+.1f}%`** — {dupont_val.get('valuation_status', '')})."
            )
        })

        # --- LƯỢT 3: CẤU TRÚC ĐA KHUNG, MINERVINI SEPA 8-POINT, VCP & CANSLIM ---
        tech_trade = tech_report.get("trade_plan", {})
        vp = tech_report.get("volume_profile", {})
        dialogue.append({
            "speaker": "📐 Chuyên Gia Cấu Trúc Đa Khung & SEPA/CANSLIM (Technical Structure Agent)",
            "role": "Weinstein Stage 1-4 • Minervini SEPA/VCP • Volume Profile POC",
            "statement": (
                f"Phân loại chu kỳ: **{tech_report.get('stage_name', 'N/A')}** | "
                f"**SEPA Trend Template:** `{sepa_vcp.get('sepa_score', 0)}/8 tiêu chí` | "
                f"**RS Rating:** `{rs_info.get('rs_rating', 50)}/99` (So với VN-Index: `{rs_info.get('outperformance_pct', 0):+.1f}%`) | "
                f"**Điểm CANSLIM:** `{canslim_report.get('canslim_score', 0)}/100 (Hạng {canslim_report.get('canslim_grade', 'C')})`. "
                f"Volume Profile: Giá vốn tổ chức **POC = `{vp.get('poc', 0):,.0f} đ`** (VAL: `{vp.get('val', 0):,.0f}` — VAH: `{vp.get('vah', 0):,.0f}`). "
                f"Vùng mua tối ưu: `{tech_trade.get('optimal_entry_zone', 'N/A')}` | Cắt lỗ cấu trúc: `{tech_trade.get('structural_stop_loss', 0):,.0f} đ` ({tech_trade.get('stop_loss_pct', 0):+.1f}%)."
            )
        })

        # --- LƯỢT 4: DÒNG TIỀN KHỐI NGOẠI & TÍCH LŨY/PHÂN PHỐI ---
        dialogue.append({
            "speaker": "🌊 Chuyên Gia Dòng Tiền Khối Ngoại & Order Flow (Sentiment Agent)",
            "role": "Giao Dịch Khối Ngoại Realtime • Up/Down Volume Ratio",
            "statement": (
                f"Trạng thái dòng tiền: **{sentiment_report['flow_status']}**. "
                f"{' '.join(sentiment_report['sentiment_notes'][:2])} "
                f"{sentiment_report['media_trap_warning'] or 'Không phát hiện dấu hiệu FOMO kéo xả bất thường.'}"
            )
        })

        # --- LƯỢT 5: TRƯỞNG NHÓM NGHIÊN CỨU PHE BÒ (BULL RESEARCHER - TAURIC TRADINGAGENTS) ---
        bull_args = []
        if fund_report.get("positives"):
            bull_args.extend(fund_report["positives"][:2])
        if not tech_report.get("is_downtrend"):
            bull_args.append(
                f"Cấu trúc kỹ thuật nằm ở {tech_report.get('stage_name')}, giữ trên vùng giá vốn POC ({vp.get('poc', 0):,.0f} đ) với tỷ lệ R:R = {tech_trade.get('risk_reward_ratio', 2.5):.2f}:1."
            )
        if bull_personas:
            bull_args.append(f"Được ủng hộ bởi các huyền thoại đầu tư: **{', '.join(bull_personas)}**.")
        if not bull_args:
            bull_args.append("Chưa có luận điểm tăng giá đủ mạnh trong ngắn hạn ngoài khả năng bật hồi kỹ thuật ngắn khi quá bán.")

        dialogue.append({
            "speaker": "🐂 Trưởng Nhóm Nghiên Cứu Phe Bò (Bull Researcher - TauricResearch)",
            "role": "Bảo Vệ Luận Điểm Đầu Tư Tăng Trưởng & Giá Trị",
            "statement": " ".join(bull_args)
        })

        # --- LƯỢT 6: TRƯỞNG NHÓM PHẢN BIỆN PHE GẤU (BEAR RESEARCHER - TAURIC TRADINGAGENTS) ---
        bear_args = []
        if risk_report.get("critical_warnings"):
            bear_args.extend(risk_report["critical_warnings"])
        if fund_report.get("red_flags"):
            bear_args.extend(fund_report["red_flags"][:2])
        if risk_report.get("bearish_arguments"):
            bear_args.extend(risk_report["bearish_arguments"][:2])
        if bear_personas:
            bear_args.append(f"Các đại kiện tướng phản đối/cảnh báo: **{', '.join(bear_personas)}**.")
        if not bear_args:
            bear_args.append("Rủi ro chính nằm ở biến động bất ngờ của thị trường chung và độ trễ thanh toán T+2.5 tại Việt Nam.")

        dialogue.append({
            "speaker": "🐻 Trưởng Nhóm Phản Biện Phe Gấu (Bear Researcher - Devil's Advocate)",
            "role": "Phản Biện Nghịch Đảo (Munger Inversion) & Vạch Trần Rủi Ro",
            "statement": " ".join(bear_args)
        })

        # --- LƯỢT 7: HỘI ĐỒNG QUẢN TRỊ RỦI RO 3 TƯ THẾ & GIÁM ĐỐC CRO ---
        postures = risk_report.get("posture_debates", {})
        finrl_m = tech_report.get("finrl_metrics", {})
        dialogue.append({
            "speaker": "🛡️ Ủy Ban Quản Trị Rủi Ro 3 Tư Thế & CRO (FinRL & TradingAgents Risk Team)",
            "role": "Kiểm Định Sharpe/Sortino/MaxDD • Khối Lượng Kelly Lô 100 • Quyền Phủ Quyết",
            "statement": (
                f"Chỉ số định lượng FinRL: **Sharpe = `{finrl_m.get('sharpe_ratio', 0):.2f}`** | "
                f"**Sortino = `{finrl_m.get('sortino_ratio', 0):.2f}`** | "
                f"**Max Drawdown = `{finrl_m.get('max_drawdown_pct', 0):.1f}%`** | "
                f"**Half-Kelly = `{finrl_m.get('half_kelly_pct', 0):.1f}% NAV`**. "
                f"Kết luận rủi ro: **{risk_report['risk_level']}** (Hạn mức tối đa: `{risk_report['max_position_size']}`).\n"
                f"- {postures.get('aggressive', '')}\n"
                f"- {postures.get('neutral', '')}\n"
                f"- {postures.get('conservative', '')}"
            )
        })

        return {
            "symbol": symbol,
            "meeting_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "macro_report": macro_report,
            "fund_report": fund_report,
            "tech_report": tech_report,
            "sentiment_report": sentiment_report,
            "risk_report": risk_report,
            "canslim_report": canslim_report,
            "personas_council": personas_council,
            "dialogue": dialogue
        }
