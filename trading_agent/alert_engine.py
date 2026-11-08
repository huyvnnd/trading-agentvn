"""
Alert & Notification Engine for Vietnam Stock Market.
Quản lý các cảnh báo chạm ngưỡng giá (Price Target / Stop Loss) và cảnh báo tín hiệu kỹ thuật.
"""

import os
import json
from datetime import datetime
from trading_agent.data_engine import DataEngine

class AlertEngine:
    def __init__(self, data_file: str = None, data_engine: DataEngine = None):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "alerts.json")

        self.data_file = data_file
        self.de = data_engine or DataEngine()
        self.alerts = []
        self.triggered_alerts = []
        self.load()

    def load(self):
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.alerts = data.get("alerts", [])
                    self.triggered_alerts = data.get("triggered", [])
            except Exception as e:
                print(f"[AlertEngine] Error loading alerts: {e}")

    def save(self):
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "alerts": self.alerts,
                    "triggered": self.triggered_alerts
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[AlertEngine] Error saving alerts: {e}")

    def add_price_alert(self, symbol: str, condition: str, target_price: float, note: str = "") -> dict:
        """
        Thêm cảnh báo giá:
        - condition: 'above' (vượt lên trên) hoặc 'below' (giảm xuống dưới)
        """
        symbol = symbol.strip().upper()
        alert = {
            "id": f"ALT{len(self.alerts) + len(self.triggered_alerts) + 1:04d}",
            "type": "price",
            "symbol": symbol,
            "condition": condition,
            "target_price": target_price,
            "note": note,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "active"
        }
        self.alerts.append(alert)
        self.save()
        cond_text = "vượt lên trên" if condition == "above" else "giảm xuống dưới"
        return {
            "success": True,
            "message": f"Đã thiết lập cảnh báo: Báo động khi {symbol} {cond_text} {target_price:,.0f} đ",
            "alert": alert
        }

    def check_alerts(self) -> list:
        """Kiểm tra toàn bộ các cảnh báo đang kích hoạt so với giá thực tế."""
        new_triggered = []
        remaining_alerts = []

        for alt in self.alerts:
            symbol = alt["symbol"]
            quote = self.de.get_latest_quote(symbol)
            if quote["status"] != "success":
                remaining_alerts.append(alt)
                continue

            current_price = float(quote["price"])
            target = float(alt["target_price"])
            condition = alt["condition"]

            triggered = False
            msg = ""

            if condition == "above" and current_price >= target:
                triggered = True
                msg = f"🔔 CẢNH BÁO GIÁ: {symbol} đã VƯỢT {target:,.0f} đ (Giá hiện tại: {current_price:,.0f} đ)"
            elif condition == "below" and current_price <= target:
                triggered = True
                msg = f"⚠️ CẢNH BÁO GIÁ: {symbol} đã GIẢM DƯỚI {target:,.0f} đ (Giá hiện tại: {current_price:,.0f} đ)"

            if triggered:
                alt["triggered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                alt["triggered_price"] = current_price
                alt["message"] = msg
                alt["status"] = "triggered"
                self.triggered_alerts.append(alt)
                new_triggered.append(msg)
            else:
                remaining_alerts.append(alt)

        if new_triggered:
            self.alerts = remaining_alerts
            self.save()

        return new_triggered

    def remove_alert(self, alert_id: str) -> bool:
        """Hủy một cảnh báo."""
        initial_len = len(self.alerts)
        self.alerts = [a for a in self.alerts if a["id"] != alert_id]
        if len(self.alerts) < initial_len:
            self.save()
            return True
        return False
