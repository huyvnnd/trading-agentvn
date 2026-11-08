"""
Strategy Engine & Backtester for Vietnam Stock Market.
Hỗ trợ thiết lập, tùy biến các chiến lược kỹ thuật và kiểm thử lịch sử (Backtest)
tuân thủ các quy tắc thị trường chứng khoán Việt Nam (Phí thuế, T+2.5, bước giá).
"""

import pandas as pd
import numpy as np
from datetime import datetime
from trading_agent.technical_analysis import TechnicalAnalysis

class BaseStrategy:
    def __init__(self, name: str, params: dict = None):
        self.name = name
        self.params = params or {}

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sinh cột 'signal': 1 (Mua), -1 (Bán), 0 (Không hành động)."""
        raise NotImplementedError

class SMACrossoverStrategy(BaseStrategy):
    """Chiến lược giao cắt đường trung bình SMA (Golden Cross / Death Cross)."""
    def __init__(self, fast_period: int = 20, slow_period: int = 50):
        super().__init__("SMA Crossover", {"fast_period": fast_period, "slow_period": slow_period})
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        fast_col = f"sma_{self.fast_period}"
        slow_col = f"sma_{self.slow_period}"

        df[fast_col] = df["close"].rolling(window=self.fast_period).mean()
        df[slow_col] = df["close"].rolling(window=self.slow_period).mean()

        df["signal"] = 0
        cond_buy = (df[fast_col] > df[slow_col]) & (df[fast_col].shift(1) <= df[slow_col].shift(1))
        cond_sell = (df[fast_col] < df[slow_col]) & (df[fast_col].shift(1) >= df[slow_col].shift(1))

        df.loc[cond_buy, "signal"] = 1
        df.loc[cond_sell, "signal"] = -1
        return df

class RSIStrategy(BaseStrategy):
    """Chiến lược giao dịch theo RSI Quá bán / Quá mua."""
    def __init__(self, period: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        super().__init__("RSI Mean Reversion", {"period": period, "oversold": oversold, "overbought": overbought})
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = TechnicalAnalysis.calculate_indicators(df)
        df["signal"] = 0

        # Mua khi RSI thoát khỏi vùng quá bán đi lên
        cond_buy = (df["rsi"] > self.oversold) & (df["rsi"].shift(1) <= self.oversold)
        # Bán khi RSI cắt xuống từ vùng quá mua
        cond_sell = (df["rsi"] < self.overbought) & (df["rsi"].shift(1) >= self.overbought)

        df.loc[cond_buy, "signal"] = 1
        df.loc[cond_sell, "signal"] = -1
        return df

class MACDStrategy(BaseStrategy):
    """Chiến lược MACD giao cắt đường Signal."""
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__("MACD Crossover", {"fast": fast, "slow": slow, "signal": signal})

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = TechnicalAnalysis.calculate_indicators(df)
        df["signal"] = 0

        cond_buy = (df["macd"] > df["macd_signal"]) & (df["macd"].shift(1) <= df["macd_signal"].shift(1))
        cond_sell = (df["macd"] < df["macd_signal"]) & (df["macd"].shift(1) >= df["macd_signal"].shift(1))

        df.loc[cond_buy, "signal"] = 1
        df.loc[cond_sell, "signal"] = -1
        return df

class BollingerBandsStrategy(BaseStrategy):
    """Chiến lược Bollinger Bands bật ngược hỗ trợ dải dưới hoặc vượt dải trên."""
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__("Bollinger Bands Reversal", {"period": period, "std_dev": std_dev})

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = TechnicalAnalysis.calculate_indicators(df)
        df["signal"] = 0

        # Mua khi nến đóng cửa vượt lên trên Lower Band
        cond_buy = (df["close"] > df["bb_low"]) & (df["close"].shift(1) <= df["bb_low"].shift(1))
        # Bán khi nến chạm Upper Band
        cond_sell = (df["close"] >= df["bb_high"])

        df.loc[cond_buy, "signal"] = 1
        df.loc[cond_sell, "signal"] = -1
        return df

class BreakoutVolumeStrategy(BaseStrategy):
    """Chiến lược Vượt đỉnh 20 phiên kèm Khối lượng bùng nổ."""
    def __init__(self, lookback: int = 20, volume_factor: float = 1.5):
        super().__init__("Breakout & Volume Surge", {"lookback": lookback, "volume_factor": volume_factor})
        self.lookback = lookback
        self.volume_factor = volume_factor

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = TechnicalAnalysis.calculate_indicators(df)
        df["signal"] = 0

        high_prev = df["high"].shift(1).rolling(window=self.lookback).max()
        vol_sma = df["volume"].shift(1).rolling(window=20).mean()

        cond_buy = (df["close"] > high_prev) & (df["volume"] > vol_sma * self.volume_factor)
        # Bán khi gãy đường SMA20
        cond_sell = (df["close"] < df["sma_20"]) & (df["close"].shift(1) >= df["sma_20"].shift(1))

        df.loc[cond_buy, "signal"] = 1
        df.loc[cond_sell, "signal"] = -1
        return df

class CustomRuleStrategy(BaseStrategy):
    """
    Chiến lược Tùy biến theo yêu cầu người dùng:
    Cho phép kết hợp đa chỉ báo (RSI, MA, MACD, Volume, Giá).
    """
    def __init__(self, name: str = "Chiến lược Tùy Biến", config: dict = None):
        super().__init__(name, config or {})
        self.config = config or {
            "rsi_buy_max": 40.0,
            "rsi_sell_min": 70.0,
            "require_price_above_sma20": True,
            "require_volume_spike": False,
            "min_vol_ratio": 1.2
        }

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = TechnicalAnalysis.calculate_indicators(df)
        df["signal"] = 0

        rsi_max = self.config.get("rsi_buy_max", 40.0)
        rsi_min = self.config.get("rsi_sell_min", 70.0)
        above_sma = self.config.get("require_price_above_sma20", True)
        vol_spike = self.config.get("require_volume_spike", False)
        min_vol = self.config.get("min_vol_ratio", 1.2)

        # Điều kiện Mua
        buy_cond = (df["rsi"] <= rsi_max)
        if above_sma and "sma_20" in df.columns:
            buy_cond = buy_cond & (df["close"] > df["sma_20"])
        if vol_spike and "vol_ratio" in df.columns:
            buy_cond = buy_cond & (df["vol_ratio"] >= min_vol)

        # Điều kiện Bán
        sell_cond = (df["rsi"] >= rsi_min)
        if above_sma and "sma_20" in df.columns:
            sell_cond = sell_cond | (df["close"] < df["sma_20"])

        df.loc[buy_cond, "signal"] = 1
        df.loc[sell_cond, "signal"] = -1
        return df


class StrategyBacktester:
    """
    Bộ máy mô phỏng kiểm thử giao dịch (Backtester) cho thị trường chứng khoán Việt Nam:
    - Vốn ban đầu (mặc định 100,000,000 VNĐ)
    - Phí giao dịch (0.15%) & Thuế bán cổ phiếu (0.10%)
    - Chu kỳ T+2.5 (chỉ cho phép bán sau tối thiểu 2 phiên giao dịch)
    - Tự động cắt lỗ (Stop Loss) và chốt lời (Take Profit)
    - Quản lý quy mô vị thế (Position Sizing)
    """
    def __init__(
        self,
        initial_capital: float = 100_000_000.0,
        stop_loss_pct: float = 7.0,
        take_profit_pct: float = 15.0,
        trailing_stop_pct: float = 0.0,
        commission_rate: float = 0.0015,
        tax_rate: float = 0.0010,
        t_plus: int = 2,
        position_size_pct: float = 1.0  # 1.0 = All in, 0.5 = 50% vốn cho mỗi lệnh
    ):
        self.initial_capital = initial_capital
        self.stop_loss_pct = stop_loss_pct / 100.0 if stop_loss_pct > 1.0 else stop_loss_pct
        self.take_profit_pct = take_profit_pct / 100.0 if take_profit_pct > 1.0 else take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct / 100.0 if trailing_stop_pct > 1.0 else trailing_stop_pct
        self.commission_rate = commission_rate
        self.tax_rate = tax_rate
        self.t_plus = t_plus
        self.position_size_pct = position_size_pct

    def run(self, df: pd.DataFrame, strategy: BaseStrategy) -> dict:
        """Chạy backtest trên dữ liệu giá OHLCV với chiến lược chỉ định."""
        if df.empty or len(df) < 5:
            return {"error": "Không đủ dữ liệu lịch sử để backtest"}

        # Tạo tín hiệu từ chiến lược
        df_sig = strategy.generate_signals(df)

        cash = self.initial_capital
        position = 0  # Số lượng cổ phiếu nắm giữ
        entry_price = 0.0
        entry_idx = 0
        peak_price = 0.0

        trades = []
        equity_records = []

        for i in range(len(df_sig)):
            row = df_sig.iloc[i]
            date = str(row["time"]) if "time" in row else str(i)
            close = float(row["close"])
            high = float(row.get("high", close))
            low = float(row.get("low", close))
            signal = int(row.get("signal", 0))

            # 1. Kiểm tra vị thế đang nắm giữ (Chốt lời, Cắt lỗ, Trailing Stop, hoặc Tín hiệu Bán)
            if position > 0:
                holding_days = i - entry_idx
                peak_price = max(peak_price, high)

                exit_reason = None
                exit_price = close

                # Kiểm tra T+2: chỉ được bán khi đã nắm giữ đủ số ngày T+
                can_sell = holding_days >= self.t_plus

                if can_sell:
                    # Kiểm tra Cắt lỗ (Stop Loss)
                    if self.stop_loss_pct > 0 and low <= entry_price * (1 - self.stop_loss_pct):
                        exit_price = entry_price * (1 - self.stop_loss_pct)
                        exit_reason = f"Cắt Lỗ (-{self.stop_loss_pct*100:.1f}%)"
                    # Kiểm tra Chốt lời (Take Profit)
                    elif self.take_profit_pct > 0 and high >= entry_price * (1 + self.take_profit_pct):
                        exit_price = entry_price * (1 + self.take_profit_pct)
                        exit_reason = f"Chốt Lời (+{self.take_profit_pct*100:.1f}%)"
                    # Trailing Stop
                    elif self.trailing_stop_pct > 0 and peak_price > entry_price and low <= peak_price * (1 - self.trailing_stop_pct):
                        exit_price = peak_price * (1 - self.trailing_stop_pct)
                        exit_reason = f"Trailing Stop (-{self.trailing_stop_pct*100:.1f}%)"
                    # Tín hiệu Bán từ chiến lược
                    elif signal == -1:
                        exit_price = close
                        exit_reason = "Tín hiệu Bán (Strategy Exit)"

                # Thực hiện lệnh Bán nếu thỏa điều kiện
                if exit_reason is not None:
                    gross_revenue = position * exit_price
                    fee = gross_revenue * self.commission_rate
                    tax = gross_revenue * self.tax_rate
                    net_revenue = gross_revenue - fee - tax

                    pnl_vnd = net_revenue - (position * entry_price)
                    pnl_pct = (exit_price - entry_price) / entry_price * 100.0

                    cash += net_revenue

                    trades.append({
                        "entry_date": df_sig.iloc[entry_idx]["time"].strftime("%Y-%m-%d") if hasattr(df_sig.iloc[entry_idx]["time"], "strftime") else str(df_sig.iloc[entry_idx]["time"]),
                        "exit_date": df_sig.iloc[i]["time"].strftime("%Y-%m-%d") if hasattr(df_sig.iloc[i]["time"], "strftime") else str(df_sig.iloc[i]["time"]),
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "shares": position,
                        "pnl_vnd": pnl_vnd,
                        "pnl_pct": pnl_pct,
                        "holding_days": holding_days,
                        "exit_reason": exit_reason
                    })

                    position = 0
                    entry_price = 0.0
                    peak_price = 0.0

            # 2. Kiểm tra vào lệnh Mua mới (nếu chưa có vị thế và có tín hiệu Mua)
            if position == 0 and signal == 1 and cash > close * 100:
                capital_to_use = cash * self.position_size_pct
                # Đơn vị lô chứng khoán Việt Nam: bội số của 100
                shares_to_buy = int(capital_to_use // (close * (1 + self.commission_rate) * 100)) * 100

                if shares_to_buy >= 100:
                    gross_cost = shares_to_buy * close
                    fee = gross_cost * self.commission_rate
                    total_cost = gross_cost + fee

                    cash -= total_cost
                    position = shares_to_buy
                    entry_price = close
                    entry_idx = i
                    peak_price = close

            # Ghi nhận giá trị tài sản ròng theo ngày (Equity)
            portfolio_val = cash + (position * close)
            equity_records.append({
                "time": row["time"],
                "portfolio_value": portfolio_val,
                "cash": cash,
                "holding_value": position * close,
                "close_price": close
            })

        df_equity = pd.DataFrame(equity_records)
        metrics = self._calculate_metrics(df_equity, trades)

        return {
            "strategy_name": strategy.name,
            "params": strategy.params,
            "initial_capital": self.initial_capital,
            "final_value": df_equity.iloc[-1]["portfolio_value"] if not df_equity.empty else self.initial_capital,
            "equity_curve": df_equity,
            "trades": trades,
            "metrics": metrics
        }

    def _calculate_metrics(self, df_equity: pd.DataFrame, trades: list) -> dict:
        """Tính toán các chỉ số đánh giá hiệu năng chiến lược."""
        if df_equity.empty:
            return {}

        init_val = self.initial_capital
        final_val = df_equity.iloc[-1]["portfolio_value"]
        total_return_pct = ((final_val - init_val) / init_val) * 100.0

        # Benchmark return (Buy & Hold)
        first_close = df_equity.iloc[0]["close_price"]
        last_close = df_equity.iloc[-1]["close_price"]
        benchmark_return_pct = ((last_close - first_close) / first_close) * 100.0 if first_close > 0 else 0.0

        # Max Drawdown
        values = df_equity["portfolio_value"].values
        cummax = np.maximum.accumulate(values)
        drawdowns = (values - cummax) / cummax
        max_drawdown_pct = abs(float(np.min(drawdowns))) * 100.0 if len(drawdowns) > 0 else 0.0

        # Win Rate & Profit Factor
        total_trades = len(trades)
        winning_trades = [t for t in trades if t["pnl_vnd"] > 0]
        losing_trades = [t for t in trades if t["pnl_vnd"] <= 0]

        win_rate = (len(winning_trades) / total_trades * 100.0) if total_trades > 0 else 0.0

        total_gain = sum(t["pnl_vnd"] for t in winning_trades)
        total_loss = abs(sum(t["pnl_vnd"] for t in losing_trades))
        profit_factor = (total_gain / total_loss) if total_loss > 0 else (99.0 if total_gain > 0 else 1.0)

        avg_gain_pct = (sum(t["pnl_pct"] for t in winning_trades) / len(winning_trades)) if winning_trades else 0.0
        avg_loss_pct = (sum(t["pnl_pct"] for t in losing_trades) / len(losing_trades)) if losing_trades else 0.0

        # Daily returns & Sharpe Ratio (annualized ~ 252 trading days)
        df_equity["daily_return"] = df_equity["portfolio_value"].pct_change().fillna(0)
        mean_ret = df_equity["daily_return"].mean()
        std_ret = df_equity["daily_return"].std()
        sharpe_ratio = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 0 else 0.0

        return {
            "total_return_pct": round(total_return_pct, 2),
            "benchmark_return_pct": round(benchmark_return_pct, 2),
            "alpha_pct": round(total_return_pct - benchmark_return_pct, 2),
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "total_trades": total_trades,
            "win_count": len(winning_trades),
            "loss_count": len(losing_trades),
            "avg_gain_pct": round(avg_gain_pct, 2),
            "avg_loss_pct": round(avg_loss_pct, 2)
        }
