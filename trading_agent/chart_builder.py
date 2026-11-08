"""
Interactive Multi-Indicator Technical Analysis Chart Studio
Hỗ trợ người dùng thêm/bớt các chỉ báo kỹ thuật trực tiếp trên biểu đồ (Overlays & Sub-panels),
đa khung thời gian (15m, 1H, 1D, 1W, 1M), đa loại đồ thị (Candlestick, Heikin-Ashi, Line),
kèm thanh chẩn đoán tín hiệu kỹ thuật tức thời.
Đã tối ưu hóa bằng @st.fragment & @st.cache_data để phản hồi tức thời (< 0.08s) và tuyệt đối không lặp rerun.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, Any, List, Optional

from trading_agent.technical_analysis import TechnicalAnalysis


@st.cache_data(ttl=300, show_spinner=False)
def _cached_fetch_and_compute_indicators(symbol: str, interval: str, days_fetch: int, _data_engine) -> pd.DataFrame:
    """Cache dữ liệu lịch sử kèm toàn bộ chỉ báo kỹ thuật để đổi mô hình/chỉ báo phản hồi tức thì (< 0.05s)."""
    df_raw = _data_engine.get_historical_data(symbol, days=days_fetch, interval=interval)
    if df_raw is None or df_raw.empty or len(df_raw) < 15:
        return pd.DataFrame()
    df_full = TechnicalAnalysis.add_all_indicators(df_raw)
    return df_full


@st.cache_data(ttl=600, show_spinner=False)
def _cached_fetch_vnindex_daily(days_fetch: int, _data_engine) -> pd.DataFrame:
    try:
        return _data_engine.get_historical_data("VNINDEX", days=days_fetch, interval="1D")
    except Exception:
        return pd.DataFrame()


PRESET_CONFIGS = {
    "Tùy chỉnh tự do (Custom)": (
        [
            "SMA 20",
            "SMA 50",
            "SMA 200",
            "Bollinger Bands (20,2)",
            "Volume Profile (POC/VAH/VAL)",
            "Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Zone)",
            "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
        ],
        [
            "Volume + MA20",
            "MCDX RSI SMA [CongTrader] (Banker + Blue/White)",
            "RSI (14) + MA9",
            "MACD (12,26,9)",
        ],
    ),
    "Minervini SEPA & VCP (MA20/50/150/200 + Vol + RS)": (
        [
            "SMA 20",
            "SMA 50",
            "SMA 150",
            "SMA 200",
            "Kênh Đỉnh/Đáy 20P (Donchian)",
            "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
        ],
        [
            "Volume + MA20",
            "MCDX RSI SMA [CongTrader] (Banker + Blue/White)",
            "RS Line vs VN-INDEX",
            "RSI (14) + MA9",
        ],
    ),
    "Wyckoff VSA & SMC (Volume Profile + VWAP + MCDX + BUY/SELL)": (
        [
            "SMA 20",
            "SMA 50",
            "VWAP (20)",
            "Volume Profile (POC/VAH/VAL)",
            "Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Zone)",
            "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
        ],
        [
            "Volume + MA20",
            "MCDX RSI SMA [CongTrader] (Banker + Blue/White)",
            "MFI (14 - Dòng tiền)",
            "OBV (On-Balance Vol)",
        ],
    ),
    "Ichimoku & Xu Hướng (Ichimoku + ADX/DMI + MACD)": (
        [
            "Ichimoku Cloud (9,26,52)",
            "SMA 200",
            "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
        ],
        [
            "Volume + MA20",
            "ADX & DMI (+DI, -DI)",
            "MACD (12,26,9)",
        ],
    ),
    "Swing Trading & Bắt Đáy (MCDX + SMC Zone + Bollinger + RSI)": (
        [
            "SMA 20",
            "SMA 50",
            "SMA 200",
            "Bollinger Bands (20,2)",
            "Volume Profile (POC/VAH/VAL)",
            "Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Zone)",
            "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
        ],
        [
            "Volume + MA20",
            "MCDX RSI SMA [CongTrader] (Banker + Blue/White)",
            "RSI (14) + MA9",
            "Stochastic (%K, %D)",
        ],
    ),
    "VPA Order Flow & Turtle ATR (Cung Cầu + Keltner + Trailing Stop)": (
        [
            "SMA 20",
            "SMA 50",
            "Keltner Bands (20, 3*ATR)",
            "Turtle ATR Trailing Stop (Chandelier)",
            "Darvas Box (20P)",
            "Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Zone)",
            "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
        ],
        [
            "Volume + MA20",
            "Áp Lực Cung Cầu Order Flow (Buying vs Selling Pressure)",
            "MCDX RSI SMA [CongTrader] (Banker + Blue/White)",
            "Nỗ Lực vs Kết Quả (Effort vs Result - VPA)",
        ],
    ),
}


def _on_preset_change_callback(preset_key: str, ov_key: str, sub_key: str):
    """Callback cập nhật trực tiếp danh sách chỉ báo trong 1 chu kỳ duy nhất khi người dùng đổi Preset."""
    chosen = st.session_state.get(preset_key, "Tùy chỉnh tự do (Custom)")
    if chosen in PRESET_CONFIGS:
        ov_list, sub_list = PRESET_CONFIGS[chosen]
        st.session_state[ov_key] = list(ov_list)
        st.session_state[sub_key] = list(sub_list)


class InteractiveChartBuilder:
    """
    Studio Biểu Đồ Phân Tích Kỹ Thuật Đa Chỉ Báo (Tùy biến Thêm/Bớt Chỉ Báo Thời Gian Thực)
    """

    OVERLAY_OPTIONS = [
        "SMA 20",
        "SMA 50",
        "SMA 150",
        "SMA 200",
        "EMA 12 & 26",
        "Bollinger Bands (20,2)",
        "Keltner Bands (20, 3*ATR)",
        "Turtle ATR Trailing Stop (Chandelier)",
        "Darvas Box (20P)",
        "Ichimoku Cloud (9,26,52)",
        "Ichimoku VN (9,17,33 + Đao Găm 65/129)",
        "VWAP (20)",
        "Volume Profile (POC/VAH/VAL)",
        "Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Zone)",
        "Kênh Đỉnh/Đáy 20P (Donchian)",
        "Mức Cắt Lỗ & Chốt Lời (SL/TP)",
    ]

    SUBPANEL_OPTIONS = [
        "Volume + MA20",
        "Áp Lực Cung Cầu Order Flow (Buying vs Selling Pressure)",
        "Nỗ Lực vs Kết Quả (Effort vs Result - VPA)",
        "MCDX RSI SMA [CongTrader] (Banker + Blue/White)",
        "RSI (14) + MA9",
        "MACD (12,26,9)",
        "Stochastic (%K, %D)",
        "ADX & DMI (+DI, -DI)",
        "MFI (14 - Dòng tiền)",
        "OBV (On-Balance Vol)",
        "RS Line vs VN-INDEX",
    ]

    TIMEFRAME_MAP = {
        "Ngày (1D)": ("1D", 450),
        "Tuần (1W)": ("1W", 1500),
        "Tháng (1M)": ("1M", 2500),
        "1 Giờ (1H)": ("1H", 60),
        "15 Phút (15m)": ("15m", 25),
    }

    @classmethod
    @st.fragment
    def render_customizable_chart(
        cls,
        symbol: str,
        data_engine,
        tech_report: Optional[Dict[str, Any]] = None,
        key_prefix: str = "chart_studio",
        default_overlays: Optional[List[str]] = None,
        default_subpanels: Optional[List[str]] = None,
        compact: bool = False,
    ):
        """
        Render bộ điều khiển chọn chỉ báo (Thêm/Bớt trực quan) và vẽ biểu đồ kỹ thuật đa tầng Plotly.
        Chạy trong @st.fragment độc lập để khi đổi mô hình phân tích kỹ thuật / chỉ báo sẽ phản hồi tức thì (< 0.08s)
        mà không phải tải lại toàn bộ trang.
        """
        symbol = symbol.upper().strip()
        if default_overlays is None:
            default_overlays = list(PRESET_CONFIGS["Tùy chỉnh tự do (Custom)"][0])
        if default_subpanels is None:
            default_subpanels = list(PRESET_CONFIGS["Tùy chỉnh tự do (Custom)"][1])

        st.markdown(
            f"""
            <div style="background:linear-gradient(90deg,#0f172a,#1e293b);padding:12px 18px;border-radius:10px;border-left:4px solid #38bdf8;margin-bottom:10px;">
                <span style="font-size:1.08rem;font-weight:700;color:#f8fafc;">📈 STUDIO BIỂU ĐỒ KỸ THUẬT ĐA CHỈ BÁO: <span style="color:#38bdf8;">{symbol}</span></span>
                <span style="font-size:0.85rem;color:#94a3b8;margin-left:12px;">(Đổi mô hình Preset hoặc Click chọn/bỏ chọn để thêm/bớt chỉ báo tức thì)</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Sử dụng key cố định theo key_prefix để không bao giờ gây hủy/tạo lại widget lặp vô tận
        tf_key = f"{key_prefix}_tf"
        ctype_key = f"{key_prefix}_ctype"
        lb_key = f"{key_prefix}_lb"
        preset_key = f"{key_prefix}_preset"
        ov_key = f"{key_prefix}_ov"
        sub_key = f"{key_prefix}_sub"

        if ov_key not in st.session_state:
            st.session_state[ov_key] = list(default_overlays)
        if sub_key not in st.session_state:
            st.session_state[sub_key] = list(default_subpanels)

        # Bộ điều khiển cấu hình biểu đồ
        c1, c2, c3, c4 = st.columns([1.2, 1.4, 1.1, 1.8])
        with c1:
            tf_label = st.selectbox(
                "⏱️ Khung Thời Gian:",
                list(cls.TIMEFRAME_MAP.keys()),
                index=0,
                key=tf_key,
            )
        with c2:
            chart_type = st.selectbox(
                "🕯️ Loại Đồ Thị:",
                ["Nến Nhật (Candlestick)", "Heikin-Ashi (Xu hướng mượt)", "Đường Giá (Line)"],
                index=0,
                key=ctype_key,
            )
        with c3:
            lookback = st.selectbox(
                "🔍 Số Phiên:",
                [80, 130, 200, 300, 500],
                index=1 if not compact else 0,
                key=lb_key,
            )
        with c4:
            st.selectbox(
                "⚡ Bộ Mẫu Mô Hình Phân Tích Kỹ Thuật (Preset):",
                list(PRESET_CONFIGS.keys()),
                index=0,
                key=preset_key,
                on_change=_on_preset_change_callback,
                args=(preset_key, ov_key, sub_key),
            )

        ov_col, sub_col = st.columns(2)
        with ov_col:
            selected_overlays = st.multiselect(
                "📌 Thêm / Bớt Chỉ Báo Trên Biểu Đồ Giá (Overlays):",
                options=cls.OVERLAY_OPTIONS,
                key=ov_key,
            )
        with sub_col:
            selected_subpanels = st.multiselect(
                "📊 Thêm / Bớt Chỉ Báo Dao Động Tầng Dưới (Sub-panels):",
                options=cls.SUBPANEL_OPTIONS,
                key=sub_key,
            )

        interval, days_fetch = cls.TIMEFRAME_MAP.get(tf_label, ("1D", 450))
        df_full = _cached_fetch_and_compute_indicators(symbol, interval, days_fetch, data_engine)
        if df_full is None or df_full.empty or len(df_full) < 15:
            st.warning(f"Không đủ dữ liệu lịch sử cho mã `{symbol}` ở khung `{tf_label}`.")
            return

        df = df_full.tail(min(int(lookback), len(df_full))).copy()

        # Lấy thêm VNINDEX nếu chọn RS Line
        vnindex_df = None
        if "RS Line vs VN-INDEX" in selected_subpanels:
            vnindex_df = _cached_fetch_vnindex_daily(days_fetch, data_engine)

        # Xây dựng cấu trúc Subplots linh hoạt theo số lượng sub-panels người dùng chọn
        n_sub = len(selected_subpanels)
        total_rows = 1 + n_sub

        if n_sub == 0:
            row_heights = [1.0]
        elif n_sub == 1:
            row_heights = [0.72, 0.28]
        elif n_sub == 2:
            row_heights = [0.58, 0.21, 0.21]
        elif n_sub == 3:
            row_heights = [0.50, 0.16, 0.17, 0.17]
        else:
            main_h = 0.44
            sub_h = round((1.0 - main_h) / n_sub, 3)
            row_heights = [main_h] + [sub_h] * n_sub

        subplot_titles = [f"{symbol} ({tf_label}) — {chart_type.split(' ')[0]}"] + selected_subpanels

        fig = make_subplots(
            rows=total_rows,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.025,
            row_heights=row_heights,
            subplot_titles=subplot_titles,
        )

        # 1. VẼ ĐỒ THỊ GIÁ CHÍNH (ROW 1)
        if chart_type.startswith("Heikin-Ashi") and "HA_Open" in df.columns:
            fig.add_trace(
                go.Candlestick(
                    x=df["time"],
                    open=df["HA_Open"],
                    high=df["HA_High"],
                    low=df["HA_Low"],
                    close=df["HA_Close"],
                    name="Heikin-Ashi",
                    increasing_line_color="#10b981",
                    decreasing_line_color="#ef4444",
                ),
                row=1,
                col=1,
            )
        elif chart_type.startswith("Đường Giá"):
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["close"],
                    mode="lines",
                    name="Giá Đóng Cửa",
                    line=dict(color="#38bdf8", width=2.2),
                    fill="tozeroy",
                    fillcolor="rgba(56, 189, 248, 0.08)",
                ),
                row=1,
                col=1,
            )
        else:
            fig.add_trace(
                go.Candlestick(
                    x=df["time"],
                    open=df["open"],
                    high=df["high"],
                    low=df["low"],
                    close=df["close"],
                    name="Giá OHLC",
                    increasing_line_color="#10b981",
                    decreasing_line_color="#ef4444",
                ),
                row=1,
                col=1,
            )

        # 2. VẼ CÁC CHỈ BÁO OVERLAY TRÊN BIỂU ĐỒ GIÁ
        if "SMA 20" in selected_overlays and "SMA_20" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["SMA_20"],
                    name="SMA 20",
                    line=dict(color="#38bdf8", width=1.4),
                ),
                row=1,
                col=1,
            )
        if "SMA 50" in selected_overlays and "SMA_50" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["SMA_50"],
                    name="SMA 50",
                    line=dict(color="#f59e0b", width=1.7),
                ),
                row=1,
                col=1,
            )
        if "SMA 150" in selected_overlays and "SMA_150" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["SMA_150"],
                    name="SMA 150",
                    line=dict(color="#ec4899", width=1.6, dash="dot"),
                ),
                row=1,
                col=1,
            )
        if "SMA 200" in selected_overlays and "SMA_200" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["SMA_200"],
                    name="SMA 200",
                    line=dict(color="#a855f7", width=2.1),
                ),
                row=1,
                col=1,
            )
        if "EMA 12 & 26" in selected_overlays:
            if "EMA_12" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["EMA_12"],
                        name="EMA 12",
                        line=dict(color="#22d3ee", width=1.3, dash="dash"),
                    ),
                    row=1,
                    col=1,
                )
            if "EMA_26" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["EMA_26"],
                        name="EMA 26",
                        line=dict(color="#fb923c", width=1.4, dash="dash"),
                    ),
                    row=1,
                    col=1,
                )
        if "VWAP (20)" in selected_overlays and "VWAP_20" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["VWAP_20"],
                    name="VWAP (20)",
                    line=dict(color="#fde047", width=1.8, dash="dashdot"),
                ),
                row=1,
                col=1,
            )
        if "Bollinger Bands (20,2)" in selected_overlays and "BB_High" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["BB_High"],
                    name="BB Upper",
                    line=dict(color="rgba(148, 163, 184, 0.55)", width=1.1, dash="dot"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["BB_Low"],
                    name="BB Lower",
                    line=dict(color="rgba(148, 163, 184, 0.55)", width=1.1, dash="dot"),
                    fill="tonexty",
                    fillcolor="rgba(148, 163, 184, 0.07)",
                ),
                row=1,
                col=1,
            )
        if "Ichimoku Cloud (9,26,52)" in selected_overlays and "Ichi_Tenkan" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Ichi_Tenkan"],
                    name="Tenkan-sen (9)",
                    line=dict(color="#38bdf8", width=1.2),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Ichi_Kijun"],
                    name="Kijun-sen (26)",
                    line=dict(color="#f43f5e", width=1.4),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Ichi_SpanA"],
                    name="Senkou Span A",
                    line=dict(color="rgba(16, 185, 129, 0.5)", width=1.0),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Ichi_SpanB"],
                    name="Senkou Span B (Kumo)",
                    line=dict(color="rgba(239, 68, 68, 0.5)", width=1.0),
                    fill="tonexty",
                    fillcolor="rgba(16, 185, 129, 0.10)",
                ),
                row=1,
                col=1,
            )
        if "Keltner Bands (20, 3*ATR)" in selected_overlays and "Keltner_Upper" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Keltner_Upper"],
                    name="Keltner Upper (3 ATR)",
                    line=dict(color="#38bdf8", width=1.1, dash="dash"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Keltner_Lower"],
                    name="Keltner Lower (3 ATR)",
                    line=dict(color="#38bdf8", width=1.1, dash="dash"),
                    fill="tonexty",
                    fillcolor="rgba(56, 189, 248, 0.05)",
                ),
                row=1,
                col=1,
            )
            if "Keltner_Mid" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Keltner_Mid"],
                        name="Keltner EMA20",
                        line=dict(color="#fde047", width=1.2, dash="dot"),
                    ),
                    row=1,
                    col=1,
                )
        if "Turtle ATR Trailing Stop (Chandelier)" in selected_overlays and "Chand_Stop_Long" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Chand_Stop_Long"],
                    name="Turtle Trailing Stop Long",
                    line=dict(color="#22c55e", width=1.4, dash="dashdot"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Chand_Stop_Short"],
                    name="Turtle Trailing Stop Short",
                    line=dict(color="#ef4444", width=1.4, dash="dashdot"),
                ),
                row=1,
                col=1,
            )
        if "Darvas Box (20P)" in selected_overlays and "Darvas_Top" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Darvas_Top"],
                    name="Hộp Darvas (Top)",
                    line=dict(color="#c084fc", width=1.3),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Darvas_Bottom"],
                    name="Hộp Darvas (Bottom)",
                    line=dict(color="#818cf8", width=1.3),
                    fill="tonexty",
                    fillcolor="rgba(192, 132, 252, 0.05)",
                ),
                row=1,
                col=1,
            )
        if "Ichimoku VN (9,17,33 + Đao Găm 65/129)" in selected_overlays:
            if "Ichi_Kijun_VN" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Ichi_Kijun_VN"],
                        name="Kijun VN (17)",
                        line=dict(color="#06b6d4", width=1.3),
                    ),
                    row=1,
                    col=1,
                )
            if "Ichi_DaoGam_65" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Ichi_DaoGam_65"],
                        name="Đao Găm 65 (Hỗ trợ trung hạn)",
                        line=dict(color="#eab308", width=1.8),
                    ),
                    row=1,
                    col=1,
                )
            if "Ichi_DaoGam_129" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Ichi_DaoGam_129"],
                        name="Đao Găm 129 (Hỗ trợ dài hạn)",
                        line=dict(color="#f97316", width=2.0, dash="dash"),
                    ),
                    row=1,
                    col=1,
                )
        if "Kênh Đỉnh/Đáy 20P (Donchian)" in selected_overlays and "Donchian_High_20" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Donchian_High_20"],
                    name="Đỉnh 20P (Breakout)",
                    line=dict(color="#10b981", width=1.1, dash="dot"),
                ),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df["Donchian_Low_20"],
                    name="Đáy 20P (Support)",
                    line=dict(color="#ef4444", width=1.1, dash="dot"),
                ),
                row=1,
                col=1,
            )

        # Volume Profile (POC / VAH / VAL)
        if "Volume Profile (POC/VAH/VAL)" in selected_overlays:
            poc, vah, val_price = cls._compute_volume_profile_levels(df, tech_report)
            if poc > 0:
                fig.add_hline(
                    y=poc,
                    line_dash="dash",
                    line_color="#facc15",
                    line_width=1.8,
                    annotation_text=f"POC: {poc:,.0f}",
                    annotation_position="top left",
                    row=1,
                    col=1,
                )
            if vah > 0:
                fig.add_hline(
                    y=vah,
                    line_dash="dot",
                    line_color="#34d399",
                    line_width=1.2,
                    annotation_text=f"VAH: {vah:,.0f}",
                    annotation_position="top right",
                    row=1,
                    col=1,
                )
            if val_price > 0:
                fig.add_hline(
                    y=val_price,
                    line_dash="dot",
                    line_color="#fb7185",
                    line_width=1.2,
                    annotation_text=f"VAL: {val_price:,.0f}",
                    annotation_position="bottom right",
                    row=1,
                    col=1,
                )

        # Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Premium/Discount Zone)
        if "Tín Hiệu Bắt Đáy/Đỉnh (BUY/SELL TP-SL & SMC Zone)" in selected_overlays:
            if "SMC_High_60" in df.columns and "SMC_Low_60" in df.columns:
                smc_h = float(df["SMC_High_60"].iloc[-1])
                smc_l = float(df["SMC_Low_60"].iloc[-1])
                if smc_h > smc_l > 0:
                    prem_bottom = smc_h - 0.22 * (smc_h - smc_l)
                    disc_top = smc_l + 0.30 * (smc_h - smc_l)
                    fig.add_hrect(
                        y0=prem_bottom,
                        y1=smc_h,
                        fillcolor="rgba(239, 68, 68, 0.10)",
                        line_width=1,
                        line_dash="dot",
                        line_color="rgba(239, 68, 68, 0.45)",
                        annotation_text=f"SMC PREMIUM (Cung Đỉnh: {prem_bottom:,.0f}-{smc_h:,.0f})",
                        annotation_position="top right",
                        row=1,
                        col=1,
                    )
                    fig.add_hrect(
                        y0=smc_l,
                        y1=disc_top,
                        fillcolor="rgba(16, 185, 129, 0.10)",
                        line_width=1,
                        line_dash="dot",
                        line_color="rgba(16, 185, 129, 0.45)",
                        annotation_text=f"SMC DISCOUNT (Cầu Đáy: {smc_l:,.0f}-{disc_top:,.0f})",
                        annotation_position="bottom right",
                        row=1,
                        col=1,
                    )

            if "Buy_Bottom_Signal" in df.columns:
                buy_df = df[df["Buy_Bottom_Signal"] == True]
                if not buy_df.empty:
                    buy_labels = [
                        f"▲ BUY / LPS<br>TP: {c * 1.12:,.0f}<br>SL: {l * 0.96:,.0f}"
                        for c, l in zip(buy_df["close"], buy_df["low"])
                    ]
                    fig.add_trace(
                        go.Scatter(
                            x=buy_df["time"],
                            y=buy_df["low"] * 0.985,
                            mode="markers+text",
                            name="▲ BUY (Đáy/LPS)",
                            text=["▲ BUY/LPS"] * len(buy_df),
                            textposition="bottom center",
                            textfont=dict(color="#10b981", size=10),
                            hovertext=buy_labels,
                            hoverinfo="text+x",
                            marker=dict(symbol="triangle-up", size=13, color="#10b981", line=dict(width=1, color="#ffffff")),
                        ),
                        row=1,
                        col=1,
                    )

            if "Sell_Top_Signal" in df.columns:
                sell_df = df[df["Sell_Top_Signal"] == True]
                if not sell_df.empty:
                    sell_labels = [
                        f"▼ SELL / LPSY<br>TP: {c * 0.91:,.0f}<br>SL: {h * 1.03:,.0f}"
                        for c, h in zip(sell_df["close"], sell_df["high"])
                    ]
                    fig.add_trace(
                        go.Scatter(
                            x=sell_df["time"],
                            y=sell_df["high"] * 1.015,
                            mode="markers+text",
                            name="▼ SELL (Đỉnh/LPSY)",
                            text=["▼ SELL/LPSY"] * len(sell_df),
                            textposition="top center",
                            textfont=dict(color="#ef4444", size=10),
                            hovertext=sell_labels,
                            hoverinfo="text+x",
                            marker=dict(symbol="triangle-down", size=13, color="#ef4444", line=dict(width=1, color="#ffffff")),
                        ),
                        row=1,
                        col=1,
                    )

        # Mức Cắt Lỗ & Chốt Lời (SL / TP)
        if "Mức Cắt Lỗ & Chốt Lời (SL/TP)" in selected_overlays:
            last_close = float(df["close"].iloc[-1])
            atr_now = float(df["ATR_14"].iloc[-1]) if "ATR_14" in df.columns and not pd.isna(df["ATR_14"].iloc[-1]) else last_close * 0.03
            sl_price = (
                float(tech_report["trade_plan"]["stop_loss"])
                if tech_report and tech_report.get("trade_plan", {}).get("stop_loss", 0) > 0
                else round(last_close - 2.0 * atr_now, 0)
            )
            tp1_price = (
                float(tech_report["trade_plan"]["target_1"])
                if tech_report and tech_report.get("trade_plan", {}).get("target_1", 0) > 0
                else round(last_close + 3.0 * atr_now, 0)
            )
            fig.add_hline(
                y=sl_price,
                line_dash="dashdot",
                line_color="#ef4444",
                line_width=1.4,
                annotation_text=f"Stop Loss: {sl_price:,.0f}",
                annotation_position="bottom left",
                row=1,
                col=1,
            )
            fig.add_hline(
                y=tp1_price,
                line_dash="dashdot",
                line_color="#10b981",
                line_width=1.4,
                annotation_text=f"Target 1: {tp1_price:,.0f}",
                annotation_position="top left",
                row=1,
                col=1,
            )

        # 3. VẼ CÁC SUB-PANELS TẦNG DƯỚI THEO LỰA CHỌN CỦA NGƯỜI DÙNG
        for idx, panel_name in enumerate(selected_subpanels):
            row_idx = idx + 2

            if panel_name == "Volume + MA20":
                vol_colors = [
                    "#10b981" if c >= o else "#ef4444"
                    for c, o in zip(df["close"], df["open"])
                ]
                fig.add_trace(
                    go.Bar(
                        x=df["time"],
                        y=df["volume"],
                        name="Volume",
                        marker_color=vol_colors,
                        opacity=0.85,
                    ),
                    row=row_idx,
                    col=1,
                )
                if "Vol_SMA_20" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["time"],
                            y=df["Vol_SMA_20"],
                            name="Vol MA20",
                            line=dict(color="#facc15", width=1.5),
                        ),
                        row=row_idx,
                        col=1,
                    )

            elif panel_name == "Áp Lực Cung Cầu Order Flow (Buying vs Selling Pressure)" and "Buying_Pressure" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Buying_Pressure"],
                        name="Lực Cầu (Buying %)",
                        line=dict(color="#10b981", width=2.0),
                        fill="tozeroy",
                        fillcolor="rgba(16, 185, 129, 0.12)",
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Selling_Pressure"],
                        name="Lực Cung (Selling %)",
                        line=dict(color="#ef4444", width=2.0),
                        fill="tozeroy",
                        fillcolor="rgba(239, 68, 68, 0.12)",
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_hline(y=50, line_dash="dash", line_color="#94a3b8", row=row_idx, col=1)
                fig.update_yaxes(range=[0, 105], row=row_idx, col=1)

            elif panel_name == "Nỗ Lực vs Kết Quả (Effort vs Result - VPA)" and "Effort_Score" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Effort_Score"],
                        name="Effort (Nỗ lực Vol)",
                        line=dict(color="#818cf8", width=1.8),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Result_Score"],
                        name="Result (Kết quả Giá)",
                        line=dict(color="#2dd4bf", width=1.8),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_hline(y=50, line_dash="dash", line_color="#94a3b8", row=row_idx, col=1)
                fig.update_yaxes(range=[0, 105], row=row_idx, col=1)

            elif panel_name == "MCDX RSI SMA [CongTrader] (Banker + Blue/White)" and "MCDX_Banker" in df.columns:
                fig.add_trace(
                    go.Bar(
                        x=df["time"],
                        y=pd.Series(20.0, index=df.index),
                        name="MCDX Retail (Nhỏ lẻ)",
                        marker_color="rgba(250, 204, 21, 0.30)",
                        hoverinfo="skip",
                    ),
                    row=row_idx,
                    col=1,
                )
                if "MCDX_Hot" in df.columns:
                    fig.add_trace(
                        go.Bar(
                            x=df["time"],
                            y=df["MCDX_Hot"],
                            name="MCDX Hot Money (Đầu cơ)",
                            marker_color="rgba(245, 158, 11, 0.45)",
                        ),
                        row=row_idx,
                        col=1,
                    )
                banker_colors = [
                    "#10b981" if b >= s else "#ef4444"
                    for b, s in zip(df["MCDX_Banker"].fillna(0), df["MCDX_Banker_SMA36"].fillna(0))
                ]
                fig.add_trace(
                    go.Bar(
                        x=df["time"],
                        y=df["MCDX_Banker"],
                        name="MCDX Banker (Tạo lập)",
                        marker_color=banker_colors,
                        opacity=0.92,
                    ),
                    row=row_idx,
                    col=1,
                )
                if "MCDX_Banker_SMA36" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["time"],
                            y=df["MCDX_Banker_SMA36"],
                            name="Banker SMA(36)",
                            line=dict(color="#d946ef", width=1.8),
                        ),
                        row=row_idx,
                        col=1,
                    )
                if "MCDX_Fast" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["time"],
                            y=df["MCDX_Fast"],
                            name="MCDX Fast (Blue)",
                            line=dict(color="#3b82f6", width=2.2),
                        ),
                        row=row_idx,
                        col=1,
                    )
                if "MCDX_Slow" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["time"],
                            y=df["MCDX_Slow"],
                            name="MCDX Slow (White)",
                            line=dict(color="#f8fafc", width=1.5),
                        ),
                        row=row_idx,
                        col=1,
                    )
                fig.add_hline(y=15, line_dash="dot", line_color="#10b981", row=row_idx, col=1)
                fig.add_hline(y=10, line_dash="dot", line_color="#64748b", row=row_idx, col=1)
                fig.add_hline(y=5, line_dash="dot", line_color="#ef4444", row=row_idx, col=1)
                fig.update_yaxes(range=[0, 20.5], row=row_idx, col=1)

            elif panel_name == "RSI (14) + MA9" and "RSI_14" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["RSI_14"],
                        name="RSI (14)",
                        line=dict(color="#38bdf8", width=1.7),
                    ),
                    row=row_idx,
                    col=1,
                )
                if "RSI_MA9" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["time"],
                            y=df["RSI_MA9"],
                            name="RSI MA(9)",
                            line=dict(color="#f59e0b", width=1.2, dash="dot"),
                        ),
                        row=row_idx,
                        col=1,
                    )
                fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=row_idx, col=1)
                fig.add_hline(y=50, line_dash="dot", line_color="#64748b", row=row_idx, col=1)
                fig.add_hline(y=30, line_dash="dot", line_color="#10b981", row=row_idx, col=1)

            elif panel_name == "MACD (12,26,9)" and "MACD" in df.columns:
                hist_colors = ["#10b981" if v >= 0 else "#ef4444" for v in df["MACD_Hist"].fillna(0)]
                fig.add_trace(
                    go.Bar(
                        x=df["time"],
                        y=df["MACD_Hist"],
                        name="MACD Hist",
                        marker_color=hist_colors,
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["MACD"],
                        name="MACD",
                        line=dict(color="#38bdf8", width=1.5),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["MACD_Signal"],
                        name="Signal (9)",
                        line=dict(color="#f97316", width=1.4),
                    ),
                    row=row_idx,
                    col=1,
                )

            elif panel_name == "Stochastic (%K, %D)" and "Stoch_K" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Stoch_K"],
                        name="Stoch %K (14)",
                        line=dict(color="#38bdf8", width=1.5),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["Stoch_D"],
                        name="Stoch %D (3)",
                        line=dict(color="#f97316", width=1.3, dash="dot"),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_hline(y=80, line_dash="dot", line_color="#ef4444", row=row_idx, col=1)
                fig.add_hline(y=20, line_dash="dot", line_color="#10b981", row=row_idx, col=1)

            elif panel_name == "ADX & DMI (+DI, -DI)" and "ADX_14" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["ADX_14"],
                        name="ADX (14)",
                        line=dict(color="#facc15", width=2.0),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["DI_Plus"],
                        name="+DI",
                        line=dict(color="#10b981", width=1.3),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["DI_Minus"],
                        name="-DI",
                        line=dict(color="#ef4444", width=1.3),
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_hline(y=25, line_dash="dot", line_color="#94a3b8", annotation_text="Trend > 25", row=row_idx, col=1)

            elif panel_name == "MFI (14 - Dòng tiền)" and "MFI_14" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["MFI_14"],
                        name="MFI (14)",
                        line=dict(color="#c084fc", width=1.7),
                        fill="tozeroy",
                        fillcolor="rgba(192, 132, 252, 0.08)",
                    ),
                    row=row_idx,
                    col=1,
                )
                fig.add_hline(y=80, line_dash="dot", line_color="#ef4444", row=row_idx, col=1)
                fig.add_hline(y=20, line_dash="dot", line_color="#10b981", row=row_idx, col=1)

            elif panel_name == "OBV (On-Balance Vol)" and "OBV" in df.columns:
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=df["OBV"],
                        name="OBV",
                        line=dict(color="#22d3ee", width=1.6),
                    ),
                    row=row_idx,
                    col=1,
                )
                if "OBV_SMA20" in df.columns:
                    fig.add_trace(
                        go.Scatter(
                            x=df["time"],
                            y=df["OBV_SMA20"],
                            name="OBV MA20",
                            line=dict(color="#f59e0b", width=1.2, dash="dot"),
                        ),
                        row=row_idx,
                        col=1,
                    )

            elif panel_name == "RS Line vs VN-INDEX":
                rs_series = cls._compute_rs_line(df, vnindex_df)
                fig.add_trace(
                    go.Scatter(
                        x=df["time"],
                        y=rs_series,
                        name="RS Line (CP / VNINDEX)",
                        line=dict(color="#ec4899", width=1.8),
                    ),
                    row=row_idx,
                    col=1,
                )

        chart_height = max(560, 380 + n_sub * 155) if not compact else max(480, 320 + n_sub * 130)
        fig.update_layout(
            template="plotly_dark",
            height=chart_height,
            barmode="overlay",
            xaxis_rangeslider_visible=False,
            margin=dict(l=12, r=12, t=35, b=12),
            legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="left", x=0),
            hovermode="x unified",
        )

        st.plotly_chart(fig, width="stretch", key=f"{key_prefix}_plotly")

        # 4. THANH TỔNG HỢP TÍN HIỆU CHỈ BÁO TỨC THỜI (INSTANT INDICATOR MATRIX)
        cls._render_indicator_signal_strip(df, symbol)

    @staticmethod
    def _compute_volume_profile_levels(df: pd.DataFrame, tech_report: Optional[Dict[str, Any]] = None):
        if tech_report and tech_report.get("volume_profile"):
            vp = tech_report["volume_profile"]
            poc = float(vp.get("poc", 0))
            vah = float(vp.get("vah", 0))
            val_p = float(vp.get("val", 0))
            if poc > 0:
                return poc, vah, val_p

        try:
            prices = (df["high"] + df["low"] + df["close"]) / 3.0
            vols = df["volume"].values
            min_p, max_p = float(df["low"].min()), float(df["high"].max())
            if max_p <= min_p:
                return 0.0, 0.0, 0.0
            bins = np.linspace(min_p, max_p, 25)
            hist_vol = np.zeros(len(bins) - 1)
            for p, v in zip(prices, vols):
                idx = min(max(int((p - min_p) / (max_p - min_p) * (len(bins) - 2)), 0), len(bins) - 2)
                hist_vol[idx] += v
            poc_idx = int(np.argmax(hist_vol))
            poc = round((bins[poc_idx] + bins[poc_idx + 1]) / 2.0, 0)
            total_v = np.sum(hist_vol)
            target_v = total_v * 0.70
            cur_v = hist_vol[poc_idx]
            low_i, high_i = poc_idx, poc_idx
            while cur_v < target_v and (low_i > 0 or high_i < len(hist_vol) - 1):
                v_down = hist_vol[low_i - 1] if low_i > 0 else -1
                v_up = hist_vol[high_i + 1] if high_i < len(hist_vol) - 1 else -1
                if v_up >= v_down and high_i < len(hist_vol) - 1:
                    high_i += 1
                    cur_v += hist_vol[high_i]
                elif low_i > 0:
                    low_i -= 1
                    cur_v += hist_vol[low_i]
                else:
                    break
            val_p = round(bins[low_i], 0)
            vah = round(bins[high_i + 1], 0)
            return poc, vah, val_p
        except Exception:
            return 0.0, 0.0, 0.0

    @staticmethod
    def _compute_rs_line(df: pd.DataFrame, vnindex_df: Optional[pd.DataFrame]) -> pd.Series:
        if vnindex_df is None or vnindex_df.empty:
            base = float(df["close"].iloc[0]) if len(df) > 0 and df["close"].iloc[0] > 0 else 1.0
            return (df["close"] / base) * 100.0
        try:
            v_map = vnindex_df.set_index(pd.to_datetime(vnindex_df["time"]).dt.date)["close"].to_dict()
            dates = pd.to_datetime(df["time"]).dt.date
            v_vals = [v_map.get(d, np.nan) for d in dates]
            v_series = pd.Series(v_vals, index=df.index).ffill().bfill()
            ratio = df["close"] / v_series.replace(0, np.nan)
            first_valid = ratio.dropna().iloc[0] if not ratio.dropna().empty else 1.0
            return ((ratio / first_valid) * 100.0).fillna(100.0)
        except Exception:
            return pd.Series(100.0, index=df.index)

    @staticmethod
    def _render_indicator_signal_strip(df: pd.DataFrame, symbol: str):
        if df is None or df.empty:
            return
        last = df.iloc[-1]
        close = float(last.get("close", 0))
        sma20 = float(last.get("SMA_20", close))
        sma50 = float(last.get("SMA_50", close))
        sma200 = float(last.get("SMA_200", close))
        rsi = float(last.get("RSI_14", 50)) if not pd.isna(last.get("RSI_14", np.nan)) else 50.0
        will_r = float(last.get("Williams_R", -50)) if not pd.isna(last.get("Williams_R", np.nan)) else -50.0
        mcdx_b = float(last.get("MCDX_Banker", 0)) if not pd.isna(last.get("MCDX_Banker", np.nan)) else 0.0
        mcdx_b36 = float(last.get("MCDX_Banker_SMA36", 0)) if not pd.isna(last.get("MCDX_Banker_SMA36", np.nan)) else 0.0
        mcdx_fast = float(last.get("MCDX_Fast", 10)) if not pd.isna(last.get("MCDX_Fast", np.nan)) else 10.0
        mcdx_slow = float(last.get("MCDX_Slow", 10)) if not pd.isna(last.get("MCDX_Slow", np.nan)) else 10.0
        smc_pos = float(last.get("SMC_Pos_Pct", 50)) if not pd.isna(last.get("SMC_Pos_Pct", np.nan)) else 50.0
        vol_ratio = (
            float(last.get("volume", 0)) / float(last.get("Vol_SMA_20", 1))
            if float(last.get("Vol_SMA_20", 0)) > 0
            else 1.0
        )

        if close > sma20 and sma20 >= sma50:
            ma_title = "TĂNG"
            ma_state = f"Giá > MA20 ({sma20:,.0f})"
        elif close < sma20 and close >= sma50:
            ma_title = "GÃY MA20"
            ma_state = f"Dưới MA20 ({sma20:,.0f})"
        elif close < sma20 and close < sma50:
            ma_title = "GIẢM"
            ma_state = f"Dưới MA20 & MA50 ({sma50:,.0f})"
        else:
            ma_title = "TÍCH LŨY"
            ma_state = f"MA50: {sma50:,.0f}"

        banker_state = "Tạo lập Gom (>SMA36)" if mcdx_b >= mcdx_b36 and mcdx_b >= 5.0 else "Dòng tiền Rút (<SMA36)"
        fast_state = "Blue cắt lên White" if mcdx_fast >= mcdx_slow else "Blue lao dốc (<White)"
        smc_zone = "Discount (Cầu Đáy)" if smc_pos <= 35.0 else ("Premium (Cung Đỉnh)" if smc_pos >= 70.0 else "Equilibrium (Giữa)")
        vol_state = f"{vol_ratio:.2f}x TB20"

        bp_val = float(last.get("Buying_Pressure", 50)) if not pd.isna(last.get("Buying_Pressure", np.nan)) else 50.0
        sp_val = float(last.get("Selling_Pressure", 50)) if not pd.isna(last.get("Selling_Pressure", np.nan)) else 50.0
        order_flow_state = "Cầu áp đảo 🟢" if bp_val > sp_val * 1.15 else ("Cung áp đảo 🔴" if sp_val > bp_val * 1.15 else "Cân bằng 🟡")

        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        m1.metric("📐 Cấu Trúc MA", ma_title, ma_state)
        m2.metric("🏦 MCDX Banker", f"{mcdx_b:.1f} / {mcdx_b36:.1f}", banker_state)
        m3.metric("🔵 MCDX Blue/White", f"{mcdx_fast:.1f} / {mcdx_slow:.1f}", fast_state)
        m4.metric("🧱 Vùng SMC 60D", f"{smc_pos:.0f}%", smc_zone)
        m5.metric("⚖️ Lực Cầu/Cung", f"{bp_val:.0f}% / {sp_val:.0f}%", order_flow_state)
        m6.metric("⚡ RSI(14) & %R", f"{rsi:.1f}", f"%R: {will_r:.0f}")
        m7.metric("📊 Khối Lượng", vol_state, f"MA200: {sma200:,.0f}")
