"""
Portfolio Management & Paper Trading for Vietnam Market.
Quản lý tài khoản giao dịch mô phỏng, ghi nhận lệnh Mua/Bán, tính toán lãi/lỗ (P&L) theo thời gian thực.
"""

import os
import json
from datetime import datetime
import pandas as pd

class PortfolioManager:
    def __init__(self, data_file: str = None, initial_cash: float = 100_000_000.0):
        if data_file is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_file = os.path.join(base_dir, "data", "portfolio.json")

        self.data_file = data_file
        self.initial_cash = initial_cash
        self.cash = initial_cash
        self.holdings = {}  # {symbol: {"quantity": int, "avg_price": float}}
        self.transactions = []  # list of tx dicts

        self.load()

    def load(self):
        """Đọc trạng thái danh mục từ file JSON."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.cash = float(data.get("cash", self.initial_cash))
                    self.holdings = data.get("holdings", {})
                    self.transactions = data.get("transactions", [])
            except Exception as e:
                print(f"[Portfolio] Error loading portfolio: {e}")

    def save(self):
        """Lưu trạng thái danh mục vào file JSON."""
        try:
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({
                    "cash": self.cash,
                    "holdings": self.holdings,
                    "transactions": self.transactions,
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[Portfolio] Error saving portfolio: {e}")

    def reset(self, new_cash: float = None):
        """Khởi tạo lại danh mục về trạng thái ban đầu."""
        self.cash = new_cash if new_cash is not None else self.initial_cash
        self.holdings = {}
        self.transactions = []
        self.save()

    def buy(self, symbol: str, quantity: int, price: float, commission_rate: float = 0.0015) -> dict:
        """Thực hiện lệnh Mua cổ phiếu."""
        symbol = symbol.strip().upper()
        if quantity <= 0:
            return {"success": False, "message": "Số lượng phải lớn hơn 0"}
        if quantity % 100 != 0:
            return {"success": False, "message": "Số lượng mua phải là bội số của 100 (quy định sàn VN)"}

        gross_cost = quantity * price
        fee = gross_cost * commission_rate
        total_cost = gross_cost + fee

        if total_cost > self.cash:
            return {
                "success": False,
                "message": f"Số dư tiền không đủ! Cần {total_cost:,.0f} đ, hiện có {self.cash:,.0f} đ"
            }

        # Cập nhật tiền mặt
        self.cash -= total_cost

        # Cập nhật vị thế nắm giữ (tính giá vốn bình quân gia quyền)
        if symbol in self.holdings:
            cur_qty = self.holdings[symbol]["quantity"]
            cur_avg = self.holdings[symbol]["avg_price"]
            new_qty = cur_qty + quantity
            new_avg = ((cur_qty * cur_avg) + (quantity * price)) / new_qty
            self.holdings[symbol]["quantity"] = new_qty
            self.holdings[symbol]["avg_price"] = new_avg
        else:
            self.holdings[symbol] = {
                "quantity": quantity,
                "avg_price": price
            }

        # Ghi nhận giao dịch
        tx = {
            "id": f"TX{len(self.transactions) + 1:05d}",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "MUA",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "gross_amount": gross_cost,
            "fee": fee,
            "tax": 0.0,
            "net_amount": total_cost
        }
        self.transactions.append(tx)
        self.save()

        return {
            "success": True,
            "message": f"Khớp lệnh MUA thành công {quantity:,} {symbol} tại giá {price:,.0f} đ",
            "tx": tx
        }

    def sell(self, symbol: str, quantity: int, price: float, commission_rate: float = 0.0015, tax_rate: float = 0.0010) -> dict:
        """Thực hiện lệnh Bán cổ phiếu."""
        symbol = symbol.strip().upper()
        if symbol not in self.holdings or self.holdings[symbol]["quantity"] < quantity:
            avail = self.holdings.get(symbol, {}).get("quantity", 0)
            return {
                "success": False,
                "message": f"Số lượng cổ phiếu {symbol} khả dụng không đủ ({avail} < {quantity})"
            }

        if quantity <= 0:
            return {"success": False, "message": "Số lượng phải lớn hơn 0"}
        if quantity % 100 != 0:
            return {"success": False, "message": "Số lượng bán phải là bội số của 100"}

        gross_rev = quantity * price
        fee = gross_rev * commission_rate
        tax = gross_rev * tax_rate
        net_rev = gross_rev - fee - tax

        # Cập nhật tiền mặt
        self.cash += net_rev

        # Cập nhật số lượng
        cur_qty = self.holdings[symbol]["quantity"]
        if cur_qty == quantity:
            del self.holdings[symbol]
        else:
            self.holdings[symbol]["quantity"] = cur_qty - quantity

        tx = {
            "id": f"TX{len(self.transactions) + 1:05d}",
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action": "BÁN",
            "symbol": symbol,
            "quantity": quantity,
            "price": price,
            "gross_amount": gross_rev,
            "fee": fee,
            "tax": tax,
            "net_amount": net_rev
        }
        self.transactions.append(tx)
        self.save()

        return {
            "success": True,
            "message": f"Khớp lệnh BÁN thành công {quantity:,} {symbol} tại giá {price:,.0f} đ. Thu về {net_rev:,.0f} đ",
            "tx": tx
        }

    def get_summary(self, current_prices: dict = None) -> dict:
        """
        Tính toán tổng tài sản, lãi/lỗ toàn danh mục và chi tiết từng mã.
        """
        current_prices = current_prices or {}
        stock_value = 0.0
        holdings_detail = []

        for sym, h in self.holdings.items():
            qty = h["quantity"]
            avg = h["avg_price"]
            curr_p = current_prices.get(sym, avg)
            val = qty * curr_p
            pnl_vnd = (curr_p - avg) * qty
            pnl_pct = ((curr_p - avg) / avg * 100.0) if avg > 0 else 0.0

            stock_value += val
            holdings_detail.append({
                "Mã CP": sym,
                "Số Lượng": qty,
                "Giá Vốn (đ)": avg,
                "Giá Hiện Tại (đ)": curr_p,
                "Giá Trị (đ)": val,
                "Lãi/Lỗ (VNĐ)": pnl_vnd,
                "Lãi/Lỗ (%)": round(pnl_pct, 2)
            })

        total_assets = self.cash + stock_value
        total_pnl_vnd = total_assets - self.initial_cash
        total_pnl_pct = (total_pnl_vnd / self.initial_cash * 100.0) if self.initial_cash > 0 else 0.0

        return {
            "cash": self.cash,
            "stock_value": stock_value,
            "total_assets": total_assets,
            "total_pnl_vnd": total_pnl_vnd,
            "total_pnl_pct": round(total_pnl_pct, 2),
            "holdings": holdings_detail
        }
