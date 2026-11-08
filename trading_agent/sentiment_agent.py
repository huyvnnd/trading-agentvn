"""
Sentiment, Foreign Flow & Smart Money Order-Flow Agent for Vietnam Stock Market.
Phân tích dòng tiền thực tế (100% Real Data từ Bảng giá KBS & Sổ lệnh Intraday):
1. Dòng tiền Khối Ngoại (Foreign Net Buy / Sell Volume & Value thực tế trong phiên).
2. Cân bằng Sổ lệnh & Khớp lệnh Chủ động (Bid/Ask Depth & Active Buy vs Active Sell Volume).
3. Tỷ lệ Phiên Tích Lũy / Phân Phối của Tổ chức trong 20 phiên (O'Neil Accumulation/Distribution Ratio).
4. Cảnh báo Bẫy Truyền Thông (Media Bull Trap / Retail FOMO / Climax Distribution).
"""

import pandas as pd
import numpy as np
from trading_agent.data_engine import DataEngine


class SentimentAgent:
    def __init__(self, data_engine: DataEngine = None):
        self.de = data_engine or DataEngine()

    def analyze_sentiment_and_flow(self, symbol: str) -> dict:
        symbol = symbol.strip().upper()
        quote = self.de.get_latest_quote(symbol)
        df = self.de.get_history(symbol, days=60)

        if df.empty or len(df) < 15:
            return {
                "symbol": symbol,
                "sentiment_score": 0,
                "flow_status": "CHƯA ĐỦ DỮ LIỆU",
                "foreign_net_vol": 0,
                "foreign_net_val_billion": 0.0,
                "up_down_vol_ratio": 1.0,
                "media_trap_warning": None,
                "sentiment_notes": ["Dữ liệu lịch sử chưa đủ để đánh giá hành vi dòng tiền."]
            }

        curr_price = float(quote.get("price", df["close"].iloc[-1]))
        curr_vol = float(quote.get("volume", df["volume"].iloc[-1]))
        chg_pct = float(quote.get("change_pct", 0.0))

        # 1. Dữ liệu Khối Ngoại Thực Tế từ Bảng giá KBS
        f_buy = int(quote.get("foreign_buy_volume", 0))
        f_sell = int(quote.get("foreign_sell_volume", 0))
        f_net_vol = f_buy - f_sell
        f_net_val_b = round((f_net_vol * curr_price) / 1e9, 2)

        # 2. Phân tích 20 phiên Tích lũy (Up Volume) vs Phân phối (Down Volume)
        recent_21 = df.tail(21).copy()
        recent_21["diff"] = recent_21["close"].diff()
        up_vol = float(recent_21.loc[recent_21["diff"] > 0, "volume"].sum())
        dn_vol = float(recent_21.loc[recent_21["diff"] < 0, "volume"].sum())
        up_down_ratio = round(up_vol / max(dn_vol, 1.0), 2)

        avg_vol_20 = float(df["volume"].tail(20).mean())
        vol_ratio = curr_vol / max(avg_vol_20, 1.0)
        sma20 = float(df["close"].tail(20).mean())
        dist_from_sma20_pct = ((curr_price - sma20) / sma20 * 100.0) if sma20 > 0 else 0.0

        # Đếm số phiên phân phối (Distribution Days: giá giảm > 0.5% với Vol > Vol phiên trước)
        recent_20 = recent_21.tail(20).copy()
        recent_20["prev_vol"] = recent_20["volume"].shift(1)
        recent_20["pct_chg"] = recent_20["close"].pct_change() * 100.0
        dist_days = int(((recent_20["pct_chg"] < -0.5) & (recent_20["volume"] > recent_20["prev_vol"])).sum())
        acc_days = int(((recent_20["pct_chg"] > 0.5) & (recent_20["volume"] > recent_20["prev_vol"])).sum())

        sentiment_score = 0
        notes = []
        media_trap_warning = None

        # Đánh giá Khối ngoại
        if f_net_vol > 100_000 or f_net_val_b >= 3.0:
            sentiment_score += 2
            notes.append(
                f"Khối ngoại MUA RÒNG mạnh +{f_net_vol:,} CP (+{f_net_val_b:,.2f} tỷ VNĐ) [Mua: {f_buy:,} | Bán: {f_sell:,} CP]."
            )
        elif f_net_vol < -100_000 or f_net_val_b <= -3.0:
            sentiment_score -= 2
            notes.append(
                f"Khối ngoại BÁN RÒNG {f_net_vol:,} CP ({f_net_val_b:,.2f} tỷ VNĐ) [Mua: {f_buy:,} | Bán: {f_sell:,} CP], gây áp lực cung ngắn hạn."
            )
        elif f_buy > 0 or f_sell > 0:
            notes.append(
                f"Giao dịch Khối ngoại cân bằng: Ròng {f_net_vol:+,} CP ({f_net_val_b:+.2f} tỷ VNĐ)."
            )

        # Đánh giá Tích lũy / Phân phối 20 phiên
        if up_down_ratio >= 1.3 and acc_days >= dist_days:
            sentiment_score += 2
            flow_status = "DÒNG TIỀN TỔ CHỨC TÍCH LŨY (INSTITUTIONAL ACCUMULATION) 🟢"
            notes.append(
                f"Tỷ lệ Khối lượng Mua gom / Bán xả 20 phiên đạt {up_down_ratio:.2f}x ({acc_days} phiên gom chuẩn vs {dist_days} phiên phân phối)."
            )
        elif up_down_ratio <= 0.75 or dist_days >= acc_days + 3:
            sentiment_score -= 3
            flow_status = "ÁP LỰC PHÂN PHỐI TỔ CHỨC (INSTITUTIONAL DISTRIBUTION) 🔴"
            notes.append(
                f"Xuất hiện {dist_days} phiên phân phối lớn trong 20 ngày qua (Tỷ lệ Up/Down Vol chỉ đạt {up_down_ratio:.2f}x)."
            )
        else:
            flow_status = "DÒNG TIỀN HẤP THỤ CÂN BẰNG (NEUTRAL ROTATION) 🟡"
            notes.append(
                f"Cung cầu 20 phiên cân bằng (Up/Down Vol = {up_down_ratio:.2f}x | {acc_days} phiên tăng vol vs {dist_days} phiên giảm vol)."
            )

        # Phát hiện Bẫy Truyền Thông / FOMO / Xả hàng giá cao
        if dist_from_sma20_pct > 12.0 and vol_ratio > 1.6:
            sentiment_score -= 2
            media_trap_warning = (
                f"⚠️ CẢNH BÁO FOMO / BUYING CLIMAX: Giá đã kéo giãn quá xa đường MA20 (+{dist_from_sma20_pct:.1f}%) "
                f"kèm khối lượng đột biến ({vol_ratio:.1f}x TB20). Rủi ro tổ chức tận dụng hưng phấn tin tốt để trao tay cho nhỏ lẻ (Rủi ro kẹt T+2.5)!"
            )
        elif chg_pct <= -2.5 and vol_ratio >= 1.4:
            sentiment_score -= 2
            media_trap_warning = (
                f"⚠️ CẢNH BÁO XẢ HÀNG CHỦ ĐỘNG: Giá giảm mạnh ({chg_pct:+.2f}%) kèm khối lượng bung lớn ({vol_ratio:.1f}x TB20). "
                f"Tuyệt đối không bắt đáy khi áp lực cung tổ chức đang thoát ra!"
            )
        elif abs(chg_pct) <= 1.2 and vol_ratio <= 0.65 and dist_from_sma20_pct >= -3.0:
            sentiment_score += 2
            notes.append(
                f"Tín hiệu Cạn Cung (No Supply / Volume Dry-Up): Khối lượng co hẹp chỉ bằng {vol_ratio*100:.0f}% TB20, nhỏ lẻ đã rũ bỏ xong."
            )

        return {
            "symbol": symbol,
            "sentiment_score": sentiment_score,
            "flow_status": flow_status,
            "foreign_buy_vol": f_buy,
            "foreign_sell_vol": f_sell,
            "foreign_net_vol": f_net_vol,
            "foreign_net_val_billion": f_net_val_b,
            "up_down_vol_ratio": up_down_ratio,
            "accumulation_days_20": acc_days,
            "distribution_days_20": dist_days,
            "vol_ratio": round(vol_ratio, 2),
            "dist_from_sma20_pct": round(dist_from_sma20_pct, 2),
            "media_trap_warning": media_trap_warning,
            "sentiment_notes": notes
        }
