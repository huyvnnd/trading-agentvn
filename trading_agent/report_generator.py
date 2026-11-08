"""
Institutional Report Generator for Vietnam Stock Market.
Tạo báo cáo thẩm định đầu tư chuyên nghiệp (Institutional Investment Memo / Research Report)
đầy đủ các phần: Vĩ mô, Thẩm định BCTC, Cấu trúc đa khung, Tranh luận hội đồng & Quyết định CIO.
"""

import os
from datetime import datetime

class ReportGenerator:
    @staticmethod
    def generate_html_report(decision_data: dict) -> str:
        symbol = decision_data.get("symbol", "VN_STOCK")
        meeting = decision_data.get("meeting", {})
        macro = meeting.get("macro_report", {})
        fund = meeting.get("fund_report", {})
        tech = meeting.get("tech_report", {})
        risk = meeting.get("risk_report", {})
        dialogue = meeting.get("dialogue", [])
        trade_p = decision_data.get("trade_plan", {})

        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<title>Báo Cáo Thẩm Định Đầu Tư - {symbol}</title>
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2c3e50; padding: 30px; background: #fdfdfd; }}
    .header {{ border-bottom: 3px solid #1a237e; padding-bottom: 15px; margin-bottom: 25px; }}
    .title {{ font-size: 26px; color: #1a237e; font-weight: bold; margin: 0; }}
    .subtitle {{ color: #7f8c8d; font-size: 14px; margin-top: 5px; }}
    .badge {{ display: inline-block; padding: 6px 14px; font-weight: bold; border-radius: 4px; color: white; background: {decision_data.get('decision_color', '#1e88e5')}; }}
    .section {{ background: white; border: 1px solid #e0e0e0; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.03); }}
    .section-title {{ font-size: 18px; color: #0d47a1; border-left: 4px solid #1e88e5; padding-left: 10px; margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-top: 10px; }}
    .card {{ background: #f8f9fa; padding: 12px; border-radius: 6px; border: 1px solid #eee; }}
    .card-label {{ font-size: 12px; color: #7f8c8d; text-transform: uppercase; }}
    .card-value {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
    .dialogue-item {{ border-left: 3px solid #b0bec5; padding: 10px 15px; margin-bottom: 12px; background: #fcfcfc; border-radius: 0 6px 6px 0; }}
    .speaker {{ font-weight: bold; color: #37474f; }}
    .role {{ font-size: 12px; color: #78909c; font-style: italic; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
    th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
    th {{ background: #f1f8ff; color: #0d47a1; }}
</style>
</head>
<body>
<div class="header">
    <div class="title">🏛️ BÁO CÁO THẨM ĐỊNH ĐẦU TƯ TỔ CHỨC: {symbol}</div>
    <div class="subtitle">Hội Đồng Đầu Tư Chuyên Nghiệp • Ngày thẩm định: {meeting.get('meeting_time', datetime.now().strftime('%Y-%m-%d'))}</div>
</div>

<div class="section">
    <div class="section-title">I. NGHỊ QUYẾT GIÁM ĐỐC ĐẦU TƯ (CIO)</div>
    <p><span class="badge">{decision_data.get('final_decision')}</span> &nbsp; <strong>Điểm Thuyết Phục:</strong> {decision_data.get('conviction_score')}/10 &nbsp;|&nbsp; <strong>Hạn mức:</strong> {decision_data.get('allocation_pct')}% NAV</p>
    <p><strong>Kế hoạch hành động:</strong> {decision_data.get('action_plan')}</p>
    <ul>
        {"".join([f"<li>{t}</li>" for t in decision_data.get('tranches', [])])}
    </ul>
</div>

<div class="section">
    <div class="section-title">II. THÔNG SỐ GIAO DỊCH TỐI ƯU (R:R ≥ 2.5 : 1)</div>
    <div class="grid">
        <div class="card">
            <div class="card-label">Vùng Mua An Toàn</div>
            <div class="card-value">{trade_p.get('optimal_entry_zone', 'N/A')}</div>
        </div>
        <div class="card">
            <div class="card-label">Dừng Lỗ Cấu Trúc</div>
            <div class="card-value" style="color: #d32f2f;">{trade_p.get('structural_stop_loss', 0):,.0f} đ ({trade_p.get('stop_loss_pct', 0):+.1f}%)</div>
        </div>
        <div class="card">
            <div class="card-label">Mục Tiêu TP1</div>
            <div class="card-value" style="color: #2e7d32;">{trade_p.get('take_profit_target_1', 0):,.0f} đ ({trade_p.get('target_1_pct', 0):+.1f}%)</div>
        </div>
        <div class="card">
            <div class="card-label">Tỷ Lệ Lợi Nhuận/Rủi Ro</div>
            <div class="card-value">{trade_p.get('risk_reward_ratio', 0):.2f} : 1</div>
        </div>
    </div>
</div>

<div class="section">
    <div class="section-title">III. BIÊN BẢN HỌP TRANH LUẬN & PHẢN BIỆN (DEBATE MINUTES)</div>
    {"".join([f'''
    <div class="dialogue-item">
        <div class="speaker">{d['speaker']} <span class="role">({d['role']})</span></div>
        <div class="statement">{d['statement']}</div>
    </div>
    ''' for d in dialogue])}
</div>

<div class="section">
    <div class="section-title">IV. BỐI CẢNH VĨ MÔ & NỘI TẠI DOANH NGHIỆP</div>
    <p><strong>Pha thị trường:</strong> {macro.get('regime')} ({macro.get('regime_desc')})</p>
    <p><strong>Sức khỏe tài chính:</strong> {fund.get('health_status')} | P/E: {fund.get('pe', 'N/A')} | P/B: {fund.get('pb', 'N/A')} | ROE: {fund.get('roe', 'N/A')}%</p>
    <p><strong>Thanh khoản bình quân 20 phiên:</strong> {fund.get('avg_liquidity_vnd', 0)/1e9:.1f} tỷ VNĐ/phiên ({fund.get('avg_vol_20', 0):,.0f} CP/phiên)</p>
</div>
</body>
</html>"""
        return html
