"""
Macro & Global/Domestic Market Regime Agent (with FinRL Turbulence & O'Neil Market Direction 'M').
Phân tích vĩ mô trong nước, quốc tế, Độ rộng thị trường (Market Breadth), Đếm ngày phân phối VN-Index
và Chỉ số Hỗn loạn FinRL (Turbulence Index Circuit Breaker).
Tích hợp bộ nhớ đệm TTL 15 phút giúp phản hồi tức thì (< 0.001s).
"""

import time
import xml.etree.ElementTree as ET
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import requests
import pandas as pd
import numpy as np


class MacroAgent:
    _cached_regime = None
    _cached_ts = 0.0

    def __init__(self, data_engine=None):
        self.de = data_engine
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    def fetch_global_macro(self) -> dict:
        tickers = {
            "dxy": ("DX-Y.NYB", 103.5),
            "us10y": ("^TNX", 4.20),
            "brent_oil": ("BZ=F", 74.5),
            "sp500": ("^GSPC", 5800.0),
            "gold": ("GC=F", 2720.0)
        }

        def _fetch_one(item):
            key, (ticker, default_val) = item
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=5d"
                resp = requests.get(url, headers=self.headers, timeout=3.0)
                if resp.status_code == 200:
                    meta = resp.json()["chart"]["result"][0]["meta"]
                    price = float(meta.get("regularMarketPrice", default_val))
                    prev = float(meta.get("chartPreviousClose", price))
                    chg_pct = ((price - prev) / prev * 100.0) if prev > 0 else 0.0
                    return key, {"price": round(price, 2), "change_pct": round(chg_pct, 2), "status": "live"}
            except Exception:
                pass
            return key, {"price": default_val, "change_pct": 0.0, "status": "fallback"}

        results = {}
        with ThreadPoolExecutor(max_workers=5) as ex:
            for k, val in ex.map(_fetch_one, tickers.items()):
                results[k] = val
        return results

    def fetch_vietnam_macro(self) -> dict:
        usdvnd_sell = 25450.0
        status = "fallback"
        try:
            url = "https://portal.vietcombank.com.vn/Usercontrols/TVPortal.TyGia/pXML.aspx"
            resp = requests.get(url, headers=self.headers, timeout=3.0)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for exrate in root.findall("Exrate"):
                    if exrate.attrib.get("CurrencyCode") == "USD":
                        sell_str = exrate.attrib.get("Sell", "25450").replace(",", "")
                        usdvnd_sell = float(sell_str)
                        status = "live"
                        break
        except Exception:
            pass

        # Compute real VN-Index technical regime, Distribution Days & FinRL Turbulence Index
        vni_price = 1260.0
        vni_sma20 = 1250.0
        vni_sma50 = 1240.0
        vni_sma200 = 1220.0
        dist_days_25 = 2
        turbulence_index = 0.85
        vn30_advancing = 15
        vn30_declining = 10

        if self.de is not None:
            try:
                df_vni = self.de.get_history("VNINDEX", days=350)
                if not df_vni.empty and len(df_vni) >= 30:
                    closes = df_vni["close"]
                    vni_price = float(closes.iloc[-1])
                    vni_sma20 = float(closes.tail(20).mean())
                    vni_sma50 = float(closes.tail(50).mean())
                    vni_sma200 = float(closes.tail(min(len(closes), 200)).mean())

                    # Count O'Neil Distribution Days in last 25 sessions (drop <= -0.3% on higher volume)
                    w25 = df_vni.tail(26).copy()
                    w25["ret"] = w25["close"].pct_change() * 100.0
                    w25["v_prev"] = w25["volume"].shift(1)
                    dist_days_25 = int(((w25["ret"] <= -0.3) & (w25["volume"] > w25["v_prev"])).sum())

                    # FinRL Turbulence Index (squared standardized return deviation over 120d lookback)
                    rets = closes.pct_change().dropna()
                    if len(rets) >= 30:
                        mu = float(rets.tail(120).mean())
                        sigma = max(float(rets.tail(120).std()), 0.005)
                        recent_std = float(rets.tail(5).std()) if len(rets) >= 5 else sigma
                        z_shock = abs(float(rets.iloc[-1]) - mu) / sigma
                        turbulence_index = round(float(0.5 * (z_shock ** 2) + 0.5 * ((recent_std / sigma) ** 2)), 2)

                # VN30 Breadth from fast batch price board
                vn30_syms = self.de.get_vn30_symbols()
                pb = self.de.get_batch_price_board(vn30_syms)
                if pb:
                    vn30_advancing = sum(1 for v in pb.values() if v.get("change_pct", 0) > 0)
                    vn30_declining = sum(1 for v in pb.values() if v.get("change_pct", 0) < 0)
            except Exception:
                pass

        return {
            "usdvnd_rate": usdvnd_sell,
            "sbv_refinancing_rate": 4.50,
            "vnindex_pe": 13.6,
            "vnindex_price": round(vni_price, 2),
            "vnindex_sma20": round(vni_sma20, 2),
            "vnindex_sma50": round(vni_sma50, 2),
            "vnindex_sma200": round(vni_sma200, 2),
            "distribution_days_25": dist_days_25,
            "turbulence_index": turbulence_index,
            "vn30_advancing": vn30_advancing,
            "vn30_declining": vn30_declining,
            "status": status
        }

    def analyze_market_regime(self, force_reload: bool = False) -> dict:
        now_ts = time.time()
        if not force_reload and MacroAgent._cached_regime is not None and (now_ts - MacroAgent._cached_ts < 900):
            return MacroAgent._cached_regime

        glob = self.fetch_global_macro()
        dom = self.fetch_vietnam_macro()

        macro_score = 0
        headwinds = []
        tailwinds = []

        # 1. Đánh giá DXY
        dxy_val = glob["dxy"]["price"]
        if dxy_val >= 105.5:
            macro_score -= 2
            headwinds.append(f"Chỉ số DXY cao ({dxy_val}): Gây áp lực lên tỷ giá USD/VND và dòng vốn ngoại.")
        elif dxy_val <= 102.5:
            macro_score += 2
            tailwinds.append(f"Chỉ số DXY hạ nhiệt ({dxy_val}): Thuận lợi cho chính sách tiền tệ NHNN và thu hút vốn ngoại.")
        else:
            tailwinds.append(f"Chỉ số DXY duy trì vùng trung tính ({dxy_val}).")

        # 2. Lợi suất US10Y
        us10y_val = glob["us10y"]["price"]
        if us10y_val >= 4.5:
            macro_score -= 2
            headwinds.append(f"Lợi suất TPCP Mỹ 10Y cao ({us10y_val}%): Chi phí vốn toàn cầu đắt đỏ.")
        elif us10y_val <= 4.1:
            macro_score += 2
            tailwinds.append(f"Lợi suất TPCP Mỹ 10Y dịu lại ({us10y_val}%): Hỗ trợ định giá P/E cổ phiếu tăng trưởng.")

        # 3. Tỷ giá USD/VND
        usdvnd = dom["usdvnd_rate"]
        if usdvnd >= 25600:
            macro_score -= 2
            headwinds.append(f"Tỷ giá USD/VND căng thẳng ({usdvnd:,.0f} đ): Rủi ro NHNN phát hành tín phiếu hút ròng thanh khoản.")
        else:
            macro_score += 1
            tailwinds.append(f"Tỷ giá USD/VND trong tầm kiểm soát ({usdvnd:,.0f} đ), lãi suất điều hành duy trì {dom['sbv_refinancing_rate']}%.")

        # 4. Xu hướng kỹ thuật VN-INDEX (William O'Neil 'M' & FinRL Turbulence)
        vni_p = dom["vnindex_price"]
        vni_50 = dom["vnindex_sma50"]
        vni_200 = dom["vnindex_sma200"]
        dist_days = dom["distribution_days_25"]
        turb = dom["turbulence_index"]

        if vni_p > vni_50 and vni_50 >= vni_200:
            macro_score += 3
            tailwinds.append(
                f"VN-INDEX ({vni_p:,.1f}) duy trì Uptrend trên MA50 ({vni_50:,.1f}) & MA200 ({vni_200:,.1f}). Độ rộng VN30: {dom['vn30_advancing']} mã tăng / {dom['vn30_declining']} mã giảm."
            )
        elif vni_p < vni_200:
            macro_score -= 4
            headwinds.append(
                f"VN-INDEX ({vni_p:,.1f}) gãy dưới đường MA200 ({vni_200:,.1f}) - Thị trường chung suy yếu dài hạn!"
            )
        elif vni_p < vni_50:
            macro_score -= 2
            headwinds.append(
                f"VN-INDEX ({vni_p:,.1f}) điều chỉnh dưới MA50 ({vni_50:,.1f}), cần thận trọng tỷ trọng."
            )

        if dist_days >= 5:
            macro_score -= 2
            headwinds.append(
                f"Cảnh báo O'Neil Market Direction: Xuất hiện {dist_days} phiên phân phối lớn trong 25 phiên gần nhất trên VN-INDEX."
            )
        else:
            tailwinds.append(f"Số phiên phân phối trên VN-INDEX thấp ({dist_days} phiên / 25 ngày), áp lực xả tổng thể chưa đáng ngại.")

        if turb >= 2.5:
            macro_score -= 3
            headwinds.append(f"Chỉ số Hỗn loạn FinRL (Turbulence Index = {turb:.2f} > 2.5): Biến động thị trường bất thường, kích hoạt thu hẹp quy mô vốn!")

        # 5. Phân loại Pha Thị Trường (Market Regime)
        if macro_score >= 3 and turb < 2.5:
            regime = "UPTREND XÁC NHẬN - DÒNG TIỀN THUẬN LỢI (CONFIRMED UPTREND / RISK-ON) 🟢"
            max_equity_pct = 80
            cash_pct = 20
            regime_desc = "Vĩ mô và cấu trúc VN-Index đồng thuận tích cực. Ưu tiên giải ngân các cổ phiếu Giai đoạn 2 có mẫu hình VCP/VSA và RS ≥ 70."
        elif macro_score <= -3 or turb >= 3.0:
            regime = "THỊ TRƯỜNG RỦI RO CAO / PHÒNG THỦ (CORRECTION / RISK-OFF) 🔴"
            max_equity_pct = 25
            cash_pct = 75
            regime_desc = "Áp lực vĩ mô hoặc số phiên phân phối VN-Index tăng cao. Tuyệt đối không dùng Margin, nâng tỷ trọng tiền mặt bảo vệ tài khoản."
        else:
            regime = "UPTREND CHỊU ÁP LỰC / PHÂN HÓA CHỌN LỌC (SELECTIVE ACCUMULATION) 🟡"
            max_equity_pct = 55
            cash_pct = 45
            regime_desc = "Thị trường phân hóa mạnh theo câu chuyện KQKD từng ngành. Giải ngân tại nền hỗ trợ POC, tuyệt đối không mua đuổi giá xanh."

        result = {
            "macro_score": macro_score,
            "regime": regime,
            "regime_desc": regime_desc,
            "recommended_allocation": {
                "equity_pct": max_equity_pct,
                "cash_pct": cash_pct
            },
            "global_data": glob,
            "domestic_data": dom,
            "tailwinds": tailwinds,
            "headwinds": headwinds,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        MacroAgent._cached_regime = result
        MacroAgent._cached_ts = now_ts
        return result
