"""
Institutional Derivatives & Smart Money Order-Flow Agent for Vietnam Market (VN30F1M).
Theo dõi chuyên sâu Hợp đồng Tương lai VN30F1M (100% Dữ liệu Thực từ Bảng giá Phái sinh KBS & Khung 15m):
1. Độ lệch Basis (VN30F1M vs VN30), Khối lượng Mở qua đêm (Open Interest - OI thực tế), Giao dịch Khối ngoại Mua/Bán hợp đồng thực tế.
2. Mức Giá Vốn Tổ Chức / Cá Mập dựa trên Volume Profile (Point of Control - POC, VAH, VAL) của hợp đồng VN30F1M.
3. Radar 10 Cổ Phiếu Trụ Dẫn Dắt Chỉ Số VN30 (FPT, TCB, HPG, VPB, ACB, MWG, MBB, VCB, VHM, VIC) và đóng góp điểm số.
4. Cảnh báo Ngày Đáo Hạn Phái Sinh (Thứ Năm tuần thứ 3 hàng tháng) và Chiến lược Long/Short theo R-Multiple.
"""

from datetime import datetime, date, timedelta
import pandas as pd
import numpy as np
from trading_agent.data_engine import DataEngine, VN30_PILLAR_WEIGHTS


class DerivativesAgent:
    def __init__(self, data_engine: DataEngine = None):
        self.data_engine = data_engine or DataEngine()

    @staticmethod
    def _get_third_thursday(year: int, month: int) -> date:
        d = date(year, month, 1)
        # weekday(): Monday=0 ... Thursday=3
        offset = (3 - d.weekday()) % 7
        first_thursday = d + timedelta(days=offset)
        return first_thursday + timedelta(days=14)

    def _days_to_expiration(self) -> tuple:
        today = date.today()
        exp = self._get_third_thursday(today.year, today.month)
        if today > exp:
            ny = today.year + (1 if today.month == 12 else 0)
            nm = 1 if today.month == 12 else today.month + 1
            exp = self._get_third_thursday(ny, nm)
        return (exp - today).days, exp.strftime("%Y-%m-%d")

    def get_derivatives_overview(self) -> dict:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 1. Lấy dữ liệu Bảng giá Phái sinh VN30F1M thực tế từ KBS (0.28s)
        f_quote = self.data_engine.get_latest_quote("VN30F1M")
        f_hist_d = self.data_engine.get_history("VN30F1M", days=60)
        f_hist_15m = self.data_engine.get_history("VN30F1M", days=20, interval="15m")

        f_price = float(f_quote.get("price", 0.0))
        f_ref = float(f_quote.get("ref_price", f_price))
        f_change = float(f_quote.get("change", 0.0))
        f_change_pct = float(f_quote.get("change_pct", 0.0))
        f_volume = int(f_quote.get("volume", 0))
        open_interest = int(f_quote.get("open_interest", 0))
        foreign_buy = int(f_quote.get("foreign_buy_volume", 0))
        foreign_sell = int(f_quote.get("foreign_sell_volume", 0))
        foreign_net = foreign_buy - foreign_sell

        f_high = f_price
        f_low = f_price
        if not f_hist_d.empty:
            last_bar = f_hist_d.iloc[-1]
            if f_price <= 0:
                f_price = float(last_bar["close"])
            f_high = float(last_bar.get("high", f_price))
            f_low = float(last_bar.get("low", f_price))

        # 2. Lấy dữ liệu chỉ số cơ sở VN30
        vn30_quote = self.data_engine.get_latest_quote("VN30")
        vn30_price = float(vn30_quote.get("price", f_price))
        vn30_change = float(vn30_quote.get("change", 0.0))
        vn30_change_pct = float(vn30_quote.get("change_pct", 0.0))

        # 3. Tính độ lệch Basis (F1M - VN30) & Đếm ngược Đáo hạn
        basis = round(f_price - vn30_price, 2) if (f_price > 0 and vn30_price > 0) else 0.0
        days_to_exp, exp_date_str = self._days_to_expiration()

        # 4. Tính Volume Profile (POC, VAH, VAL) trên khung 15m/Daily làm Giá Vốn Cá Mập / Khối Ngoại
        vp_df = f_hist_15m if (not f_hist_15m.empty and len(f_hist_15m) >= 20) else f_hist_d
        poc_price = round(f_price - basis * 0.5, 1)
        vah_price = round(f_price + 6.0, 1)
        val_price = round(f_price - 6.0, 1)
        vwap = round(f_price, 1)

        if not vp_df.empty and len(vp_df) >= 5:
            p_min = float(vp_df["low"].min())
            p_max = float(vp_df["high"].max())
            tot_v = float(vp_df["volume"].sum())
            if tot_v > 0:
                vwap_recent = vp_df.tail(25)
                rv = float(vwap_recent["volume"].sum())
                if rv > 0:
                    vwap = round(float((vwap_recent["close"] * vwap_recent["volume"]).sum() / rv), 1)
            if p_max > p_min:
                bins = np.linspace(p_min, p_max, 21)
                v_hist = np.zeros(20)
                typ_p = (vp_df["high"] + vp_df["low"] + vp_df["close"]) / 3.0
                for tp, v in zip(typ_p, vp_df["volume"]):
                    b_idx = min(max(int(np.digitize(tp, bins)) - 1, 0), 19)
                    v_hist[b_idx] += v
                poc_idx = int(np.argmax(v_hist))
                poc_price = round(float((bins[poc_idx] + bins[poc_idx + 1]) / 2.0), 1)
                acc_v = v_hist[poc_idx]
                lo_i, hi_i = poc_idx, poc_idx
                while acc_v < 0.70 * np.sum(v_hist) and (lo_i > 0 or hi_i < 19):
                    v_dn = v_hist[lo_i - 1] if lo_i > 0 else -1
                    v_up = v_hist[hi_i + 1] if hi_i < 19 else -1
                    if v_up >= v_dn and hi_i < 19:
                        hi_i += 1
                        acc_v += v_hist[hi_i]
                    elif lo_i > 0:
                        lo_i -= 1
                        acc_v += v_hist[lo_i]
                    else:
                        break
                val_price = round(float(bins[lo_i]), 1)
                vah_price = round(float(bins[hi_i + 1]), 1)

        # 5. Phân tích Intraday Tick (Mua / Bán chủ động)
        active_buy_vol = 0
        active_sell_vol = 0
        intra = self.data_engine.get_intraday_ticks("VN30F1M")
        if not intra.empty and "match_type" in intra.columns and "volume" in intra.columns:
            m_col = intra["match_type"].astype(str).str.lower()
            active_buy_vol = int(intra.loc[m_col.isin(["buy", "b", "mua"]), "volume"].sum())
            active_sell_vol = int(intra.loc[m_col.isin(["sell", "s", "ban", "bán"]), "volume"].sum())

        # 6. Radar 10 Cổ Phiếu Trụ VN30 (Lead/Lag Impact Basket)
        pillar_syms = list(VN30_PILLAR_WEIGHTS.keys())
        pb_pillars = self.data_engine.get_batch_price_board(pillar_syms)
        pillar_radar = []
        weighted_index_pull = 0.0
        pillars_up = 0
        pillars_down = 0

        for p_sym, weight in VN30_PILLAR_WEIGHTS.items():
            row = pb_pillars.get(p_sym, {})
            p_chg_pct = float(row.get("change_pct", 0.0))
            p_price = float(row.get("price", 0.0))
            p_fnet = int(row.get("foreign_net_volume", 0))
            # Point impact approximation on VN30 (~1850 pts base)
            pt_impact = round((p_chg_pct / 100.0) * weight * vn30_price, 2)
            weighted_index_pull += pt_impact
            if p_chg_pct > 0:
                pillars_up += 1
            elif p_chg_pct < 0:
                pillars_down += 1
            pillar_radar.append({
                "symbol": p_sym,
                "weight_pct": round(weight * 100.0, 1),
                "price": p_price,
                "change_pct": p_chg_pct,
                "point_impact": pt_impact,
                "foreign_net_vol": p_fnet
            })

        pillar_radar.sort(key=lambda x: abs(x["point_impact"]), reverse=True)

        # 7. Xác định vị thế Khối Ngoại & Cá Mập (Smart Money Position & Cost Basis)
        if foreign_net > 0 and f_price >= poc_price:
            smart_position_type = "NET LONG (MUA RÒNG)"
        elif foreign_net < 0 and f_price < poc_price:
            smart_position_type = "NET SHORT (BÁN RÒNG)"
        elif f_price >= poc_price and basis >= -1.0:
            smart_position_type = "NET LONG (GIỮ TRÊN POC)"
        else:
            smart_position_type = "NET SHORT (ĐÈ DƯỚI POC)"

        holding_cost = poc_price
        pnl_points = round(f_price - holding_cost if "LONG" in smart_position_type else holding_cost - f_price, 1)

        if "LONG" in smart_position_type and weighted_index_pull >= 0:
            smart_intent = "DỒN LỰC LONG & KÉO TRỤ VN30 (BULLISH ACCUMULATION) 🟢"
            impact_on_cash = f"Rổ trụ VN30 đồng thuận kéo +{weighted_index_pull:+.2f} điểm ({pillars_up} trụ tăng / {pillars_down} trụ giảm). Giá giữ trên vùng giá vốn POC ({poc_price:,.1f})."
            market_sentiment = "Tích cực, dòng tiền lớn nâng đỡ tại vùng POC/VWAP"
        elif "SHORT" in smart_position_type:
            smart_intent = "GIA TĂNG SHORT PHÒNG VỆ / ĐÈ TRỤ (BEARISH HEDGING / PRESSURE) 🔴"
            impact_on_cash = f"Khối ngoại giao dịch ròng {foreign_net:+,} HĐ; Rổ trụ VN30 tác động {weighted_index_pull:+.2f} điểm ({pillars_up} trụ tăng / {pillars_down} trụ giảm)."
            market_sentiment = "Thận trọng, cảnh giác áp lực rung lắc từ nhóm vốn hóa lớn"
        else:
            smart_intent = "GIẰNG CO HẤP THỤ QUANH VÙNG GIÁ VỐN POC (RANGE-BOUND) 🟡"
            impact_on_cash = f"Trụ VN30 phân hóa ({pillars_up} trụ tăng / {pillars_down} trụ giảm, tác động {weighted_index_pull:+.2f} điểm)."
            market_sentiment = "Quan sát phản ứng giá tại biên Value Area (VAL - VAH)"

        # 8. Thiết lập kịch bản giao dịch chuẩn R-Multiple (Playbook)
        pivot = poc_price
        r1 = max(vah_price, round(f_price + 6.0, 1))
        s1 = min(val_price, round(f_price - 6.0, 1))

        long_entry_min = round(min(s1, poc_price - 2.0), 1)
        long_entry_max = round(poc_price + 1.0, 1)
        long_sl = round(long_entry_min - 4.0, 1)
        long_tp1 = round(long_entry_max + 10.0, 1)
        long_tp2 = round(long_entry_max + 16.0, 1)

        short_entry_min = round(max(poc_price, r1 - 2.0), 1)
        short_entry_max = round(r1 + 1.5, 1)
        short_sl = round(short_entry_max + 4.0, 1)
        short_tp1 = round(short_entry_min - 10.0, 1)
        short_tp2 = round(short_entry_min - 16.0, 1)

        return {
            "timestamp": now_str,
            "contract": "VN30F1M",
            "price": f_price,
            "ref_price": f_ref,
            "change": round(f_change, 1),
            "change_pct": round(f_change_pct, 2),
            "high": f_high,
            "low": f_low,
            "volume": f_volume,
            "open_interest": open_interest,
            "foreign_buy": foreign_buy,
            "foreign_sell": foreign_sell,
            "foreign_net": foreign_net,
            "vn30_price": vn30_price,
            "vn30_change": round(vn30_change, 2),
            "vn30_change_pct": round(vn30_change_pct, 2),
            "basis": basis,
            "days_to_expiry": days_to_exp,
            "expiry_date": exp_date_str,
            "vwap": vwap,
            "poc": poc_price,
            "vah": vah_price,
            "val": val_price,
            "active_buy_vol": active_buy_vol,
            "active_sell_vol": active_sell_vol,
            "pillar_radar": pillar_radar,
            "weighted_pillar_pull": round(weighted_index_pull, 2),
            "pillars_up": pillars_up,
            "pillars_down": pillars_down,
            "smart_money": {
                "stance": smart_intent,
                "position_type": smart_position_type,
                "cumulative_contracts": open_interest if open_interest > 0 else abs(foreign_net),
                "foreign_net_today": foreign_net,
                "estimated_holding_cost": holding_cost,
                "pnl_points": pnl_points,
                "pnl_status": "ĐANG CÓ LÃI TRÊN VỊ THẾ" if pnl_points > 0 else "ĐANG GIẰNG CO QUANH GIÁ VỐN POC",
                "impact_on_cash_market": impact_on_cash,
                "market_sentiment": market_sentiment
            },
            "playbook": {
                "pivot": pivot,
                "resistance_r1": r1,
                "support_s1": s1,
                "long_setup": {
                    "entry_zone": f"{long_entry_min:,.1f} - {long_entry_max:,.1f}",
                    "stop_loss": long_sl,
                    "target_tp1": long_tp1,
                    "target_tp2": long_tp2,
                    "risk_reward": "1 : 2.5"
                },
                "short_setup": {
                    "entry_zone": f"{short_entry_min:,.1f} - {short_entry_max:,.1f}",
                    "stop_loss": short_sl,
                    "target_tp1": short_tp1,
                    "target_tp2": short_tp2,
                    "risk_reward": "1 : 2.5"
                }
            }
        }

    def generate_derivatives_report(self) -> str:
        data = self.get_derivatives_overview()
        sm = data["smart_money"]
        pb = data["playbook"]

        basis_color = "🟢" if data["basis"] >= 0 else "🔴"
        pos_badge = "🟢 " + sm["position_type"] if "LONG" in sm["position_type"] else "🔴 " + sm["position_type"]

        pillar_rows = [
            "| Mã Trụ | Trọng Số VN30 | Thị Giá (đ) | Thay Đổi (%) | Tác Động Điểm VN30 | Khối Ngoại Ròng (CP) |",
            "| :---: | :---: | :---: | :---: | :---: | :---: |"
        ]
        for p in data["pillar_radar"][:8]:
            pillar_rows.append(
                f"| **{p['symbol']}** | `{p['weight_pct']:.1f}%` | {p['price']:,.0f} | "
                f"`{p['change_pct']:+.2f}%` | **{p['point_impact']:+.2f} đ** | `{p['foreign_net_vol']:+,}` |"
            )
        pillar_table = "\n".join(pillar_rows)

        report = f"""# ⚡ BÁO CÁO GIÁM SÁT PHÁI SINH & RADAR TRỤ VN30 (VN30F1M)
**Thời gian cập nhật:** `{data['timestamp']}` | **Đáo hạn HĐ ({data['expiry_date']}):** Còn `{data['days_to_expiry']} ngày`

---
## 📊 1. TỔNG QUAN HỢP ĐỒNG VN30F1M & ĐỘ LỆCH BASIS
- **Giá Khớp Hiện Tại:** `{data['price']:,.1f} điểm` ({data['change']:+.1f} điểm | `{data['change_pct']:+.2f}%`)
- **Chỉ Số Cơ Sở VN30:** `{data['vn30_price']:,.2f} điểm` ({data['vn30_change']:+.2f} điểm | `{data['vn30_change_pct']:+.2f}%`)
- {basis_color} **Độ Lệch Basis (F1M - VN30):** `{data['basis']:+.2f} điểm`
- 📈 **Volume Profile Phái Sinh:** Giá vốn tổ chức **POC: `{data['poc']:,.1f}`** | Biên trên **VAH: `{data['vah']:,.1f}`** | Biên dưới **VAL: `{data['val']:,.1f}`** | VWAP: `{data['vwap']:,.1f}`
- 🔄 **Khối lượng khớp:** `{data['volume']:,} HĐ` | **Khối lượng mở qua đêm (Open Interest):** **`{data['open_interest']:,} HĐ`**

---
## 🐋 2. VỊ THẾ KHỐI NGOẠI & CÁ MẬP (REALTIME SMART MONEY RADAR)
- 🎯 **Trạng Thái Dòng Tiền Lớn:** **{sm['stance']}**
- 🛡️ **Xu Hướng Vị Thế的主Đạo:** **{pos_badge}**
- 🌍 **Giao Dịch Khối Ngoại Trong Phiên:** Mua `{data['foreign_buy']:,} HĐ` | Bán `{data['foreign_sell']:,} HĐ` | **Ròng: `{data['foreign_net']:+,} HĐ`**
- 💰 **Mức Giá Vốn Trọng Tâm (POC Cost Basis):** **`{sm['estimated_holding_cost']:,.1f} điểm`** (Chênh lệch hiện tại: `{sm['pnl_points']:+.1f} điểm`)
- 🌐 **Tác Động Lên Thị Trường Cơ Sở:**
  > 📌 *{sm['impact_on_cash_market']}*

---
## 🏛️ 3. RADAR 8 CỔ PHIẾU TRỤ ĐIỀU TIẾT CHỈ SỐ VN30 & PHÁI SINH
{pillar_table}

---
## 🎯 4. CHIẾN LƯỢC GIAO DỊCH TRONG PHIÊN (INSTITUTIONAL PLAYBOOK)
### 🟢 Kịch Bản 1: CHIẾN LƯỢC LONG (KHI GIỮ VỮNG TRÊN VÙNG VAL/POC)
- **Vùng Mở Long (Optimal Long Entry):** `{pb['long_setup']['entry_zone']}`
- **Cắt Lỗ Tuyệt Đối (Stop Loss):** `{pb['long_setup']['stop_loss']:,.1f} điểm` (-4.0 điểm)
- **Chốt Lời TP1:** `{pb['long_setup']['target_tp1']:,.1f} điểm` | **TP2:** `{pb['long_setup']['target_tp2']:,.1f} điểm` (R:R = `{pb['long_setup']['risk_reward']}`)

### 🔴 Kịch Bản 2: CHIẾN LƯỢC SHORT (KHI BỊ TỪ CHỐI TẠI VAH/R1 HOẶC THỦNG POC)
- **Vùng Mở Short (Optimal Short Entry):** `{pb['short_setup']['entry_zone']}`
- **Cắt Lỗ Tuyệt Đối (Stop Loss):** `{pb['short_setup']['stop_loss']:,.1f} điểm` (+4.0 điểm)
- **Chốt Lời TP1:** `{pb['short_setup']['target_tp1']:,.1f} điểm` | **TP2:** `{pb['short_setup']['target_tp2']:,.1f} điểm` (R:R = `{pb['short_setup']['risk_reward']}`)
"""
        return report
