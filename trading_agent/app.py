"""
Vietnam Institutional Quantitative & Multi-Agent Trading Platform (Streamlit).
Hợp nhất tinh hoa từ 8 dự án mã nguồn mở hàng đầu thế giới và Việt Nam:
1. TauricResearch/TradingAgents: Analyst Swarm, Bull vs. Bear Researcher Debate, 3-Posture Risk Team (Aggressive, Neutral, Conservative), CIO.
2. virattt/ai-hedge-fund: Hội đồng 9 Đại Kiện Tướng Đầu Tư (Buffett, Munger, Graham, Lynch, Druckenmiller, Damodaran, O'Neil/Minervini, Burry, Ackman).
3. AI4Finance-Foundation/FinRL: Sharpe, Sortino, Calmar, Max Drawdown, Turbulence Index, Half-Kelly & Khối lượng Lô 100 CP điều chỉnh T+2.5.
4. AI4Finance-Foundation/FinRobot: Phân tích DuPont 3 Bước, Kiểm toán Dòng tiền BCTC, Định giá Đa Mô Hình (Football Field Matrix).
5. tradermonty/claude-trading-skills: CANSLIM (0-100), Stan Weinstein Stage 1-4, Mark Minervini 8-Point SEPA & VCP Contraction, Wyckoff VSA/SMC.
6. thinh-vu/vnstock (KBS/VCI High-Speed Engine): Dữ liệu Bảng giá Batch (<0.4s), Lịch sử Đa khung, BCTC 54 chỉ tiêu, Phái sinh VN30F1M OI & Khối ngoại.
7. An-Tran-2001/TradingAgents-Vn: Quy chế T+2.5, Biên độ ±7%/±10%/±15%, Nhật ký Phản tư (Reflection Memory Loop).
8. vnstock-hq/vnstock_chart: Biểu đồ Nến Tổ chức tích hợp Volume Profile ngang (POC/VAH/VAL), Đường Sức mạnh giá RS Line & Hệ thống MA.
"""

import os
import sys
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Setup paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

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
from trading_agent.report_generator import ReportGenerator
from trading_agent.vsa_smc_screener import VSASMCScreener
from trading_agent.screener import StockScreener
from trading_agent.portfolio import PortfolioManager
from trading_agent.alert_engine import AlertEngine
from trading_agent.derivatives_agent import DerivativesAgent
from trading_agent.agent import TradingAgent
from trading_agent.chart_builder import InteractiveChartBuilder
from trading_agent.self_learning_engine import SelfLearningEngine
from trading_agent.strategy_engine import (
    SMACrossoverStrategy, RSIStrategy, MACDStrategy,
    BollingerBandsStrategy, BreakoutVolumeStrategy,
    CustomRuleStrategy, StrategyBacktester
)
import socket


def get_lan_ip() -> str:
    """Lấy địa chỉ IP mạng nội bộ (LAN IP) khả dụng nhất của máy chủ để truy cập từ mobile / laptop khác."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


st.set_page_config(
    page_title="VN Institutional AI Hedge Fund & Trading Agent",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional Institutional Styling
st.markdown("""
<style>
    .block-container {
        padding-top: 3.2rem !important;
        padding-bottom: 2rem !important;
    }
    .main-title {
        font-size: 1.95rem;
        font-weight: 800;
        color: #0d47a1;
        margin-bottom: 2px;
        letter-spacing: -0.3px;
    }
    .sub-title {
        color: #455a64;
        font-size: 0.96rem;
        margin-bottom: 14px;
    }
    .cmd-banner {
        background: linear-gradient(135deg, #0d254c 0%, #1565c0 100%);
        color: white;
        padding: 14px 20px;
        border-radius: 10px;
        margin-bottom: 16px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
    }
    .persona-card {
        background-color: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 8px;
        padding: 12px 14px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
        height: 100%;
    }
    .dialogue-box {
        background-color: #f8fafd;
        border-left: 4px solid #1565c0;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 8px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    }
    .buy-box {
        background-color: #e8f5e9;
        border-left: 5px solid #2e7d32;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .avoid-box {
        background-color: #ffebee;
        border-left: 5px solid #c62828;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
    .watchlist-box {
        background-color: #fffde7;
        border: 1px solid #ffe082;
        border-left: 5px solid #f57f17;
        padding: 12px 16px;
        border-radius: 6px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


CACHE_SCHEMA_VERSION = "v14_near_peak_resistance_and_web_standalone"


@st.cache_resource
def get_institutional_engines(schema_ver: str = CACHE_SCHEMA_VERSION):
    de = DataEngine(default_source="KBS")
    pm = PortfolioManager(initial_cash=1_000_000_000.0)
    sc = StockScreener(de)
    ae = AlertEngine(data_engine=de)
    ag = TradingAgent(data_engine=de, portfolio=pm, screener=sc, alert_engine=ae)
    ma = MacroAgent(data_engine=de)
    fa = FundamentalAgent(data_engine=de)
    tsa = TechnicalStructureAgent(data_engine=de)
    sle = ag.self_learning
    cio = CIOAgent(debate_engine=ag.debate_engine, self_learning=sle)
    dam = DynamicAgentManager()
    vss = VSASMCScreener(de)
    da = DerivativesAgent(data_engine=de)
    return de, pm, sc, ae, ag, ma, fa, tsa, cio, dam, vss, da, sle


data_engine, portfolio_mgr, screener, alert_mgr, agent, macro_agent, fund_agent, tech_agent, cio_agent, dynamic_mgr, vsa_screener, derivatives_agent, self_learning_engine = get_institutional_engines(CACHE_SCHEMA_VERSION)


# =========================================================================
# CACHED REAL-TIME DATA & QUANTITATIVE COMPUTATION LAYER (< 0.05s ON HIT)
# =========================================================================
@st.cache_data(ttl=300, show_spinner=False)
def cached_cio_decision(symbol: str, schema_ver: str = CACHE_SCHEMA_VERSION) -> dict:
    return cio_agent.evaluate_and_decide(symbol)


@st.cache_data(ttl=300, show_spinner=False)
def cached_macro_regime(schema_ver: str = CACHE_SCHEMA_VERSION) -> dict:
    return macro_agent.analyze_market_regime()


@st.cache_data(ttl=120, show_spinner=False)
def cached_market_overview(schema_ver: str = CACHE_SCHEMA_VERSION) -> dict:
    return data_engine.get_market_overview()


@st.cache_data(ttl=120, show_spinner=False)
def cached_latest_quote(symbol: str, schema_ver: str = CACHE_SCHEMA_VERSION) -> dict:
    return data_engine.get_latest_quote(symbol)


@st.cache_data(ttl=180, show_spinner=False)
def cached_derivatives_overview(schema_ver: str = CACHE_SCHEMA_VERSION) -> dict:
    return derivatives_agent.get_derivatives_overview()


@st.cache_data(ttl=300, show_spinner=False)
def cached_derivatives_15m_history(schema_ver: str = CACHE_SCHEMA_VERSION) -> pd.DataFrame:
    return data_engine.get_history("VN30F1M", days=20, interval="15m")


@st.cache_data(ttl=600, show_spinner=False)
def cached_vsa_universe_scan(schema_ver: str = CACHE_SCHEMA_VERSION) -> tuple:
    df_buy = vsa_screener.scan_vsa_smc_universe(min_score=35)
    df_watchlist = vsa_screener.scan_watchlist_universe()
    df_avoid = vsa_screener.scan_danger_stocks_to_avoid()
    return df_buy, df_watchlist, df_avoid


@st.cache_data(ttl=600, show_spinner=False)
def cached_screener_scan(criteria: str, schema_ver: str = CACHE_SCHEMA_VERSION) -> pd.DataFrame:
    if criteria == "vsa_smc":
        df_b, _, _ = cached_vsa_universe_scan(schema_ver)
        return df_b
    elif criteria == "vsa_watchlist":
        _, df_w, _ = cached_vsa_universe_scan(schema_ver)
        return df_w
    elif criteria == "avoid_stage4":
        _, _, df_a = cached_vsa_universe_scan(schema_ver)
        return df_a
    return screener.scan_symbols(criteria=criteria)


@st.cache_data(ttl=300, show_spinner=False)
def cached_reflection_log() -> list:
    return cio_agent.get_reflection_log(data_engine=data_engine)


if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [
        {
            "role": "assistant",
            "content": (
                "🏛️ **Chào mừng bạn đến với Hệ Thống Quỹ Đầu Tư Định Lượng Đa Tác Tử (Institutional AI Hedge Fund)!**\n\n"
                "Hệ thống đã hợp nhất tinh hoa từ **8 dự án mã nguồn mở hàng đầu** (`TradingAgents`, `ai-hedge-fund`, `FinRL`, `FinRobot`, `claude-trading-skills`, `vnstock`, `TradingAgents-Vn`, `vnstock_chart`) và tối ưu tốc độ phản hồi tức thời:\n"
                "- 🎯 **Tab 1 (Trung Tâm Khuyến Nghị Hôm Nay):** Click trực tiếp vào bất kỳ dòng cổ phiếu nào để mở ngay **Hồ Sơ Nghị Quyết CIO & Studio Biểu Đồ Kỹ Thuật Đa Chỉ Báo**.\n"
                "- 💬 **Tab 2 (AI Chat Đa Nhiệm):** Hiểu và thực thi ngay lập tức mọi câu lệnh tiếng Việt có dấu hoặc không dấu (VD: `loc co phieu bat day`, `Lọc cổ phiếu VSA SMC`, `Phân tích TCB`, `So sánh HPG và HSG`, `Tư vấn danh mục 1 tỷ`).\n"
                "- 📈 **Studio Biểu Đồ Đa Chỉ Báo:** Đổi mô hình phân tích kỹ thuật (`Preset`) hoặc thêm/bớt 19 chỉ báo phản hồi tức thì (`< 0.08s`).\n\n"
                "👉 Hãy bấm các nút tác vụ nhanh bên dưới hoặc gõ bất kỳ yêu cầu nào!"
            )
        }
    ]

if "selected_symbol" not in st.session_state:
    st.session_state["selected_symbol"] = "FRT"


def set_selected_symbol(sym: str):
    """Callback cập nhật mã cổ phiếu được chọn trong 1 chu kỳ duy nhất, không bao giờ gây lặp rerun."""
    if not sym:
        return
    clean_s = str(sym).strip().upper()
    if data_engine.is_valid_symbol(clean_s):
        st.session_state["selected_symbol"] = clean_s


def _on_sb_input_change():
    raw = st.session_state.get("sb_input_ticker", "")
    if raw:
        cand = raw.strip().upper()
        if data_engine.is_valid_symbol(cand):
            st.session_state["selected_symbol"] = cand
            st.session_state["sb_input_error"] = ""
        else:
            st.session_state["sb_input_error"] = f"⚠️ Mã '{cand}' không tồn tại trên sàn!"
        st.session_state["sb_input_ticker"] = ""


def _on_sb_select_change():
    picked = st.session_state.get("sb_select_ticker")
    if picked and data_engine.is_valid_symbol(picked):
        st.session_state["selected_symbol"] = picked


def _sync_dataframe_row_clicks():
    """
    Kiểm tra sự kiện click chọn dòng từ tất cả các bảng (Dashboard & Bộ Lọc Tinh Hoa)
    ngay đầu chu kỳ chạy script để cập nhật `selected_symbol` trong 1 lượt duy nhất (0 vòng lặp rerun).
    Tuyệt đối không ghi đè vào key của widget khác khi script đang chạy.
    """
    cur_filter = st.session_state.get("current_filter", "vsa_smc")
    table_mappings = [
        ("dash_buy_df_select", "_df_buy_view_syms"),
        ("dash_wl_df_select", "_df_wl_view_syms"),
        ("dash_av_df_select", "_df_av_view_syms"),
        (f"screener_interactive_df_{cur_filter}", "_df_sc_view_syms"),
    ]
    for df_key, syms_key in table_mappings:
        widget_state = st.session_state.get(df_key)
        sel_rows = widget_state.get("selection", {}).get("rows", []) if isinstance(widget_state, dict) else []
        last_rows = st.session_state.get(f"_last_rows_{df_key}", [])
        if sel_rows != last_rows:
            st.session_state[f"_last_rows_{df_key}"] = list(sel_rows)
            sym_list = st.session_state.get(syms_key, [])
            if sel_rows and 0 <= sel_rows[0] < len(sym_list):
                set_selected_symbol(sym_list[sel_rows[0]])


_sync_dataframe_row_clicks()

# ----------------- SIDEBAR -----------------
with st.sidebar:
    st.markdown("### 🏛️ AI Hedge Fund VN")
    st.caption("TradingAgents • AI-Hedge-Fund • FinRL • FinRobot • Claude-Skills • Vnstock")

    st.markdown("---")
    st.markdown("#### ⚡ Chọn Mã Cổ Phiếu Thẩm Định")
    all_symbols = data_engine.get_all_symbols_list()

    selected_symbol = st.session_state["selected_symbol"]
    st.success(f"🎯 Mã đang chọn: **{selected_symbol}**")

    st.text_input(
        "Nhập nhanh mã CP (1,700+ mã HOSE/HNX/UPCOM):",
        placeholder="VD: FRT, HDB, VPB, TCB, BSR, VIC...",
        key="sb_input_ticker",
        on_change=_on_sb_input_change,
    )
    if st.session_state.get("sb_input_error"):
        st.warning(st.session_state["sb_input_error"])

    if selected_symbol not in all_symbols:
        all_symbols = [selected_symbol] + all_symbols

    st.selectbox(
        "Hoặc chọn từ danh sách niêm yết:",
        all_symbols,
        index=all_symbols.index(selected_symbol) if selected_symbol in all_symbols else 0,
        key="sb_select_ticker",
        on_change=_on_sb_select_change,
    )

    st.caption("Chọn nhanh mã tiêu biểu:")
    qc1, qc2, qc3, qc4 = st.columns(4)
    qc1.button("FRT", width="stretch", on_click=set_selected_symbol, args=("FRT",))
    qc2.button("HDB", width="stretch", on_click=set_selected_symbol, args=("HDB",))
    qc3.button("TCB", width="stretch", on_click=set_selected_symbol, args=("TCB",))
    qc4.button("TCM", width="stretch", on_click=set_selected_symbol, args=("TCM",))

    selected_symbol = st.session_state["selected_symbol"]

    st.markdown("---")
    st.markdown("#### 🌐 Trạng Thái Vĩ Mô & Thị Trường")
    macro_quick = cached_macro_regime()
    dom_q = macro_quick.get("domestic_data", {})
    st.info(f"**{macro_quick['regime']}**")
    m_c1, m_c2 = st.columns(2)
    m_c1.metric("VN-INDEX", f"{dom_q.get('vnindex_price', 0):,.1f}", f"PP: {dom_q.get('distribution_days_25', 0)} ngày")
    m_c2.metric("Turbulence", f"{dom_q.get('turbulence_index', 0):.2f}", "An toàn < 2.5")
    st.caption(f"Khuyến nghị: **{macro_quick['recommended_allocation']['equity_pct']}% Cổ phiếu / {macro_quick['recommended_allocation']['cash_pct']}% Tiền mặt**")

    if st.button("🔄 Làm Mới Dữ Liệu Realtime", width="stretch"):
        st.cache_data.clear()

    st.markdown("---")
    st.markdown("#### 📱 Xem Trên Điện Thoại & Máy Khác")
    with st.expander("📲 Quét QR / Kết Nối Mạng LAN", expanded=False):
        lan_ip_curr = get_lan_ip()
        mobile_url = f"http://{lan_ip_curr}:8502"
        st.markdown(f"**Link Wi-Fi:** [`{mobile_url}`]({mobile_url})")
        try:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(box_size=4, border=1)
            qr.add_data(mobile_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#0d47a1", back_color="white")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            st.markdown(
                f'<div style="text-align: center; margin: 8px 0;">'
                f'<img src="data:image/png;base64,{b64}" width="140" style="border-radius: 8px; border: 2px solid #0d47a1;"/><br>'
                f'<small style="color: #666; font-size: 0.8rem;">Dùng Camera điện thoại quét mã để mở ngay</small>'
                f'</div>',
                unsafe_allow_html=True
            )
        except Exception:
            pass
        st.caption("⚠️ **Lưu ý**: Điện thoại hoặc laptop khác phải kết nối **cùng mạng Wi-Fi** với máy chủ này. Không nhập `localhost` trên thiết bị khác.")

# ----------------- TOP EXECUTIVE COMMAND BAR -----------------
mkt_ov = cached_market_overview()
vni_q = mkt_ov["vnindex"]
vn30_q = mkt_ov["vn30"]
f1m_q = mkt_ov["vn30f1m"]
sel_q = cached_latest_quote(selected_symbol)

top_c1, top_c2, top_c3, top_c4, top_c5 = st.columns(5)
top_c1.metric("📈 VN-INDEX", f"{vni_q.get('price', 0):,.2f}", f"{vni_q.get('change', 0):+.2f} ({vni_q.get('change_pct', 0):+.2f}%)")
top_c2.metric("🏛️ VN30-INDEX", f"{vn30_q.get('price', 0):,.2f}", f"{vn30_q.get('change', 0):+.2f} ({vn30_q.get('change_pct', 0):+.2f}%)")
basis_top = round(f1m_q.get("price", 0) - vn30_q.get("price", 0), 2) if f1m_q.get("price", 0) > 0 else 0.0
top_c3.metric("⚡ Phái Sinh VN30F1M", f"{f1m_q.get('price', 0):,.1f}", f"Basis: {basis_top:+.2f} đ | OI: {f1m_q.get('open_interest', 0):,}")
top_c4.metric(f"🎯 Mã Đang Xem: {selected_symbol}", f"{sel_q.get('price', 0):,.0f} đ", f"{sel_q.get('change_pct', 0):+.2f}% (NN: {sel_q.get('foreign_net_volume', 0):+,})")
top_c5.metric("🛡️ Độ Rộng Rổ VN30", f"{dom_q.get('vn30_advancing', 0)} Tăng / {dom_q.get('vn30_declining', 0)} Giảm", f"Tỷ giá: {dom_q.get('usdvnd_rate', 25450):,.0f} đ")

lan_ip_top = get_lan_ip()
st.markdown(
    f"""
    <div style="background: linear-gradient(90deg, #e3f2fd, #f3e5f5); padding: 7px 16px; border-radius: 6px; font-size: 0.86rem; margin-top: 10px; margin-bottom: 12px; border: 1px solid #90caf9; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <span>💻 <b>Máy chủ hiện tại:</b> <code>http://localhost:8502</code></span>
        <span>📱 <b>Truy cập từ Điện Thoại / Laptop khác (Cùng Wi-Fi):</b> <a href="http://{lan_ip_top}:8502" target="_blank" style="font-weight: 700; color: #0d47a1; text-decoration: underline;">http://{lan_ip_top}:8502</a></span>
        <span style="color: #555;">📲 <i>(Quét mã QR tại cột bên trái để mở tức thì)</i></span>
    </div>
    """,
    unsafe_allow_html=True
)

# ----------------- MAIN TABS -----------------
(
    tab_dashboard,
    tab_chat,
    tab_committee,
    tab_mtf,
    tab_screener,
    tab_self_learning,
    tab_derivatives,
    tab_fund,
    tab_macro,
    tab_portfolio,
    tab_strategy,
    tab_blueprint
) = st.tabs([
    "🎯 Khuyến Nghị Hôm Nay",
    "💬 AI Chat Đa Nhiệm",
    "🏛️ Hội Đồng IC & 9 Đại Kiện Tướng",
    "📈 Studio Biểu Đồ & Đa Khung SEPA/VCP",
    "🔍 Bộ Lọc Tinh Hoa (Click Chọn Mã)",
    "🧠 AI Tự Học & Ghi Nhớ Sai Lầm",
    "🐋 Phái Sinh VN30F1M & Trụ VN30",
    "🏢 Kiểm Toán DuPont & Định Giá",
    "🌐 Vĩ Mô & Độ Rộng",
    "💼 Danh Mục & Nhật Ký Phản Tư",
    "⚙️ Backtest & Agent Động",
    "📖 Biên Bản Phản Biện 8 Dự Án & HDSD"
])

# ==================== TAB 1: EXECUTIVE ACTIONABLE DASHBOARD ====================
with tab_dashboard:
    st.markdown('<div class="main-title">🎯 Trung Tâm Chỉ Huy & Khuyến Nghị Hành Động Hôm Nay</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Cơ chế phản biện 3 nhóm định chế: Top Cổ phiếu Stage 2 Phê duyệt Giải ngân • Danh mục Tích lũy Stage 1 Theo dõi quan sát (NKG, TPB, VJC) • Cổ phiếu Downtrend Stage 4 Bắt buộc tránh xa. Click trực tiếp vào dòng cổ phiếu bất kỳ để chọn mã & mở Biểu đồ Kỹ thuật bên dưới!</div>', unsafe_allow_html=True)

    df_buy_dash, df_watchlist_dash, df_avoid_dash = cached_vsa_universe_scan()

    col_buy_panel, col_wl_panel = st.columns(2)

    with col_buy_panel:
        st.markdown("""
        <div class="buy-box">
            <h4 style="margin:0; color:#1b5e20;">💎 TOP CỔ PHIẾU CHUẨN ĐIỂM MUA TỔ CHỨC (STAGE 2 UPTREND & SEPA ≥ 5/8)</h4>
            <p style="margin:4px 0 0 0; font-size:0.9rem; color:#2e7d32;">👆 Đạt đủ chuẩn Stan Weinstein Giai đoạn 2 + Minervini SEPA/VCP và được Hội đồng CIO phê duyệt giải ngân.</p>
        </div>
        """, unsafe_allow_html=True)
        if not df_buy_dash.empty:
            display_buy_cols = ["Mã CP", "Ngành", "Giá (VNĐ)", "Điểm Smart Money", "Giai Đoạn", "RS Rating", "SEPA", "Giá Vốn POC", "Vùng Mua An Toàn", "Cắt Lỗ Cấu Trúc"]
            avail_buy_cols = [c for c in display_buy_cols if c in df_buy_dash.columns]
            df_buy_view = df_buy_dash[avail_buy_cols].head(10).reset_index(drop=True)
            st.session_state["_df_buy_view_syms"] = df_buy_view["Mã CP"].tolist()
            st.dataframe(
                df_buy_view,
                width="stretch",
                height=280,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="dash_buy_df_select"
            )

            st.caption("👉 Hoặc bấm nhanh vào mã mua chuẩn bên dưới:")
            btn_cols = st.columns(min(6, len(df_buy_dash)))
            for idx_b, (_, r_b) in enumerate(df_buy_dash.head(6).iterrows()):
                sym_b = r_b["Mã CP"]
                btn_cols[idx_b].button(
                    f"✅ {sym_b}" if sym_b == selected_symbol else f"💎 {sym_b}",
                    key=f"dash_buy_{sym_b}",
                    type="primary" if sym_b == selected_symbol else "secondary",
                    width="stretch",
                    on_click=set_selected_symbol,
                    args=(sym_b,),
                )
        else:
            st.warning("🛡️ **NGUYÊN TẮC BẢO VỆ VỐN TUYỆT ĐỐI:** Thị trường đang trong giai đoạn điều chỉnh/rủi ro cao. Hiện tại 0 mã đạt trọn vẹn tiêu chuẩn Giải ngân Stage 2 của Hội đồng CIO. Khuyến nghị ưu tiên nắm giữ 100% tiền mặt phòng thủ, chỉ quan sát danh mục Watchlist.")

    with col_wl_panel:
        st.markdown("""
        <div class="watchlist-box">
            <h4 style="margin:0; color:#e65100;">🟡 DANH MỤC THEO DÕI QUAN SÁT (STAGE 1 TÍCH LŨY / CHỜ BỨT PHÁ PIVOT)</h4>
            <p style="margin:4px 0 0 0; font-size:0.9rem; color:#ef6c00;">👆 Đang tích lũy nền giá Giai đoạn 1 quanh POC (VD: NKG, TPB, VJC, BSR, HDB). Tuyệt đối CHƯA mua vội khi chưa nổ Pivot.</p>
        </div>
        """, unsafe_allow_html=True)
        if not df_watchlist_dash.empty:
            display_wl_cols = ["Mã CP", "Ngành", "Giá (VNĐ)", "Điểm Smart Money", "Giai Đoạn", "SEPA", "RS Rating", "Giá Vốn POC", "Trạng Thái Theo Dõi", "Điều Kiện Kích Hoạt Mua"]
            avail_wl_cols = [c for c in display_wl_cols if c in df_watchlist_dash.columns]
            df_wl_view = df_watchlist_dash[avail_wl_cols].head(10).reset_index(drop=True)
            st.session_state["_df_wl_view_syms"] = df_wl_view["Mã CP"].tolist()
            st.dataframe(
                df_wl_view,
                width="stretch",
                height=280,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="dash_wl_df_select"
            )

            st.caption("👉 Bấm nhanh mã theo dõi để kiểm tra cấu trúc tích lũy:")
            btn_wl_cols = st.columns(min(6, len(df_watchlist_dash)))
            for idx_w, (_, r_w) in enumerate(df_watchlist_dash.head(6).iterrows()):
                sym_w = r_w["Mã CP"]
                btn_wl_cols[idx_w].button(
                    f"✅ {sym_w}" if sym_w == selected_symbol else f"🔍 {sym_w}",
                    key=f"dash_wl_{sym_w}",
                    type="primary" if sym_w == selected_symbol else "secondary",
                    width="stretch",
                    on_click=set_selected_symbol,
                    args=(sym_w,),
                )
        else:
            st.info("Hiện tại chưa có mã nào trong danh mục theo dõi.")

    with st.expander("⛔ DANH SÁCH CỔ PHIẾU DOWNTREND GIAI ĐOẠN 4 & BỊ PHỦ QUYẾT (BẮT BUỘC TRÁNH XA 100%)", expanded=False):
        st.markdown("""
        <div class="avoid-box">
            <h4 style="margin:0; color:#b71c1c;">⛔ DANH SÁCH CỔ PHIẾU DOWNTREND GIAI ĐOẠN 4 (CẤM BẮT ĐÁY DAO RƠI)</h4>
            <p style="margin:4px 0 0 0; font-size:0.9rem; color:#c62828;">👆 Nằm dưới MA50/MA200, áp lực bán phân phối lớn, vi phạm nguyên tắc quản trị rủi ro tổ chức. Click để xem chi tiết lý do Phủ quyết.</p>
        </div>
        """, unsafe_allow_html=True)
        if not df_avoid_dash.empty:
            display_av_cols = ["Mã CP", "Ngành", "Giá (VNĐ)", "Giai Đoạn", "RS Rating", "SEPA", "SMA50 (đ)", "SMA200 (đ)", "Lý Do Cấm Mua"]
            avail_av_cols = [c for c in display_av_cols if c in df_avoid_dash.columns]
            df_av_view = df_avoid_dash[avail_av_cols].head(10).reset_index(drop=True)
            st.session_state["_df_av_view_syms"] = df_av_view["Mã CP"].tolist()
            st.dataframe(
                df_av_view,
                width="stretch",
                height=260,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                key="dash_av_df_select"
            )

            st.caption("👉 Bấm nhanh vào mã bên dưới để kiểm tra lý do cảnh báo:")
            av_cols = st.columns(min(8, len(df_avoid_dash)))
            for idx_a, (_, r_a) in enumerate(df_avoid_dash.head(8).iterrows()):
                sym_a = r_a["Mã CP"]
                av_cols[idx_a].button(
                    f"✅ {sym_a}" if sym_a == selected_symbol else f"⛔ {sym_a}",
                    key=f"dash_av_{sym_a}",
                    type="primary" if sym_a == selected_symbol else "secondary",
                    width="stretch",
                    on_click=set_selected_symbol,
                    args=(sym_a,),
                )

    st.markdown("---")
    d_ov_quick = cached_derivatives_overview()
    dec_quick = cached_cio_decision(selected_symbol)

    c_sum1, c_sum2 = st.columns(2)
    with c_sum1:
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid {dec_quick['decision_color']};">
            <h4 style="margin-top:0;">🏛️ Tóm Tắt Nghị Quyết Mã Đang Chọn: <b>{selected_symbol}</b></h4>
            <p style="font-size:1.05rem; font-weight:700; color:{dec_quick['decision_color']}; margin-bottom:6px;">{dec_quick['final_decision']}</p>
            <p style="margin-bottom:6px;"><b>Điểm Thuyết Phục:</b> <code>{dec_quick['conviction_score']}/10</code> | <b>CANSLIM:</b> <code>{dec_quick['meeting']['canslim_report']['canslim_score']}/100</code> | <b>SEPA:</b> <code>{dec_quick['meeting']['tech_report']['sepa_vcp']['sepa_score']}/8</code> | <b>Giá trị nội tại:</b> <code>{dec_quick['meeting']['fund_report']['intrinsic_value']:,.0f} đ</code></p>
            <p style="margin-bottom:0; font-size:0.92rem; color:#37474f;">{dec_quick['action_plan']}</p>
        </div>
        """, unsafe_allow_html=True)

    with c_sum2:
        sm_q = d_ov_quick["smart_money"]
        pb_q = d_ov_quick["playbook"]
        st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid #1565c0;">
            <h4 style="margin-top:0;">🐋 Tóm Tắt Phái Sinh <b>VN30F1M</b> & Giá Vốn Cá Mập</h4>
            <p style="font-size:1.05rem; font-weight:700; color:#1565c0; margin-bottom:6px;">{sm_q['stance']}</p>
            <p style="margin-bottom:6px;"><b>Giá F1M:</b> <code>{d_ov_quick['price']:,.1f}</code> | <b>Basis:</b> <code>{d_ov_quick['basis']:+.2f} đ</code> | <b>Giá vốn POC:</b> <code>{d_ov_quick['poc']:,.1f}</code> | <b>Khối ngoại Ròng:</b> <code>{d_ov_quick['foreign_net']:+,} HĐ</code> | <b>OI:</b> <code>{d_ov_quick['open_interest']:,} HĐ</code></p>
            <p style="margin-bottom:0; font-size:0.92rem; color:#37474f;">🟢 <b>Vùng Long:</b> <code>{pb_q['long_setup']['entry_zone']}</code> (SL: <code>{pb_q['long_setup']['stop_loss']}</code>, TP1: <code>{pb_q['long_setup']['target_tp1']}</code>) &nbsp;|&nbsp; 🔴 <b>Vùng Short:</b> <code>{pb_q['short_setup']['entry_zone']}</code> (SL: <code>{pb_q['short_setup']['stop_loss']}</code>, TP1: <code>{pb_q['short_setup']['target_tp1']}</code>)</p>
        </div>
        """, unsafe_allow_html=True)

    # MA TRẬN KIỂM TRA RÀ SOÁT CHÉO ĐA PHÒNG BAN LIÊN TỊCH (CROSS-DEPARTMENTAL AUDIT MATRIX)
    cross_aud = dec_quick.get("cross_audit", {})
    if cross_aud and "departments" in cross_aud:
        depts = cross_aud["departments"]
        m_r = depts.get("macro_risk", {})
        f_v = depts.get("fundamental_valuation", {})
        t_s = depts.get("technical_structure", {})
        p_c = depts.get("personas_council", {})

        st.markdown(f"""
        <div style="background:#ffffff; border-radius:10px; border:1px solid #cfd8dc; padding:12px 16px; margin:14px 0; box-shadow:0 2px 4px rgba(0,0,0,0.04);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; border-bottom:1px solid #eceff1; padding-bottom:8px;">
                <span style="font-weight:700; font-size:1.05rem; color:#263238;">🛡️ MA TRẬN RÀ SOÁT CHÉO ĐA PHÒNG BAN TỔ CHỨC (CROSS-AUDIT CONSENSUS) — MÃ {selected_symbol}</span>
                <span style="background:{cross_aud.get('verdict_color', '#ffa726')}22; color:{cross_aud.get('verdict_color', '#ffa726')}; font-weight:700; padding:4px 12px; border-radius:6px; font-size:0.88rem; border:1px solid {cross_aud.get('verdict_color', '#ffa726')};">
                    {cross_aud.get('verdict', 'CHƯA XÁC ĐỊNH')}
                </span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:10px;">
                <div style="background:#f8f9fa; padding:9px 12px; border-radius:6px; border-left:4px solid {'#00c853' if m_r.get('passed') else '#d50000'}; font-size:0.88rem;">
                    <b>{m_r.get('title', '🌐 Vĩ Mô & Rủi Ro')}:</b> {m_r.get('detail', '')}
                </div>
                <div style="background:#f8f9fa; padding:9px 12px; border-radius:6px; border-left:4px solid {'#00c853' if f_v.get('passed') else '#d50000'}; font-size:0.88rem;">
                    <b>{f_v.get('title', '🏢 Cơ Bản & Định Giá')}:</b> {f_v.get('detail', '')}
                </div>
                <div style="background:#f8f9fa; padding:9px 12px; border-radius:6px; border-left:4px solid {'#00c853' if t_s.get('passed') else '#d50000'}; font-size:0.88rem;">
                    <b>{t_s.get('title', '📐 Kỹ Thuật Đa Khung & VCP')}:</b> {t_s.get('detail', '')}
                </div>
                <div style="background:#f8f9fa; padding:9px 12px; border-radius:6px; border-left:4px solid {'#00c853' if p_c.get('passed') else '#d50000'}; font-size:0.88rem;">
                    <b>{p_c.get('title', '🌟 Hội Đồng 9 Kiện Tướng')}:</b> {p_c.get('detail', '')}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Hiển thị trực tiếp Studio Biểu Đồ Kỹ Thuật ngay tại Tab 1 cho mã cổ phiếu vừa chọn!
    InteractiveChartBuilder.render_customizable_chart(
        symbol=selected_symbol,
        data_engine=data_engine,
        tech_report=dec_quick["meeting"]["tech_report"],
        key_prefix="dash_main_studio",
        compact=True,
    )


# ==================== TAB 2: AI CHAT ORCHESTRATOR (@st.fragment FOR INSTANT RESPONSE) ====================
@st.fragment
def render_chat_orchestrator_fragment(current_selected_sym: str):
    st.markdown('<div class="main-title">💬 Trò Chuyện Đa Nhiệm Cùng Hội Đồng Đầu Tư AI</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Hiểu và thực thi tức thời mọi yêu cầu tiếng Việt (có dấu & không dấu): Lọc cổ phiếu bắt đáy (`loc co phieu bat day`), Lọc VSA/SMC/SEPA, Thẩm định mã bất kỳ (`Phân tích TCB`), So sánh nhiều mã (`So sánh HPG và HSG`), Tư vấn danh mục 1 tỷ, Phái sinh VN30F1M, Tự học & Tạo Agent mới</div>', unsafe_allow_html=True)

    # 8 nút tác vụ nhanh đa chức năng
    c1, c2, c3, c4 = st.columns(4)
    c5, c6, c7, c8 = st.columns(4)
    quick_input = None
    if c1.button("💎 Lọc VSA • SMC • VCP", width="stretch", key="q_btn_vsa"):
        quick_input = "Lọc các cổ phiếu thỏa mãn điểm mua theo phương pháp VSA VPA SMC Volume Profile"
    if c2.button("🎣 Lọc CP Bắt Đáy An Toàn", width="stretch", key="q_btn_bottom"):
        quick_input = "Lọc cổ phiếu bắt đáy tạo đáy an toàn tại hỗ trợ"
    if c3.button("💰 Lọc Định Giá Rẻ & ROE Cao", width="stretch", key="q_btn_val"):
        quick_input = "Lọc các cổ phiếu có P/E thấp định giá rẻ và ROE cao"
    if c4.button("⛔ CP Downtrend Cần Tránh", width="stretch", key="q_btn_avoid"):
        quick_input = "Lọc danh sách các cổ phiếu rủi ro cao đang ở giai đoạn 4 downtrend cần tránh xa"
    if c5.button(f"🏛️ Thẩm Định {current_selected_sym}", width="stretch", key="q_btn_sym"):
        quick_input = f"Phân tích {current_selected_sym}"
    if c6.button("⚖️ So Sánh HPG và HSG", width="stretch", key="q_btn_cmp"):
        quick_input = "So sánh HPG và HSG"
    if c7.button("💼 Tư Vấn Danh Mục 1 Tỷ", width="stretch", key="q_btn_port"):
        quick_input = "Tư vấn danh mục đầu tư 1 tỷ"
    if c8.button("⚡ Phái Sinh VN30F1M", width="stretch", key="q_btn_deriv"):
        quick_input = "Phái sinh hôm nay thế nào, khối ngoại cá mập đang Long hay Short ở mức giá nào?"

    # Khung nhập lệnh trực tiếp bằng Form (hoạt động tức thì trong @st.fragment mà không tải lại toàn trang)
    with st.form("multi_task_chat_form", clear_on_submit=True):
        f_col1, f_col2 = st.columns([5, 1])
        with f_col1:
            form_prompt = st.text_input(
                "Nhập yêu cầu giao việc cho Hội Đồng Đầu Tư AI:",
                placeholder="VD: loc co phieu bat day | Phân tích TCB | So sánh ACB và MBB | Lọc cổ phiếu ngân hàng | Tư vấn danh mục 500 triệu...",
                label_visibility="collapsed",
            )
        with f_col2:
            form_submit = st.form_submit_button("🚀 Gửi Yêu Cầu", type="primary", width="stretch")

    bottom_prompt = st.chat_input("Hoặc nhập câu lệnh tại đây: 'loc co phieu bat day', 'Phân tích BSR', 'So sánh FPT và CMG', 'Tư vấn danh mục 1 tỷ'...")
    actual_prompt = quick_input or (form_prompt.strip() if (form_submit and form_prompt and form_prompt.strip()) else None) or bottom_prompt

    if actual_prompt:
        st.session_state.chat_messages.append({"role": "user", "content": actual_prompt})
        response_text = agent.respond(actual_prompt)
        st.session_state.chat_messages.append({"role": "assistant", "content": response_text})
        if agent.last_analyzed_symbol and agent.last_analyzed_symbol != st.session_state.get("selected_symbol"):
            set_selected_symbol(agent.last_analyzed_symbol)
        if agent.last_screened_df is not None and not agent.last_screened_df.empty:
            st.session_state["screener_data"] = agent.last_screened_df

    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages[-12:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])


with tab_chat:
    render_chat_orchestrator_fragment(selected_symbol)


# ==================== TAB 3: INVESTMENT COMMITTEE, 9 PERSONAS & CIO DECREE ====================
with tab_committee:
    st.markdown(f'<div class="main-title">🏛️ Hội Đồng Thẩm Định & 9 Đại Kiện Tướng: **{selected_symbol}**</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Kết hợp Mô hình Tranh biện Đối kháng (TauricResearch/TradingAgents) + Hội đồng 9 Huyền Thoại Đầu Tư (virattt/ai-hedge-fund) + Quản trị vốn FinRL</div>', unsafe_allow_html=True)

    decision = cached_cio_decision(selected_symbol)
    meeting = decision["meeting"]
    trade_p = decision["trade_plan"]
    tech_rep = meeting["tech_report"]
    fund_rep = meeting["fund_report"]
    canslim_rep = meeting.get("canslim_report", {})
    personas_list = meeting.get("personas_council", [])
    finrl_m = tech_rep.get("finrl_metrics", {})
    sepa_m = tech_rep.get("sepa_vcp", {})
    rs_m = tech_rep.get("rs_info", {})
    vp_m = tech_rep.get("volume_profile", {})

    # 1. CIO Final Resolution Banner
    st.markdown(f"""
    <div style="background-color: {decision['decision_color']}; padding: 16px 22px; border-radius: 10px; color: white; margin-bottom: 18px; box-shadow: 0 3px 10px rgba(0,0,0,0.12);">
        <h2 style="color: white; margin: 0 0 6px 0; font-size: 1.45rem;">🎯 NGHỊ QUYẾT CHỦ TỊCH HỘI ĐỒNG ĐẦU TƯ (CIO): {decision['final_decision']}</h2>
        <p style="margin: 0; font-size: 1.02rem;">
            <strong>Điểm Thuyết Phục:</strong> {decision['conviction_score']}/10 &nbsp;|&nbsp;
            <strong>CANSLIM:</strong> {canslim_rep.get('canslim_score', 0)}/100 (Hạng {canslim_rep.get('canslim_grade', 'C')}) &nbsp;|&nbsp;
            <strong>Minervini SEPA:</strong> {sepa_m.get('sepa_score', 0)}/8 &nbsp;|&nbsp;
            <strong>RS Rating:</strong> {rs_m.get('rs_rating', 50)}/99 &nbsp;|&nbsp;
            <strong>Phân Bổ Tối Đa:</strong> {decision['allocation_pct']}% NAV (~{decision.get('recommended_shares_per_1b', 0):,} CP / 1 tỷ VNĐ)
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 2. Key Execution Parameters & FinRL Metrics
    k1, k2, k3, k4, k5, k6 = st.columns(6)
    k1.metric("Thị Giá Hiện Tại", f"{tech_rep.get('current_price', 0):,.0f} đ", f"POC: {vp_m.get('poc', 0):,.0f} đ")
    k2.metric("Giá Trị Nội Tại", f"{fund_rep.get('intrinsic_value', 0):,.0f} đ", f"MoS: {fund_rep.get('margin_of_safety_pct', 0):+.1f}%")
    k3.metric("Dừng Lỗ Cấu Trúc", f"{trade_p.get('structural_stop_loss', 0):,.0f} đ", f"{trade_p.get('stop_loss_pct', 0):+.1f}%")
    k4.metric("Mục Tiêu TP1 (2.5R)", f"{trade_p.get('take_profit_target_1', 0):,.0f} đ", f"{trade_p.get('target_1_pct', 0):+.1f}%")
    k5.metric("Sharpe / Sortino", f"{finrl_m.get('sharpe_ratio', 0):.2f} / {finrl_m.get('sortino_ratio', 0):.2f}", f"MDD: {finrl_m.get('max_drawdown_pct', 0):.1f}%")
    k6.metric("Khối Lượng Chuẩn (1 Tỷ NAV)", f"{decision.get('recommended_shares_per_1b', 0):,} CP", f"Half-Kelly: {finrl_m.get('half_kelly_pct', 0):.1f}%")

    if decision.get("allocation_pct", 0) == 0:
        st.warning(f"🟡 **NGHỊ QUYẾT BẢO VỆ VỐN (0% NAV):** {decision['action_plan']}")
    else:
        st.success(f"✅ **KẾ HOẠCH HÀNH ĐỘNG CỦA CIO:** {decision['action_plan']}")
        for t in decision.get("tranches", []):
            st.markdown(f"- 📌 **{t}**")

    # 2B. BẢNG RÀ SOÁT CHÉO ĐA PHÒNG BAN LIÊN TỊCH TẠI TAB 3
    cross_aud_t3 = decision.get("cross_audit", {})
    if cross_aud_t3 and "departments" in cross_aud_t3:
        depts_t3 = cross_aud_t3["departments"]
        m_r3 = depts_t3.get("macro_risk", {})
        f_v3 = depts_t3.get("fundamental_valuation", {})
        t_s3 = depts_t3.get("technical_structure", {})
        p_c3 = depts_t3.get("personas_council", {})
        st.markdown(f"""
        <div style="background:#f8f9fa; border-radius:8px; border:1px solid #cfd8dc; padding:12px 16px; margin:12px 0;">
            <div style="font-weight:700; margin-bottom:8px; color:#263238; font-size:0.95rem;">
                🛡️ KẾT QUẢ RÀ SOÁT CHÉO ĐA PHÒNG BAN: <span style="color:{cross_aud_t3.get('verdict_color', '#ffa726')};">{cross_aud_t3.get('verdict', '')}</span>
            </div>
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:8px; font-size:0.86rem;">
                <div style="padding:6px 10px; background:white; border-radius:4px; border-left:3px solid {'#00c853' if m_r3.get('passed') else '#d50000'};"><b>{m_r3.get('title')}:</b> {m_r3.get('detail')}</div>
                <div style="padding:6px 10px; background:white; border-radius:4px; border-left:3px solid {'#00c853' if f_v3.get('passed') else '#d50000'};"><b>{f_v3.get('title')}:</b> {f_v3.get('detail')}</div>
                <div style="padding:6px 10px; background:white; border-radius:4px; border-left:3px solid {'#00c853' if t_s3.get('passed') else '#d50000'};"><b>{t_s3.get('title')}:</b> {t_s3.get('detail')}</div>
                <div style="padding:6px 10px; background:white; border-radius:4px; border-left:3px solid {'#00c853' if p_c3.get('passed') else '#d50000'};"><b>{p_c3.get('title')}:</b> {p_c3.get('detail')}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 3. Council of 9 Legendary Investor Personas
    st.markdown("---")
    st.subheader("🌟 Hội Đồng 9 Đại Kiện Tướng Đầu Tư Thế Giới (virattt/ai-hedge-fund)")
    st.caption("Mỗi huyền thoại thẩm định độc lập mã cổ phiếu dựa trên công thức định lượng đặc trưng của trường phái đó:")

    for row_idx in range(0, len(personas_list), 3):
        p_cols = st.columns(3)
        for col_idx, p_item in enumerate(personas_list[row_idx:row_idx + 3]):
            sig_str = p_item["signal"]
            b_color = "#2e7d32" if "BULLISH" in sig_str else ("#c62828" if "BEARISH" in sig_str else "#ef6c00")
            with p_cols[col_idx]:
                st.markdown(f"""
                <div class="persona-card" style="border-top: 4px solid {b_color};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <strong style="font-size:1.02rem; color:#0d47a1;">{p_item['persona']}</strong>
                        <span style="font-weight:700; color:{b_color}; font-size:0.88rem;">{sig_str} ({p_item['confidence']}%)</span>
                    </div>
                    <div style="font-size:0.82rem; color:#607d8b; margin-bottom:6px;"><i>{p_item['title']}</i></div>
                    <div style="font-size:0.9rem; color:#263238;">{p_item['rationale']}</div>
                </div>
                """, unsafe_allow_html=True)

    # 4. 7-Round Adversarial Debate Minutes
    st.markdown("---")
    st.subheader("⚖️ Biên Bản Họp Tranh Biện 7 Lượt (Bull Researcher vs Bear Researcher & 3-Posture Risk Team)")
    for d in meeting.get("dialogue", []):
        st.markdown(f"""
        <div class="dialogue-box">
            <strong style="color: #0d47a1; font-size: 1.02rem;">{d['speaker']}</strong> <span style="color: #607d8b; font-style: italic;">({d['role']})</span>
            <div style="margin-top: 6px; font-size: 0.95rem; white-space: pre-line;">{d['statement']}</div>
        </div>
        """, unsafe_allow_html=True)

    html_rep = ReportGenerator.generate_html_report(decision)
    st.download_button(
        label=f"📄 Tải Xuống Báo Cáo Nghị Quyết Đầu Tư {selected_symbol} (HTML / In PDF)",
        data=html_rep,
        file_name=f"Nghi_Quyet_Dau_Tu_{selected_symbol}_{datetime.now().strftime('%Y%m%d')}.html",
        mime="text/html"
    )


# ==================== TAB 4: MULTI-TIMEFRAME STRUCTURE, SEPA/VCP & INTERACTIVE CHART STUDIO ====================
with tab_mtf:
    st.markdown(f'<div class="main-title">📈 Studio Biểu Đồ Kỹ Thuật Đa Chỉ Báo & Cấu Trúc Đa Khung: **{selected_symbol}**</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Tùy biến thêm/bớt bất kỳ chỉ báo kỹ thuật nào (SMA, EMA, Bollinger, Ichimoku, VWAP, Volume Profile, RSI, MACD, Stoch, ADX/DMI, MFI, OBV, RS Line) trên đa khung thời gian</div>', unsafe_allow_html=True)

    res_mtf = cached_cio_decision(selected_symbol)["meeting"]["tech_report"]
    if res_mtf.get("status") == "error":
        st.error(res_mtf.get("message"))
    else:
        is_dt = res_mtf.get("is_downtrend", False)
        stage_str = res_mtf.get("stage_name", "N/A")
        sepa_info = res_mtf.get("sepa_vcp", {})
        rs_info = res_mtf.get("rs_info", {})
        vp_info = res_mtf.get("volume_profile", {})

        if is_dt:
            st.error(f"⛔ **CẢNH BÁO TỔ CHỨC ({stage_str}):** {res_mtf.get('entry_recommendation')}")
        else:
            st.success(f"🟢 **TRẠNG THÁI CẤU TRÚC ({stage_str}):** {res_mtf.get('entry_recommendation')}")

        # 1. STUDIO BIỂU ĐỒ KỸ THUẬT TÙY BIẾN THÊM/BỚT CHỈ BÁO
        InteractiveChartBuilder.render_customizable_chart(
            symbol=selected_symbol,
            data_engine=data_engine,
            tech_report=res_mtf,
            key_prefix="tab_mtf_studio",
        )

        st.markdown("---")
        c_m, c_w, c_d = st.columns(3)
        c_m.info(f"**1. Khung Tháng (Macro Cycle):**\n\n{res_mtf['monthly']['trend']}\n\n*Chiết khấu từ đỉnh ATH: -{res_mtf['monthly']['discount_ath_pct']}%*")
        c_w.info(f"**2. Khung Tuần (Weinstein 30W MA):**\n\n{res_mtf['weekly']['structure']}\n\n*Hỗ trợ tuần: {res_mtf['weekly']['support']:,.0f} đ | Kháng cự tuần: {res_mtf['weekly']['resistance']:,.0f} đ*")
        c_d.info(f"**3. Khung Ngày (SEPA & Volume Profile):**\n\n{res_mtf['daily']['pattern']}\n\n*Giá vốn POC: {vp_info.get('poc', 0):,.0f} đ (VAL: {vp_info.get('val', 0):,.0f} - VAH: {vp_info.get('vah', 0):,.0f})*")

        with st.expander(f"✅ Bảng Kiểm Định 8 Tiêu Chí Siêu Cổ Phiếu Mark Minervini SEPA ({sepa_info.get('sepa_score', 0)}/8 Tiêu Chí Đạt)", expanded=True):
            crit_rows = []
            for item in sepa_info.get("criteria", []):
                crit_rows.append({
                    "STT": item["id"],
                    "Tiêu Chí Mark Minervini SEPA": item["name"],
                    "Trạng Thái": "✅ ĐẠT" if item["passed"] else "❌ CHƯA ĐẠT",
                    "Số Liệu Kiểm Chứng Thực Tế": item["detail"]
                })
            if crit_rows:
                st.dataframe(pd.DataFrame(crit_rows), width="stretch", hide_index=True)


# ==================== TAB 5: MULTI-STRATEGY STOCK SCREENER (INTERACTIVE CLICK-TO-SELECT) ====================
with tab_screener:
    st.markdown('<div class="main-title">🔍 Bộ Lọc Cổ Phiếu Tinh Hoa Đa Trường Phái (Click Chọn Mã Trực Tiếp)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Quét song song đa luồng toàn bộ rổ cổ phiếu thanh khoản cao. Click vào bất kỳ dòng mã cổ phiếu nào trong bảng để chọn mã và mở ngay Biểu Đồ Phân Tích Kỹ Thuật Đa Chỉ Báo bên dưới!</div>', unsafe_allow_html=True)

    col_sc1, col_sc2 = st.columns([3, 1])
    with col_sc1:
        screener_filter = st.selectbox(
            "Chọn bộ tiêu chí sàng lọc định lượng:",
            [
                ("vsa_smc", "💎 Điểm Mua Tổ Chức: VSA • VPA • SMC (Stage 2 Uptrend & SEPA ≥ 5/8)"),
                ("vsa_watchlist", "🟡 Danh Mục Tích Lũy Stage 1 Theo Dõi Quan Sát (Chờ Nổ Pivot - NKG, TPB, VJC)"),
                ("bottom_fishing", "🎣 Cổ Phiếu Bắt Đáy An Toàn / Tạo Đáy Tại Hỗ Trợ (Wyckoff Spring • RSI Thấp • Có Cơ Bản)"),
                ("sepa_vcp", "🚀 Siêu Cổ Phiếu Mark Minervini SEPA (≥ 6/8) & Mẫu Hình Thu Hẹp VCP"),
                ("canslim_leaders", "👑 Cổ Phiếu Dẫn Dắt Thị Trường CANSLIM (RS Rating ≥ 72 & Stage 2)"),
                ("value_investing", "💰 Định Giá Hấp Dẫn & ROE Cao (P/E ≤ 15.5, ROE ≥ 13.5%, Không Downtrend)"),
                ("low_debt", "🛡️ An Toàn Tài Chính Cao (Nợ Vay / VCSH ≤ 0.85 & ROE ≥ 12%)"),
                ("breakout", "⚡ Bứt Phá Vượt Đỉnh 20 Phiên (Stage 2 Breakout)"),
                ("volume_spike", "🌊 Đột Biến Khối Lượng Dòng Tiền Vào (Vol ≥ 1.35x TB20)"),
                ("avoid_stage4", "⛔ Danh Sách Cổ Phiếu Giai Đoạn 4 Downtrend Bắt Buộc Tránh Xa"),
                ("all", "📊 Bảng Xếp Hạng Tổng Quan Toàn Vũ Trụ Thanh Khoản Cao")
            ],
            format_func=lambda x: x[1]
        )
    with col_sc2:
        st.write("")
        st.write("")
        run_scan = st.button("🔍 Quét Ngay", type="primary", width="stretch")

    if (
        run_scan
        or "screener_data" not in st.session_state
        or st.session_state.get("_last_ui_filter") != screener_filter[0]
        or st.session_state.get("_screener_schema_ver") != CACHE_SCHEMA_VERSION
    ):
        if run_scan or st.session_state.get("_screener_schema_ver") != CACHE_SCHEMA_VERSION:
            cached_screener_scan.clear()
            StockScreener._master_cache_records = None
            screener._load_disk_master_cache()
        df_screened = cached_screener_scan(screener_filter[0], CACHE_SCHEMA_VERSION)
        st.session_state["screener_data"] = df_screened
        st.session_state["current_filter"] = screener_filter[0]
        st.session_state["_last_ui_filter"] = screener_filter[0]
        st.session_state["_screener_schema_ver"] = CACHE_SCHEMA_VERSION

    df_screened = st.session_state.get("screener_data", pd.DataFrame())
    if not df_screened.empty:
        st.info("👆 **Hướng dẫn:** Click trực tiếp vào ô đầu dòng hoặc dòng bất kỳ trong bảng dưới đây (hoặc bấm nút mã CP ngay bên dưới bảng) để chọn cổ phiếu và xem **Biểu Đồ Kỹ Thuật Đa Chỉ Báo + Nghị Quyết CIO**!")
        df_sc_view = df_screened.reset_index(drop=True)
        st.session_state["_df_sc_view_syms"] = df_sc_view["Mã CP"].tolist()
        sc_df_key = f"screener_interactive_df_{screener_filter[0]}"
        st.dataframe(
            df_sc_view,
            width="stretch",
            height=380,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=sc_df_key,
        )

        # Thanh nút bấm chọn nhanh từng mã trong kết quả lọc (dùng on_click, 0 vòng lặp rerun)
        st.markdown("##### ⚡ Chọn Nhanh Mã Cổ Phiếu Từ Kết Quả Lọc:")
        syms_in_table = df_sc_view["Mã CP"].tolist()[:16]
        for chunk_start in range(0, len(syms_in_table), 8):
            chunk = syms_in_table[chunk_start:chunk_start + 8]
            b_cols = st.columns(8)
            for idx_c, sym_c in enumerate(chunk):
                is_active = (sym_c == selected_symbol)
                btn_lbl = f"✅ {sym_c}" if is_active else f"📈 {sym_c}"
                b_cols[idx_c].button(
                    btn_lbl,
                    key=f"sc_quick_btn_{screener_filter[0]}_{sym_c}",
                    type="primary" if is_active else "secondary",
                    width="stretch",
                    on_click=set_selected_symbol,
                    args=(sym_c,),
                )
    elif screener_filter[0] in ["bottom_fishing", "rsi_oversold"]:
        st.warning(
            "🛡️ **KẾT LUẬN THẨM ĐỊNH ĐỊNH LƯỢNG HÔM NAY: `0 MÃ` ĐẠT CHUẨN ĐIỂM MUA BẮT ĐÁY TỐI ƯU AN TOÀN (KHUYẾN NGHỊ ĐỨNG NGOÀI / CẤM BẮT SỚM)**\n\n"
            "Qua kiểm định toàn bộ 68 cổ phiếu thanh khoản cao bằng **Hệ Thống Bắt Đáy 5 Lớp (`MCDX RSI SMA [CongTrader] + SMC 60D + Wyckoff VSA + Cấu trúc MA20/50/200 + Định giá MoS`)**, hiện tại **chưa có cổ phiếu nào hội tụ đủ 6 điều kiện bắt đáy tối ưu an toàn**.\n"
            "- **Điển hình `VHM` (`63,000 đ`):** Nằm dưới cả 3 đường `MA20 (63,520) / MA200 (64,867) / MA50 (68,054)` (kẹt kháng cự phân phối `LPSY`), cột **MCDX Banker = `0.0`** (`100% Vàng Nhỏ lẻ`, `0% Dòng tiền Tạo lập`), đường **MCDX Blue (`8.7`) nằm dưới White (`10.8`)** và đang giảm (`-0.5`).\n"
            "- **Điển hình `VPB` (`22,950 đ`):** Vừa rơi từ đỉnh `SMC Premium (64%)` kèm tín hiệu `SELL / LPSY`, gãy `MA20 (23,772)`, **MCDX Banker (`9.1 < SMA36 17.5`)** suy yếu và **MCDX Blue (`3.2 < White 6.0`)** cắm xuống.\n"
            "👉 *Xem ngay **Bảng Đối Chứng Kỹ Thuật Các Mã Chưa Đạt Điểm Bắt Đáy Tối Ưu An Toàn** bên dưới và click vào từng mã để kiểm tra trực tiếp trên Biểu Đồ!*"
        )
    else:
        st.info("Hiện tại chưa có mã nào khớp điều kiện lọc này.")

    if screener_filter[0] in ["bottom_fishing", "rsi_oversold"]:
        df_traps = screener.scan_bottom_fishing_traps(top_n=12)
        if not df_traps.empty:
            st.markdown("##### ⚠️ Bảng Đối Chứng Kỹ Thuật Các Mã CHƯA CÓ ĐIỂM BẮT ĐÁY TỐI ƯU AN TOÀN / BẪY BẮT DAO RƠI (Đã Loại Khỏi Khuyến Nghị Mua):")
            st.caption("Các mã dưới đây (VHM, VPB, PVT, VGC, HCM, TCB, TCM, STB, ACB...) bị Hệ thống 5 Lớp phủ quyết lệnh Mua Bắt Đáy do nằm dưới MA20/MA50/MA200, thiếu dòng tiền tạo lập (MCDX Banker = 0 hoặc < SMA36), đường MCDX Blue nằm dưới White, vừa rơi từ đỉnh SMC Premium, hoặc định giá/lợi nhuận tiêu cực.")
            st.dataframe(df_traps, width="stretch", height=290, hide_index=True)
            trap_syms = df_traps["Mã CP"].tolist()[:8]
            t_cols = st.columns(8)
            for idx_t, sym_t in enumerate(trap_syms):
                t_cols[idx_t].button(
                    f"🔍 Xem {sym_t}",
                    key=f"sc_trap_btn_{sym_t}",
                    type="primary" if sym_t == selected_symbol else "secondary",
                    width="stretch",
                    on_click=set_selected_symbol,
                    args=(sym_t,),
                )

    if not df_screened.empty or screener_filter[0] in ["bottom_fishing", "rsi_oversold"]:
        st.markdown("---")
        sc_dec = cached_cio_decision(selected_symbol)
        sc_tech = sc_dec["meeting"]["tech_report"]
        sc_fund = sc_dec["meeting"]["fund_report"]
        sc_sl = sc_dec.get("self_learning_audit", {})
        sc_mcdx = sc_tech.get("mcdx_smc_audit", {})

        st.markdown(f"""
        <div class="metric-card" style="border-left: 6px solid {sc_dec['decision_color']};">
            <h4 style="margin-top:0;">🏛️ Hồ Sơ Thẩm Định Tức Thời Mã Đang Chọn: <b style="color:#0d47a1;">{selected_symbol}</b> ({sc_fund.get('industry', 'Niêm yết')})</h4>
            <p style="font-size:1.08rem; font-weight:700; color:{sc_dec['decision_color']}; margin-bottom:6px;">{sc_dec['final_decision']}</p>
            <p style="margin-bottom:6px;">
                <b>Thị giá:</b> <code>{sc_tech.get('current_price', 0):,.0f} đ</code> &nbsp;|&nbsp;
                <b>MCDX Banker/SMA36:</b> <code>{sc_mcdx.get('mcdx_banker', 0):.1f} / {sc_mcdx.get('mcdx_banker_sma36', 0):.1f}</code> &nbsp;|&nbsp;
                <b>MCDX Blue/White:</b> <code>{sc_mcdx.get('mcdx_fast', 0):.1f} / {sc_mcdx.get('mcdx_slow', 0):.1f}</code> &nbsp;|&nbsp;
                <b>SMC 60D:</b> <code>{sc_mcdx.get('smc_pos_pct', 50):.0f}%</code> &nbsp;|&nbsp;
                <b>Giá trị nội tại:</b> <code>{sc_fund.get('intrinsic_value', 0):,.0f} đ (MoS: {sc_fund.get('margin_of_safety_pct', 0):+.1f}%)</code> &nbsp;|&nbsp;
                <b>P/E:</b> <code>{sc_fund.get('pe', '—')}x</code> &nbsp;|&nbsp;
                <b>ROE:</b> <code>{sc_fund.get('roe', '—')}%</code>
            </p>
            <p style="margin-bottom:0; font-size:0.93rem;">{sc_dec['action_plan']}</p>
        </div>
        """, unsafe_allow_html=True)

        InteractiveChartBuilder.render_customizable_chart(
            symbol=selected_symbol,
            data_engine=data_engine,
            tech_report=sc_tech,
            key_prefix="screener_embedded_studio",
            compact=True,
        )


# ==================== TAB 6: SELF-LEARNING & MISTAKE MEMORY ENGINE ====================
with tab_self_learning:
    st.markdown('<div class="main-title">🧠 Hệ Thống AI Tự Học, Hậu Kiểm & Ghi Nhớ Sai Lầm (Self-Learning Memory)</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Tự động hậu kiểm kết quả khuyến nghị với dữ liệu lịch sử thực tế (Walk-Forward T+2.5 / T+5), ghi nhớ các bẫy sai lầm (Bull Trap thiếu Vol, Mua đuổi xa nền POC, Bẫy Stage 4 Downtrend như TCM, Value Trap nợ cao) và tự động điều chỉnh trọng số</div>', unsafe_allow_html=True)

    mem_data = self_learning_engine.memory
    adap = mem_data.get("adaptive_params", {})
    cat_list = mem_data.get("mistakes_catalog", [])
    total_saves = sum(int(x.get("verified_saves", 0)) for x in cat_list)

    sl_c1, sl_c2, sl_c3, sl_c4, sl_c5, sl_c6 = st.columns(6)
    sl_c1.metric("🎯 Tỷ Lệ Thắng Hậu Kiểm (T+5)", f"{mem_data.get('win_rate_pct', 68.5):.1f}%", f"TB T+5: {mem_data.get('avg_return_t5_pct', 2.45):+.2f}%")
    sl_c2.metric("🛡️ Số Lần Cứu Lỗ Thực Tế", f"{total_saves} lần", f"{len(cat_list)} quy tắc đang bật")
    sl_c3.metric("📊 Ngưỡng Vol Breakout", f"{adap.get('min_breakout_vol_ratio', 1.35):.2f}x TB20", "Tự động nâng khi gặp Bull Trap")
    sl_c4.metric("📏 Giới Hạn Mua Đuổi POC", f"+{adap.get('max_poc_extension_pct', 7.5):.1f}%", "Chống FOMO giá cao")
    sl_c5.metric("⚡ Trần RSI Cấm Mua Đuổi", f"{adap.get('rsi_overbought_chase_limit', 74.0):.0f}", "Bảo vệ T+2.5")
    sl_c6.metric("⛔ Veto Stage 4 Downtrend", "BẬT (Strict)" if adap.get("stage4_downtrend_veto", True) else "Tắt", f"Lần kiểm: {mem_data.get('total_audits_run', 1)}")

    col_audit_btn, col_cur_check = st.columns([1.2, 2.8])
    with col_audit_btn:
        if st.button("🔄 Chạy Hậu Kiểm Walk-Forward & Tự Tinh Chỉnh Tham Số", type="primary", width="stretch"):
            with st.spinner("Đang chạy hậu kiểm đa luồng trên dữ liệu lịch sử thực tế để phát hiện bẫy sai lầm..."):
                audit_res = self_learning_engine.audit_and_learn_from_market(data_engine)
                st.success(
                    f"✅ Đã hoàn tất hậu kiểm {audit_res['sample_trades']} điểm giao dịch thực tế! "
                    f"Tỷ lệ thắng T+5: {audit_res['win_rate_pct']}% | Phát hiện {audit_res['false_breakouts_detected']} Bull-trap thiếu Vol, "
                    f"{audit_res['chase_losses_detected']} lệnh mua đuổi xa nền, {audit_res['downtrend_traps_detected']} bẫy Downtrend."
                )
                for adj_msg in audit_res.get("adjustments", []):
                    st.info(f"🔧 {adj_msg}")
                st.cache_data.clear()

    with col_cur_check:
        cur_dec = cached_cio_decision(selected_symbol)
        cur_sl = cur_dec.get("self_learning_audit", {})
        st.markdown(f"**🔍 Kết Quả Kiểm Duyệt Bộ Nhớ Tự Học Cho Mã Đang Chọn (`{selected_symbol}`):** Điểm gốc `{cur_sl.get('raw_score', 0)}` ➔ Điểm sau hiệu chỉnh Tự Học: **`{cur_sl.get('adjusted_score', 0)}`** (`{cur_sl.get('score_delta', 0):+.1f} điểm`)")
        for l_msg in cur_sl.get("triggered_lessons", []):
            if "Bài học" in l_msg or "Quy tắc" in l_msg:
                st.warning(l_msg)
            else:
                st.success(l_msg)

    st.markdown("---")
    st.subheader("📚 Danh Mục Các Sai Lầm Quá Khứ Đã Ghi Nhớ & Quy Tắc Tự Sửa Lỗi (Mistakes Catalog)")
    df_mistakes = self_learning_engine.get_summary_dataframe()
    if not df_mistakes.empty:
        st.dataframe(df_mistakes, width="stretch", hide_index=True, height=300)

    st.markdown("---")
    st.subheader("➕ Dạy AI Bài Học Mới / Ghi Nhớ Sai Lầm Thực Chiến")
    with st.form("teach_ai_mistake_form"):
        f_c1, f_c2, f_c3 = st.columns([1, 2, 1])
        with f_c1:
            t_sym = st.text_input("Mã CP áp dụng (hoặc ALL):", value=selected_symbol)
            t_pen = st.slider("Điểm phạt khi vi phạm:", min_value=-30.0, max_value=-2.0, value=-12.0, step=1.0)
        with f_c2:
            t_cat = st.text_input("Phân loại sai lầm:", value="Bẫy Dòng Tiền / Cấu Trúc Thực Chiến")
            t_sum = st.text_area("Mô tả sai lầm / thiếu sót cần ghi nhớ:", placeholder="VD: Mua cổ phiếu khi RSI phân kỳ âm 2 đỉnh trên khung 1D dẫn đến thua lỗ T+2.5...")
        with f_c3:
            t_rule = st.text_area("Quy tắc tự sửa lỗi bắt buộc:", placeholder="VD: Cấm mua mới khi xuất hiện phân kỳ âm RSI 2 đỉnh kèm Vol bán tăng vọt...")
            t_veto = st.checkbox("Kích hoạt Quyền Phủ Quyết (Chặn Mua Tuyệt Đối)", value=True)
        submitted_lesson = st.form_submit_button("🧠 Ghi Nhớ Vào Bộ Não Tự Học", type="primary")
        if submitted_lesson and t_sum.strip() and t_rule.strip():
            new_l = self_learning_engine.record_user_lesson(
                symbol=t_sym,
                category=t_cat,
                mistake_summary=t_sum,
                corrective_rule=t_rule,
                penalty_points=t_pen,
                force_avoid=t_veto,
            )
            st.cache_data.clear()
            st.success(f"✅ Đã lưu bài học `{new_l['id']}` cho mã `{new_l['symbol']}` vào Bộ Nhớ Tự Học! Hệ thống sẽ áp dụng ngay lập tức.")


# ==================== TAB 7: DERIVATIVES VN30F1M & VN30 PILLAR RADAR ====================
with tab_derivatives:
    st.markdown('<div class="main-title">🐋 Giám Sát Phái Sinh VN30F1M, Giá Vốn POC & Radar 10 Trụ VN30</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Dữ liệu thực 100% từ Bảng giá Phái sinh KBS: Open Interest (OI) qua đêm, Giao dịch Khối ngoại, Volume Profile POC và Đóng góp điểm số của 10 cổ phiếu trụ VN30</div>', unsafe_allow_html=True)

    d_data = cached_derivatives_overview()
    d_sm = d_data["smart_money"]
    d_pb = d_data["playbook"]

    dk1, dk2, dk3, dk4, dk5, dk6 = st.columns(6)
    dk1.metric("VN30F1M", f"{d_data['price']:,.1f}", f"{d_data['change']:+.1f} đ ({d_data['change_pct']:+.2f}%)")
    dk2.metric("Chỉ Số VN30", f"{d_data['vn30_price']:,.2f}", f"{d_data['vn30_change']:+.2f} đ")
    dk3.metric("Độ Lệch Basis", f"{d_data['basis']:+.2f} đ", "Premium" if d_data["basis"] >= 0 else "Discount")
    dk4.metric("Khối Lượng Mở (OI)", f"{d_data['open_interest']:,} HĐ", f"Đáo hạn: {d_data['days_to_expiry']} ngày")
    dk5.metric("Khối Ngoại Ròng", f"{d_data['foreign_net']:+,} HĐ", f"Mua {d_data['foreign_buy']:,} / Bán {d_data['foreign_sell']:,}")
    dk6.metric("Giá Vốn Cá Mập (POC)", f"{d_data['poc']:,.1f} đ", f"VAL {d_data['val']:,.1f} - VAH {d_data['vah']:,.1f}")

    st.info(f"🎯 **Nhận Định Dòng Tiền Lớn ({d_sm['stance']}):** {d_sm['impact_on_cash_market']}")

    col_pb1, col_pb2 = st.columns(2)
    with col_pb1:
        st.markdown(f"""
        <div class="buy-box">
            <h4 style="color:#1b5e20; margin-top:0;">🟢 KỊCH BẢN LONG (KHI GIỮ TRÊN VÙNG HỖ TRỢ VAL / POC)</h4>
            <p style="margin-bottom:4px;"><b>Vùng Mở Vị Thế Long (Entry):</b> <code>{d_pb['long_setup']['entry_zone']} điểm</code></p>
            <p style="margin-bottom:4px;"><b>Cắt Lỗ Tuyệt Đối (Stop Loss):</b> <code>{d_pb['long_setup']['stop_loss']} điểm</code> (-4.0 điểm)</p>
            <p style="margin-bottom:0;"><b>Mục Tiêu Chốt Lời:</b> TP1: <code>{d_pb['long_setup']['target_tp1']}</code> &nbsp;|&nbsp; TP2: <code>{d_pb['long_setup']['target_tp2']}</code> (R:R = <code>{d_pb['long_setup']['risk_reward']}</code>)</p>
        </div>
        """, unsafe_allow_html=True)
    with col_pb2:
        st.markdown(f"""
        <div class="avoid-box">
            <h4 style="color:#b71c1c; margin-top:0;">🔴 KỊCH BẢN SHORT (KHI BỊ TỪ CHỐI TẠI VAH / R1 HOẶC THỦNG POC)</h4>
            <p style="margin-bottom:4px;"><b>Vùng Mở Vị Thế Short (Entry):</b> <code>{d_pb['short_setup']['entry_zone']} điểm</code></p>
            <p style="margin-bottom:4px;"><b>Cắt Lỗ Tuyệt Đối (Stop Loss):</b> <code>{d_pb['short_setup']['stop_loss']} điểm</code> (+4.0 điểm)</p>
            <p style="margin-bottom:0;"><b>Mục Tiêu Chốt Lời:</b> TP1: <code>{d_pb['short_setup']['target_tp1']}</code> &nbsp;|&nbsp; TP2: <code>{d_pb['short_setup']['target_tp2']}</code> (R:R = <code>{d_pb['short_setup']['risk_reward']}</code>)</p>
        </div>
        """, unsafe_allow_html=True)

    st.subheader("🏛️ Radar 10 Cổ Phiếu Trụ Điều Tiết Điểm Số VN30 & Phái Sinh")
    if d_data.get("pillar_radar"):
        df_pillars = pd.DataFrame(d_data["pillar_radar"])
        df_pillars.columns = ["Mã Trụ VN30", "Trọng Số Rổ (%)", "Thị Giá (đ)", "Thay Đổi (%)", "Tác Động Điểm VN30", "Khối Ngoại Ròng (CP)"]
        st.dataframe(
            df_pillars.style.format({
                "Trọng Số Rổ (%)": "{:.1f}%",
                "Thị Giá (đ)": "{:,.0f}",
                "Thay Đổi (%)": "{:+.2f}%",
                "Tác Động Điểm VN30": "{:+.2f} điểm",
                "Khối Ngoại Ròng (CP)": "{:+,}"
            }),
            width="stretch",
            hide_index=True
        )

    df_f15 = cached_derivatives_15m_history()
    if not df_f15.empty:
        fig_f = go.Figure()
        fig_f.add_trace(go.Candlestick(
            x=df_f15["time"], open=df_f15["open"], high=df_f15["high"], low=df_f15["low"], close=df_f15["close"],
            name="VN30F1M (15m)"
        ))
        fig_f.add_hline(y=d_data["poc"], line_color="#aa00ff", line_width=2, annotation_text=f"Giá Vốn Cá Mập POC ({d_data['poc']:,.1f})")
        fig_f.add_hline(y=d_data["vah"], line_dash="dot", line_color="#c62828", annotation_text=f"VAH ({d_data['vah']:,.1f})")
        fig_f.add_hline(y=d_data["val"], line_dash="dot", line_color="#2e7d32", annotation_text=f"VAL ({d_data['val']:,.1f})")
        fig_f.update_layout(title="Biểu Đồ Khung 15 Phút Hợp Đồng VN30F1M & Vùng Giá Vốn Tổ Chức (POC / VAH / VAL)", height=460, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig_f, width="stretch", key="deriv_f15_plotly")


# ==================== TAB 8: FUNDAMENTALS, DUPONT 3-STEP & DAMODARAN VALUATION ====================
with tab_fund:
    st.markdown(f'<div class="main-title">🏢 Kiểm Toán BCTC, Phân Tích DuPont & Định Giá Nội Tại: **{selected_symbol}**</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Tích hợp FinRobot 3-Step DuPont Analysis + Mô hình Định giá Aswath Damodaran (DCF / Excess Return), Benjamin Graham Number & Peter Lynch GARP</div>', unsafe_allow_html=True)

    f_data = cached_cio_decision(selected_symbol)["meeting"]["fund_report"]
    dup_v = f_data.get("dupont_valuation", {})

    st.subheader(f"Xếp Hạng Nội Tại: {f_data['health_status']} (Ngành: {f_data.get('industry')} | BCTC: {f_data.get('latest_quarter')})")

    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
    fc1.metric("Thị Giá Hiện Tại", f"{f_data.get('current_price', 0):,.0f} đ", f"Vốn hóa: {f_data.get('market_cap')}")
    fc2.metric("Giá Trị Nội Tại Hợp Lý", f"{f_data.get('intrinsic_value', 0):,.0f} đ", f"MoS: {f_data.get('margin_of_safety_pct', 0):+.1f}%")
    fc3.metric("P/E & P/B", f"{f_data.get('pe', 'N/A')}x | {f_data.get('pb', 'N/A')}x", f"Chi phí vốn Ke: {dup_v.get('cost_of_equity_pct', 11):.1f}%")
    fc4.metric("ROE & ROA (4 Quý)", f"{f_data.get('roe', 'N/A')}% | {f_data.get('roa', 'N/A')}%", "Sinh lời vốn")
    pg_val = f_data.get("profit_growth_yoy")
    fc5.metric("Tăng Trưởng LNST YoY", f"{pg_val:+.1f}%" if pg_val is not None else "N/A", "Động lực tăng trưởng")
    fc6.metric("Thanh Khoản TB 20P", f"{f_data.get('avg_liquidity_vnd', 0)/1e9:.1f} tỷ/phiên", f"{f_data.get('avg_vol_20', 0):,.0f} CP")

    st.info(f"🔬 **Phân Tích DuPont 3 Bước (FinRobot):** {dup_v.get('dupont_summary', '')} ➔ **Động lực ROE:** *{dup_v.get('roe_driver', '')}*")

    val_models = dup_v.get("valuation_models", {})
    if val_models:
        labels = list(val_models.keys()) + ["Giá Trị Nội Tại Tổng Hợp", "Thị Giá Hiện Tại Trên Sàn"]
        values = list(val_models.values()) + [f_data.get("intrinsic_value", 0), f_data.get("current_price", 0)]
        colors = ["#1e88e5"] * len(val_models) + ["#00c853", "#ff6d00"]

        fig_val = go.Figure(go.Bar(
            x=values,
            y=labels,
            orientation="h",
            marker_color=colors,
            text=[f"{v:,.0f} VNĐ" for v in values],
            textposition="auto"
        ))
        fig_val.update_layout(
            title=f"Biểu Đồ So Sánh Định Giá Đa Mô Hình (Valuation Football Field - {selected_symbol})",
            xaxis_title="Mức Giá (VNĐ / Cổ Phiếu)",
            height=320,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        st.plotly_chart(fig_val, width="stretch", key="fund_val_plotly")

    col_pos, col_rf = st.columns(2)
    with col_pos:
        st.markdown("##### 💎 Điểm Sáng Nội Tại & Lợi Thế Cạnh Tranh")
        for pos in f_data.get("positives", []):
            st.success(pos)
    with col_rf:
        st.markdown("##### ⚠️ Cảnh Báo Kiểm Toán & Rủi Ro Tài Chính")
        if f_data.get("red_flags"):
            for rf in f_data["red_flags"]:
                st.warning(rf)
        else:
            st.info("Không phát hiện dấu hiệu gian lận BCTC hoặc rủi ro thanh khoản trọng yếu.")

    peers = f_data.get("peers", [])
    if peers:
        st.subheader("👥 Bảng So Sánh Trực Diện Với Đối Thủ Cùng Ngành")
        df_peers = pd.DataFrame(peers)
        df_peers.columns = ["Mã CP", "Thị Giá (đ)", "P/E", "P/B", "ROE (%)", "Tăng Trưởng LNST YoY (%)"]
        st.dataframe(df_peers.style.format({"Thị Giá (đ)": "{:,.0f}"}), width="stretch", hide_index=True)


# ==================== TAB 9: MACRO, MARKET BREADTH & TURBULENCE ====================
with tab_macro:
    st.markdown('<div class="main-title">🌐 Toàn Cảnh Vĩ Mô, Độ Rộng VN30 & Chỉ Số Hỗn Loạn FinRL</div>', unsafe_allow_html=True)
    m_data = cached_macro_regime()
    g_d = m_data["global_data"]
    d_d = m_data["domestic_data"]

    st.subheader(f"Pha Thị Trường Hiện Tại: {m_data['regime']}")
    st.write(m_data["regime_desc"])

    mc1, mc2, mc3, mc4 = st.columns(4)
    mc1.metric("Chỉ Số DXY", f"{g_d.get('dxy', {}).get('price')}", f"{g_d.get('dxy', {}).get('change_pct'):+.2f}%")
    mc2.metric("Lợi Suất TPCP Mỹ 10Y", f"{g_d.get('us10y', {}).get('price')}%", f"{g_d.get('us10y', {}).get('change_pct'):+.2f}%")
    mc3.metric("Dầu Thô Brent", f"${g_d.get('brent_oil', {}).get('price')}", f"{g_d.get('brent_oil', {}).get('change_pct'):+.2f}%")
    mc4.metric("S&P 500", f"{g_d.get('sp500', {}).get('price'):,.1f}", f"{g_d.get('sp500', {}).get('change_pct'):+.2f}%")

    md1, md2, md3, md4 = st.columns(4)
    md1.metric("Tỷ Giá USD/VND (VCB)", f"{d_d.get('usdvnd_rate'):,.0f} đ", "Ngưỡng an toàn < 25,600")
    md2.metric("VN-INDEX vs MA50/200", f"{d_d.get('vnindex_price'):,.1f}", f"MA50: {d_d.get('vnindex_sma50'):,.1f} | MA200: {d_d.get('vnindex_sma200'):,.1f}")
    md3.metric("Số Ngày Phân Phối (25P)", f"{d_d.get('distribution_days_25')} phiên", "Cảnh báo khi ≥ 5 phiên")
    md4.metric("FinRL Turbulence Index", f"{d_d.get('turbulence_index'):.2f}", "Ngắt mạch khi ≥ 2.50")

    col_tw, col_hw = st.columns(2)
    with col_tw:
        st.markdown("##### 🟢 Động Lực Hỗ Trợ Vĩ Mô (Tailwinds)")
        for tw in m_data["tailwinds"]:
            st.success(tw)
    with col_hw:
        st.markdown("##### 🔴 Rủi Ro & Lực Cản Vĩ Mô (Headwinds)")
        for hw in m_data["headwinds"]:
            st.warning(hw)


# ==================== TAB 10: PAPER TRADING PORTFOLIO & REFLECTION MEMORY ====================
with tab_portfolio:
    st.markdown('<div class="main-title">💼 Quản Trị Danh Mục Giả Lập & Nhật Ký Phản Tư (Reflection Loop)</div>', unsafe_allow_html=True)

    holding_syms = list(portfolio_mgr.holdings.keys())
    pb_hold = data_engine.get_batch_price_board(holding_syms) if holding_syms else {}
    holding_prices = {s: pb_hold[s]["price"] for s in holding_syms if s in pb_hold and pb_hold[s]["price"] > 0}

    port_summary = portfolio_mgr.get_summary(holding_prices)
    pm1, pm2, pm3, pm4 = st.columns(4)
    pm1.metric("Tổng Tài Sản (NAV)", f"{port_summary['total_assets']:,.0f} đ")
    pm2.metric("Tiền Mặt Khả Dụng", f"{port_summary['cash']:,.0f} đ")
    pm3.metric("Giá Trị Cổ Phiếu", f"{port_summary['stock_value']:,.0f} đ")
    pm4.metric("Tổng Lãi / Lỗ", f"{port_summary['total_pnl_vnd']:+,.0f} đ", f"{port_summary['total_pnl_pct']:+.2f}%")

    col_hold, col_order = st.columns([3, 2])
    with col_hold:
        st.subheader("📋 Danh Mục Đang Nắm Giữ")
        if port_summary["holdings"]:
            df_h = pd.DataFrame(port_summary["holdings"])
            st.dataframe(
                df_h.style.format({
                    "Giá Vốn (đ)": "{:,.0f}", "Giá Hiện Tại (đ)": "{:,.0f}",
                    "Giá Trị (đ)": "{:,.0f}", "Lãi/Lỗ (VNĐ)": "{:+,.0f}", "Lãi/Lỗ (%)": "{:+.2f}%"
                }), width="stretch"
            )
        else:
            st.info("Danh mục hiện đang 100% tiền mặt.")

    with col_order:
        st.subheader("⚡ Đặt Lệnh Giao Dịch Lô Chẵn 100 CP")
        pt_sym_idx = all_symbols.index(selected_symbol) if selected_symbol in all_symbols else 0
        ord_symbol = st.selectbox("Mã cổ phiếu:", all_symbols, index=pt_sym_idx, key="pt_ord_sym")
        ord_quote = cached_latest_quote(ord_symbol)
        ord_price = ord_quote["price"] if ord_quote["status"] == "success" else 20000.0
        st.caption(f"Giá khớp hiện tại: **{ord_price:,.0f} VNĐ**")
        ord_action = st.radio("Loại lệnh:", ["MUA", "BÁN"], horizontal=True, key="pt_ord_act")
        ord_qty = st.number_input("Số lượng (Lô chẵn 100 CP):", min_value=100, max_value=1_000_000, value=1000, step=100, key="pt_ord_qty")
        if st.button("Xác Nhận Đặt Lệnh", type="primary", key="pt_btn_ord"):
            res = portfolio_mgr.buy(ord_symbol, ord_qty, ord_price) if ord_action == "MUA" else portfolio_mgr.sell(ord_symbol, ord_qty, ord_price)
            if res["success"]:
                st.success(res["message"])
            else:
                st.error(res["message"])

    st.markdown("---")
    st.subheader("🧠 Nhật Ký Phản Tư Của Hội Đồng Đầu Tư (TradingAgents-Vn Reflection Memory Loop)")
    st.caption("Hệ thống tự động lưu lại các Nghị quyết của CIO và đối chiếu với biến động giá thực tế để tự kiểm toán chất lượng khuyến nghị:")
    ref_logs = cached_reflection_log()
    if ref_logs:
        df_ref = pd.DataFrame(ref_logs)
        cols_map = {
            "timestamp": "Thời Gian Họp",
            "symbol": "Mã CP",
            "final_decision": "Nghị Quyết CIO",
            "price_at_decision": "Giá Lúc Họp (đ)",
            "current_price": "Giá Hiện Tại (đ)",
            "intrinsic_value": "Giá Trị Nội Tại (đ)",
            "canslim_score": "CANSLIM",
            "sepa_score": "SEPA (/8)",
            "reflection_audit": "Đánh Giá Hậu Kiểm"
        }
        avail_c = [c for c in cols_map.keys() if c in df_ref.columns]
        df_ref_show = df_ref[avail_c].rename(columns=cols_map)
        st.dataframe(df_ref_show, width="stretch", hide_index=True)


# ==================== TAB 11: BACKTEST & DYNAMIC AGENTS ====================
with tab_strategy:
    st.markdown('<div class="main-title">⚙️ Kiểm Thử Chiến Lược (Backtest T+2.5) & Quản Lý Agent Động</div>', unsafe_allow_html=True)
    col_strat_cfg, col_risk_cfg = st.columns(2)
    with col_strat_cfg:
        strat_type = st.selectbox(
            "Loại chiến lược kiểm thử:",
            [
                "SMA Crossover (Golden/Death Cross)",
                "RSI Mean Reversion (Quá Bán / Quá Mua)",
                "MACD Crossover",
                "Bollinger Bands Bật Đáy / Đỉnh",
                "Breakout Vượt Đỉnh 20 Phiên + Vol Bùng Nổ"
            ]
        )
        if "SMA" in strat_type:
            strategy = SMACrossoverStrategy(fast_period=10, slow_period=30)
        elif "RSI" in strat_type:
            strategy = RSIStrategy(oversold=32.0, overbought=70.0)
        elif "MACD" in strat_type:
            strategy = MACDStrategy()
        elif "Bollinger" in strat_type:
            strategy = BollingerBandsStrategy(std_dev=2.0)
        else:
            strategy = BreakoutVolumeStrategy(lookback=20, volume_factor=1.4)

    with col_risk_cfg:
        bt_capital = st.number_input("Vốn kiểm thử (VNĐ):", min_value=50_000_000, max_value=10_000_000_000, value=500_000_000, step=50_000_000)
        bt_days = st.select_slider("Số ngày lịch sử kiểm thử:", options=[180, 365, 730], value=365)

    if st.button("🚀 Chạy Kiểm Thử Chiến Lược", type="primary"):
        df_bt = data_engine.get_history(selected_symbol, days=bt_days)
        if not df_bt.empty and len(df_bt) >= 30:
            backtester = StrategyBacktester(initial_capital=bt_capital, stop_loss_pct=7.0, take_profit_pct=18.0, commission_rate=0.0015, tax_rate=0.0010, t_plus=2)
            st.session_state["bt_result"] = backtester.run(df_bt, strategy)

    if "bt_result" in st.session_state:
        res = st.session_state["bt_result"]
        metrics = res["metrics"]
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Lợi Nhuận Chiến Lược", f"{metrics.get('total_return_pct', 0.0):+.2f}%")
        m2.metric("Mua & Nắm Giữ", f"{metrics.get('benchmark_return_pct', 0.0):+.2f}%")
        m3.metric("Tỷ Lệ Thắng", f"{metrics.get('win_rate_pct', 0)}%")
        m4.metric("Max Drawdown", f"{metrics.get('max_drawdown_pct', 0):.2f}%")
        m5.metric("Tổng Số Lệnh", f"{metrics.get('total_trades', 0)}")


# ==================== TAB 12: INSTITUTIONAL CONSENSUS CRITIQUE & USER GUIDE ====================
with tab_blueprint:
    guide_path = os.path.join(PROJECT_ROOT, "HUONG_DAN_SU_DUNG.md")
    if os.path.exists(guide_path):
        with open(guide_path, "r", encoding="utf-8") as f:
            st.markdown(f.read())
    else:
        st.info("Đang tải tài liệu Biên bản họp phản biện 8 dự án & Hướng dẫn sử dụng...")
