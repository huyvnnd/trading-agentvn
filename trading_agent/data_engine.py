"""
High-Speed Institutional Data Engine for Vietnam Stock Market.
Tích hợp tối ưu hóa tốc độ cao (< 0.4s/batch) từ vnstock (KBS / VCI),
hỗ trợ Batch Price Board, Master OHLCV Slice Cache, BCTC Chuyên Sâu (DuPont, Forensics, Bank NIM/CIR/LDR)
và Dữ liệu Phái sinh VN30F1M (Open Interest, Khối ngoại, Order Book).
"""

import sys
import os
import time
import pickle
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np

# Ensure vnstock module can be imported
VNSTOCK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vnstock"))
if VNSTOCK_PATH not in sys.path:
    sys.path.insert(0, VNSTOCK_PATH)

try:
    from vnstock import Quote, Listing, Company, Finance, Trading
    import vnstock.core.utils.client as vn_client
    # Enforce fast 6-second timeout on vnstock client so slow endpoints never hang the app
    _orig_perform = vn_client._perform_request
    def _fast_perform_request(url, headers, method, params, payload, timeout):
        return _orig_perform(url, headers, method, params, payload, min(timeout or 6, 6))
    vn_client._perform_request = _fast_perform_request
except ImportError:
    Quote = None
    Listing = None
    Company = None
    Finance = None
    Trading = None


DEFAULT_VN30 = [
    "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG",
    "MBB", "MSN", "MWG", "PLX", "POW", "SAB", "SHB", "SSB", "SSI", "STB",
    "TCB", "TPB", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
]

# Top 10 cổ phiếu trụ dẫn dắt điểm số VN30 và Phái sinh VN30F1M
VN30_PILLAR_WEIGHTS = {
    "FPT": 0.115, "TCB": 0.095, "HPG": 0.088, "VPB": 0.078, "ACB": 0.075,
    "MWG": 0.068, "MBB": 0.062, "VCB": 0.055, "VHM": 0.048, "VIC": 0.045,
    "STB": 0.045, "CTG": 0.040, "VNM": 0.038, "MSN": 0.035
}

SECTOR_MAP = {
    "ACB": "Ngân hàng", "BID": "Ngân hàng", "CTG": "Ngân hàng", "HDB": "Ngân hàng",
    "MBB": "Ngân hàng", "SHB": "Ngân hàng", "SSB": "Ngân hàng", "STB": "Ngân hàng",
    "TCB": "Ngân hàng", "TPB": "Ngân hàng", "VCB": "Ngân hàng", "VIB": "Ngân hàng",
    "VPB": "Ngân hàng", "LPB": "Ngân hàng", "EIB": "Ngân hàng", "OCB": "Ngân hàng",
    "MSB": "Ngân hàng", "NAB": "Ngân hàng",
    "SSI": "Chứng khoán", "VND": "Chứng khoán", "VCI": "Chứng khoán", "HCM": "Chứng khoán",
    "MBS": "Chứng khoán", "SHS": "Chứng khoán", "FTS": "Chứng khoán", "BSI": "Chứng khoán",
    "CTS": "Chứng khoán", "VIX": "Chứng khoán", "AGR": "Chứng khoán", "ORS": "Chứng khoán",
    "HPG": "Thép & Vật liệu", "HSG": "Thép & Vật liệu", "NKG": "Thép & Vật liệu", "VGS": "Thép & Vật liệu",
    "FPT": "Công nghệ & Viễn thông", "CMG": "Công nghệ & Viễn thông", "ELC": "Công nghệ & Viễn thông", "CTR": "Công nghệ & Viễn thông",
    "MWG": "Bán lẻ & Tiêu dùng", "FRT": "Bán lẻ & Tiêu dùng", "DGW": "Bán lẻ & Tiêu dùng", "PNJ": "Bán lẻ & Tiêu dùng",
    "MSN": "Bán lẻ & Tiêu dùng", "VNM": "Bán lẻ & Tiêu dùng", "SAB": "Bán lẻ & Tiêu dùng",
    "VHM": "Bất động sản", "VIC": "Bất động sản", "VRE": "Bất động sản", "KDH": "Bất động sản",
    "NLG": "Bất động sản", "DIG": "Bất động sản", "DXG": "Bất động sản", "PDR": "Bất động sản",
    "NVL": "Bất động sản", "CEO": "Bất động sản", "HDC": "Bất động sản",
    "KBC": "BĐS Khu Công Nghiệp", "IDC": "BĐS Khu Công Nghiệp", "SZC": "BĐS Khu Công Nghiệp",
    "VGC": "BĐS Khu Công Nghiệp", "GVR": "BĐS Khu Công Nghiệp", "BCM": "BĐS Khu Công Nghiệp", "PHR": "BĐS Khu Công Nghiệp",
    "GAS": "Dầu khí & Năng lượng", "PLX": "Dầu khí & Năng lượng", "PVD": "Dầu khí & Năng lượng",
    "PVS": "Dầu khí & Năng lượng", "BSR": "Dầu khí & Năng lượng", "PVT": "Dầu khí & Năng lượng", "POW": "Dầu khí & Năng lượng",
    "DGC": "Hóa chất & Phân bón", "DCM": "Hóa chất & Phân bón", "DPM": "Hóa chất & Phân bón", "CSV": "Hóa chất & Phân bón",
    "GMD": "Cảng biển & Logistics", "HAH": "Cảng biển & Logistics", "VSC": "Cảng biển & Logistics", "VJC": "Hàng không & Du lịch",
    "VHC": "Thủy sản & Xuất khẩu", "ANV": "Thủy sản & Xuất khẩu", "IDI": "Thủy sản & Xuất khẩu",
    "TCM": "Dệt may & Xuất khẩu", "TNG": "Dệt may & Xuất khẩu", "MSH": "Dệt may & Xuất khẩu", "GIL": "Dệt may & Xuất khẩu"
}


class DataEngine:
    # Shared class-level caches so all agent instances share fetched data instantaneously
    _shared_symbols_df = None
    _shared_symbols_list = None
    _shared_vn30_list = None
    _shared_master_history = {}      # symbol -> (timestamp, df_1500_days)
    _shared_interval_history = {}    # (symbol, interval) -> (timestamp, df)
    _shared_price_board = {}         # symbol -> (timestamp, dict_row)
    _shared_overview_cache = {}      # symbol -> (timestamp, dict_overview)
    _cache_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "market_cache.pkl"))
    _disk_loaded = False

    def __init__(self, default_source: str = "KBS"):
        self.default_source = default_source
        self._load_disk_cache_once()

    @classmethod
    def _load_disk_cache_once(cls):
        if cls._disk_loaded:
            return
        cls._disk_loaded = True
        try:
            if os.path.exists(cls._cache_file):
                with open(cls._cache_file, "rb") as f:
                    saved = pickle.load(f)
                now_ts = time.time()
                # Keep history & BCTC overview cache valid for 12 hours on disk
                for k, (ts, df) in saved.get("master_history", {}).items():
                    if now_ts - ts < 43200 and isinstance(df, pd.DataFrame) and not df.empty:
                        cls._shared_master_history[k] = (ts, df)
                for k, (ts, info) in saved.get("overview_cache", {}).items():
                    if now_ts - ts < 43200 and isinstance(info, dict):
                        cls._shared_overview_cache[k] = (ts, info)
                if saved.get("symbols_df") is not None:
                    cls._shared_symbols_df = saved.get("symbols_df")
        except Exception:
            pass

    @classmethod
    def save_disk_cache(cls):
        try:
            os.makedirs(os.path.dirname(cls._cache_file), exist_ok=True)
            with open(cls._cache_file, "wb") as f:
                pickle.dump({
                    "master_history": cls._shared_master_history,
                    "overview_cache": cls._shared_overview_cache,
                    "symbols_df": cls._shared_symbols_df
                }, f)
        except Exception:
            pass

    def get_all_symbols(self) -> pd.DataFrame:
        """Lấy danh sách toàn bộ mã cổ phiếu niêm yết trên thị trường (HOSE, HNX, UPCOM)."""
        if DataEngine._shared_symbols_df is not None:
            return DataEngine._shared_symbols_df

        for src in ["KBS", "VCI"]:
            try:
                if Listing is not None:
                    listing = Listing(source=src)
                    df = listing.all_symbols()
                    if df is not None and not df.empty:
                        DataEngine._shared_symbols_df = df
                        return df
            except Exception:
                continue

        data = [{"symbol": s, "organ_name": f"Công ty CP {s}"} for s in DEFAULT_VN30]
        return pd.DataFrame(data)

    def get_all_symbols_list(self) -> list:
        """Lấy danh sách tất cả các mã (strings) đã sắp xếp cho dropdown và tìm kiếm."""
        if DataEngine._shared_symbols_list is not None:
            return DataEngine._shared_symbols_list

        df = self.get_all_symbols()
        if df is not None and not df.empty and "symbol" in df.columns:
            syms = sorted(list(set(
                [str(s).strip().upper() for s in df["symbol"].dropna().unique() if len(str(s).strip()) >= 3]
                + DEFAULT_VN30 + list(SECTOR_MAP.keys()) + ["VN30F1M"]
            )))
            DataEngine._shared_symbols_list = syms
            return syms
        DataEngine._shared_symbols_list = DEFAULT_VN30
        return DEFAULT_VN30

    def is_valid_symbol(self, symbol: str) -> bool:
        """Kiểm tra mã cổ phiếu có tồn tại trên thị trường không."""
        if not symbol:
            return False
        sym = symbol.strip().upper()
        if sym in SECTOR_MAP or sym in DEFAULT_VN30 or sym in ["VNINDEX", "VN30", "VN30F1M", "HNXINDEX", "UPCOM"]:
            return True
        all_syms = self.get_all_symbols_list()
        return sym in all_syms

    def get_vn30_symbols(self) -> list:
        """Lấy danh sách 30 cổ phiếu rổ VN30."""
        if DataEngine._shared_vn30_list is not None:
            return DataEngine._shared_vn30_list
        DataEngine._shared_vn30_list = DEFAULT_VN30
        return DEFAULT_VN30

    def get_batch_price_board(self, symbols: list, force_reload: bool = False) -> dict:
        """
        Lấy bảng giá điện tử realtime cho 1 hoặc hàng trăm mã chỉ trong ~0.35 giây qua KBS.
        Trả về dict: {symbol: {...thông tin giá, trần, sàn, tham chiếu, khối ngoại mua/bán, dư mua/bán...}}
        """
        if not symbols:
            return {}
        now_ts = time.time()
        clean_syms = list(dict.fromkeys([s.strip().upper() for s in symbols if s]))

        missing_stocks = []
        missing_derivs = []
        results = {}

        for s in clean_syms:
            if not force_reload and s in DataEngine._shared_price_board:
                ts, cached_row = DataEngine._shared_price_board[s]
                if now_ts - ts < 45:  # 45s TTL for realtime board
                    results[s] = cached_row
                    continue
            if s in ["VN30F1M", "VN30F2M", "41I1GB000"] or s.startswith("VN30F"):
                missing_derivs.append(s)
            elif s not in ["VNINDEX", "VN30", "HNXINDEX", "UPCOM"]:
                missing_stocks.append(s)

        if Trading is not None:
            # 1. Fetch stock batch in 1 HTTP call
            if missing_stocks:
                try:
                    tr = Trading(symbol=missing_stocks[0], source="KBS")
                    df_pb = tr.price_board(missing_stocks)
                    if df_pb is not None and not df_pb.empty:
                        for _, row in df_pb.iterrows():
                            sym = str(row.get("symbol", "")).strip().upper()
                            if not sym:
                                continue
                            parsed = self._normalize_price_board_row(sym, row, is_derivative=False)
                            DataEngine._shared_price_board[sym] = (now_ts, parsed)
                            results[sym] = parsed
                except Exception:
                    pass

            # 2. Fetch derivative batch if requested
            if missing_derivs:
                try:
                    tr_d = Trading(symbol="VN30F1M", source="KBS")
                    df_d = tr_d.price_board(["VN30F1M"])
                    if df_d is not None and not df_d.empty:
                        row = df_d.iloc[0]
                        parsed = self._normalize_price_board_row("VN30F1M", row, is_derivative=True)
                        DataEngine._shared_price_board["VN30F1M"] = (now_ts, parsed)
                        results["VN30F1M"] = parsed
                except Exception:
                    pass

        return results

    def _normalize_price_board_row(self, symbol: str, row: pd.Series, is_derivative: bool = False) -> dict:
        def _flt(val, default=0.0):
            try:
                if pd.isna(val) or val is None or val == "":
                    return default
                return float(val)
            except Exception:
                return default

        price = _flt(row.get("close_price"))
        ref = _flt(row.get("reference_price"))
        ceil = _flt(row.get("ceiling_price"))
        floor = _flt(row.get("floor_price"))
        open_p = _flt(row.get("open_price"), ref)
        high_p = _flt(row.get("high_price"), price)
        low_p = _flt(row.get("low_price"), price)
        avg_p = _flt(row.get("average_price"), price)

        # Normalize unit if in thousands VND (stocks only)
        scale = 1.0
        if not is_derivative and symbol not in ["VNINDEX", "VN30", "HNXINDEX", "UPCOM"]:
            ref_check = price if price > 0 else ref
            if 0 < ref_check < 1000:
                scale = 1000.0

        price *= scale
        ref *= scale
        ceil *= scale
        floor *= scale
        open_p *= scale
        high_p *= scale
        low_p *= scale
        avg_p *= scale

        if price <= 0 and ref > 0:
            price = ref

        chg = price - ref if ref > 0 else _flt(row.get("price_change")) * scale
        chg_pct = ((price - ref) / ref * 100.0) if ref > 0 else _flt(row.get("percent_change"))

        vol = int(_flt(row.get("volume_accumulated")))
        val_vnd = _flt(row.get("total_value"))
        f_buy = int(_flt(row.get("foreign_buy_volume")))
        f_sell = int(_flt(row.get("foreign_sell_volume")))
        oi = int(_flt(row.get("open_interest")))

        bid_vol_total = int(_flt(row.get("bid_vol_1")) + _flt(row.get("bid_vol_2")) + _flt(row.get("bid_vol_3")))
        ask_vol_total = int(_flt(row.get("ask_vol_1")) + _flt(row.get("ask_vol_2")) + _flt(row.get("ask_vol_3")))

        return {
            "symbol": symbol,
            "exchange": str(row.get("exchange", "HOSE") or "HOSE"),
            "price": price,
            "ref_price": ref,
            "ceiling_price": ceil,
            "floor_price": floor,
            "open_price": open_p,
            "high_price": high_p,
            "low_price": low_p,
            "average_price": avg_p,
            "change": chg,
            "change_pct": round(chg_pct, 2),
            "volume": vol,
            "total_value_vnd": val_vnd,
            "foreign_buy_volume": f_buy,
            "foreign_sell_volume": f_sell,
            "foreign_net_volume": f_buy - f_sell,
            "foreign_net_value_vnd": (f_buy - f_sell) * price,
            "bid_price_1": _flt(row.get("bid_price_1")) * scale,
            "bid_vol_1": int(_flt(row.get("bid_vol_1"))),
            "ask_price_1": _flt(row.get("ask_price_1")) * scale,
            "ask_vol_1": int(_flt(row.get("ask_vol_1"))),
            "bid_vol_total": bid_vol_total,
            "ask_vol_total": ask_vol_total,
            "open_interest": oi,
            "status": "success" if price > 0 else "error"
        }

    def get_history(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        days: int = 365,
        interval: str = "1D",
        force_reload: bool = False
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu lịch sử giá OHLCV siêu tốc nhờ cơ chế Master 1500-Day Cache & Slicing.
        Mọi truy vấn days=10, 30, 250, 365, 1500 của cùng 1 mã chỉ tốn 1 lần gọi mạng duy nhất (~0.35s),
        các lần cắt lát (slice) tiếp theo đạt tốc độ < 0.001s!
        """
        symbol = symbol.strip().upper()
        now = datetime.now()
        now_ts = time.time()

        if interval in ["1W", "1M"]:
            df_daily = self.get_history(symbol, days=max(days, 1500), interval="1D", force_reload=force_reload)
            if df_daily is None or df_daily.empty:
                return pd.DataFrame()
            df_r = df_daily.copy()
            df_r["time"] = pd.to_datetime(df_r["time"])
            df_r = df_r.set_index("time")
            rule = "W-FRI" if interval == "1W" else "ME"
            try:
                resampled = df_r.resample(rule).agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }).dropna().reset_index()
            except Exception:
                resampled = df_r.resample("M" if interval == "1M" else "W-FRI").agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                }).dropna().reset_index()
            return resampled

        if interval != "1D":
            return self._get_intraday_history(symbol, interval=interval, days=days, force_reload=force_reload)

        # Check master cache first (stores 1500 calendar days; live today price comes from batch price_board)
        if not force_reload and symbol in DataEngine._shared_master_history:
            ts, master_df = DataEngine._shared_master_history[symbol]
            if now_ts - ts < 43200 and not master_df.empty:  # 12-hour historical bar TTL
                return self._slice_history(master_df, start_date, end_date, days)

        # Fetch full 1500 days once so all downstream MTF (Monthly, Weekly, Daily, 200MA) share it
        fetch_days = max(days, 1500)
        fetch_start = (now - timedelta(days=fetch_days)).strftime("%Y-%m-%d")
        fetch_end = now.strftime("%Y-%m-%d")

        for src in ["KBS", "VCI"]:
            try:
                if Quote is not None:
                    quote = Quote(symbol=symbol, source=src)
                    df = quote.history(start=fetch_start, end=fetch_end)
                    if df is not None and not df.empty:
                        df = self._clean_ohlcv_df(symbol, df)
                        DataEngine._shared_master_history[symbol] = (now_ts, df)
                        return self._slice_history(df, start_date, end_date, days)
            except Exception:
                continue

        # Return stale disk cache if offline
        if symbol in DataEngine._shared_master_history:
            _, master_df = DataEngine._shared_master_history[symbol]
            return self._slice_history(master_df, start_date, end_date, days)

        return pd.DataFrame()

    def _clean_ohlcv_df(self, symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"])
            df = df.sort_values("time").drop_duplicates(subset=["time"], keep="last").reset_index(drop=True)

        is_index_or_deriv = symbol in ["VNINDEX", "VN30", "HNXINDEX", "UPCOM", "VN30F1M", "VN30F2M"] or symbol.startswith("VN30F")
        for col in ["open", "high", "low", "close"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                if not is_index_or_deriv and df[col].median() < 1000:
                    df[col] = df[col] * 1000.0

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
        return df

    def get_historical_data(
        self,
        symbol: str,
        days: int = 365,
        interval: str = "1D",
        start_date: str = None,
        end_date: str = None,
        force_reload: bool = False
    ) -> pd.DataFrame:
        """Alias cho get_history để tương thích với mọi module biểu đồ và hậu kiểm."""
        return self.get_history(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            days=days,
            interval=interval,
            force_reload=force_reload
        )

    def _slice_history(self, master_df: pd.DataFrame, start_date: str, end_date: str, days: int) -> pd.DataFrame:
        if master_df.empty:
            return pd.DataFrame()
        now = datetime.now()
        s_dt = pd.to_datetime(start_date) if start_date else pd.to_datetime((now - timedelta(days=days)).strftime("%Y-%m-%d"))
        e_dt = pd.to_datetime(end_date) + timedelta(days=1) if end_date else pd.to_datetime(now.strftime("%Y-%m-%d")) + timedelta(days=1)
        mask = (master_df["time"] >= s_dt) & (master_df["time"] <= e_dt)
        sliced = master_df.loc[mask].copy().reset_index(drop=True)
        if sliced.empty:
            return master_df.tail(max(10, int(days * 0.7))).copy().reset_index(drop=True)
        return sliced

    def _get_intraday_history(self, symbol: str, interval: str = "15m", days: int = 30, force_reload: bool = False) -> pd.DataFrame:
        key = (symbol, interval)
        now_ts = time.time()
        if not force_reload and key in DataEngine._shared_interval_history:
            ts, df = DataEngine._shared_interval_history[key]
            if now_ts - ts < 300 and not df.empty:
                return df.copy()

        now = datetime.now()
        start_str = (now - timedelta(days=days)).strftime("%Y-%m-%d")
        end_str = now.strftime("%Y-%m-%d")
        try:
            if Quote is not None:
                df = Quote(symbol=symbol, source="KBS").history(start=start_str, end=end_str, interval=interval)
                if df is not None and not df.empty:
                    df = self._clean_ohlcv_df(symbol, df)
                    DataEngine._shared_interval_history[key] = (now_ts, df)
                    return df.copy()
        except Exception:
            pass
        return pd.DataFrame()

    def get_intraday_ticks(self, symbol: str) -> pd.DataFrame:
        """Lấy sổ lệnh khớp từng tick trong phiên (kèm match_type Mua/Bán chủ động) qua KBS (~0.35s)."""
        symbol = symbol.strip().upper()
        try:
            if Quote is not None:
                df = Quote(symbol=symbol, source="KBS").intraday()
                if df is not None and not df.empty:
                    df = df.copy()
                    if "price" in df.columns:
                        df["price"] = pd.to_numeric(df["price"], errors="coerce")
                        is_idx = symbol in ["VNINDEX", "VN30", "VN30F1M"]
                        if not is_idx and df["price"].median() < 1000:
                            df["price"] = df["price"] * 1000.0
                    if "volume" in df.columns:
                        df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
                    return df
        except Exception:
            pass
        return pd.DataFrame()

    def get_latest_quote(self, symbol: str) -> dict:
        """
        Lấy thông tin giá mới nhất cực nhanh:
        1. Ưu tiên lấy từ Batch Price Board (KBS) nếu là cổ phiếu hoặc phái sinh (có đủ Khối ngoại, Trần/Sàn, Dư mua/bán).
        2. Kết hợp với lịch sử OHLCV đã cache để đảm bảo tốc độ < 0.01s khi đã có cache.
        """
        symbol = symbol.strip().upper()

        # 1. For stocks and VN30F1M, try fast Price Board first
        if symbol not in ["VNINDEX", "VN30", "HNXINDEX", "UPCOM"]:
            pb = self.get_batch_price_board([symbol])
            if symbol in pb and pb[symbol].get("price", 0) > 0:
                row = pb[symbol]
                return {
                    "symbol": symbol,
                    "price": row["price"],
                    "change": row["change"],
                    "change_pct": row["change_pct"],
                    "ref_price": row["ref_price"],
                    "ceiling_price": row["ceiling_price"],
                    "floor_price": row["floor_price"],
                    "volume": row["volume"],
                    "total_value_vnd": row["total_value_vnd"],
                    "foreign_buy_volume": row["foreign_buy_volume"],
                    "foreign_sell_volume": row["foreign_sell_volume"],
                    "foreign_net_volume": row["foreign_net_volume"],
                    "foreign_net_value_vnd": row["foreign_net_value_vnd"],
                    "bid_vol_total": row["bid_vol_total"],
                    "ask_vol_total": row["ask_vol_total"],
                    "open_interest": row["open_interest"],
                    "exchange": row["exchange"],
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "success"
                }

        # 2. Fallback to cached daily history (also handles VNINDEX / VN30)
        hist = self.get_history(symbol, days=15)
        if not hist.empty:
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last
            price = float(last["close"])
            prev_price = float(prev["close"])
            change_val = price - prev_price
            change_pct = (change_val / prev_price) * 100.0 if prev_price > 0 else 0.0
            return {
                "symbol": symbol,
                "price": price,
                "change": change_val,
                "change_pct": round(change_pct, 2),
                "ref_price": prev_price,
                "ceiling_price": round(prev_price * 1.07, 0),
                "floor_price": round(prev_price * 0.93, 0),
                "volume": int(last.get("volume", 0)),
                "total_value_vnd": float(last.get("volume", 0)) * price,
                "foreign_buy_volume": 0,
                "foreign_sell_volume": 0,
                "foreign_net_volume": 0,
                "foreign_net_value_vnd": 0.0,
                "bid_vol_total": 0,
                "ask_vol_total": 0,
                "open_interest": 0,
                "exchange": "HOSE",
                "time": str(last["time"]),
                "status": "success"
            }

        return {
            "symbol": symbol,
            "price": 0.0,
            "change": 0.0,
            "change_pct": 0.0,
            "ref_price": 0.0,
            "volume": 0,
            "time": "N/A",
            "status": "error"
        }

    def get_company_overview(self, symbol: str) -> dict:
        """
        Lấy thông tin tổng quan công ty và toàn bộ 30+ chỉ số tài chính chuyên sâu (KBS Finance.ratio + Company.overview).
        Tốc độ ~0.5s lần đầu, < 0.0001s từ bộ nhớ đệm.
        """
        symbol = symbol.strip().upper()
        now_ts = time.time()
        if symbol in DataEngine._shared_overview_cache:
            ts, cached_info = DataEngine._shared_overview_cache[symbol]
            if now_ts - ts < 43200:
                return cached_info.copy()

        quote = self.get_latest_quote(symbol)
        curr_price = float(quote.get("price", 0.0))

        info = {
            "symbol": symbol,
            "organ_name": symbol,
            "industry": SECTOR_MAP.get(symbol, "Doanh nghiệp Niêm yết"),
            "exchange": quote.get("exchange", "HOSE"),
            "current_price": curr_price,
            "market_cap": "N/A",
            "market_cap_billion": 0.0,
            "outstanding_shares": 0,
            "pe": None,
            "pb": None,
            "ps": None,
            "ev_ebitda": None,
            "ev_ebit": None,
            "eps": None,
            "bvps": None,
            "dividend_yield": 0.0,
            "beta": 1.0,
            "roe": None,
            "roa": None,
            "roce": None,
            "gross_margin": None,
            "ebit_margin": None,
            "net_margin": None,
            "debt_to_equity": None,
            "liabilities_to_equity": None,
            "current_ratio": None,
            "quick_ratio": None,
            "cash_ratio": None,
            "interest_coverage": None,
            "asset_turnover": None,
            "equity_turnover": None,
            "revenue_growth_yoy": None,
            "profit_growth_yoy": None,
            "prev_profit_growth_yoy": None,
            # Banking metrics
            "is_bank": SECTOR_MAP.get(symbol) == "Ngân hàng",
            "nim": None,
            "cir": None,
            "ldr": None,
            "credit_growth": None,
            "equity_to_assets": None,
            # Cash flow forensics
            "accrual_ratio_cf": None,
            "cash_to_income": None,
            "cash_return_on_equity": None,
            "cps": None,
            "target_price": None,
            "company_profile": "",
            "latest_quarter": "N/A"
        }

        # 1. Fetch KBS Finance.ratio() (fast ~0.45s, 32-54 rows of rich fundamentals)
        try:
            if Finance is not None:
                f = Finance(symbol=symbol, source="KBS")
                r = f.ratio()
                if r is not None and not r.empty and "item_id" in r.columns:
                    period_cols = [c for c in r.columns if c not in ["item", "item_id", "item_en", "period"]]
                    if period_cols:
                        info["latest_quarter"] = str(period_cols[0])
                    ratio_map = {}
                    prev_map = {}
                    for _, row in r.iterrows():
                        iid = str(row.get("item_id", "")).strip()
                        if not iid:
                            continue
                        # Find first non-null period value
                        vals = []
                        for pc in period_cols:
                            v = row.get(pc)
                            if pd.notna(v) and v is not None and str(v).strip() != "":
                                try:
                                    vals.append(float(v))
                                except Exception:
                                    pass
                        if vals:
                            ratio_map[iid] = vals[0]
                            if len(vals) > 1:
                                prev_map[iid] = vals[1]

                    def _g(k, default=None):
                        return ratio_map.get(k, default)

                    info["eps"] = _g("trailing_eps")
                    info["bvps"] = _g("book_value_per_share_bvps")
                    info["pe"] = _g("pe_ratio")
                    info["pb"] = _g("pb_ratio")
                    info["ps"] = _g("ps_ratio")
                    info["ev_ebitda"] = _g("ev_ebitda")
                    info["ev_ebit"] = _g("ev_ebit")
                    info["dividend_yield"] = _g("dividend_yield", 0.0)
                    info["beta"] = _g("beta", 1.0)
                    info["roe"] = _g("roe_trailling") if _g("roe_trailling") is not None else _g("roe")
                    info["roa"] = _g("roa_trailling") if _g("roa_trailling") is not None else _g("roa")
                    info["roce"] = _g("return_on_capital_employed_roce")
                    info["gross_margin"] = _g("gross_margin")
                    info["ebit_margin"] = _g("ebit_margin")
                    info["net_margin"] = _g("net_margin")

                    # Bank metrics
                    if _g("net_interest_margin_nim") is not None or _g("cost_income_ratio_cir") is not None:
                        info["is_bank"] = True
                        info["industry"] = "Ngân hàng"
                        info["nim"] = _g("net_interest_margin_nim")
                        info["cir"] = _g("cost_income_ratio_cir")
                        info["ldr"] = _g("outstanding_loans_customer_deposits")
                        info["credit_growth"] = _g("deposits_from_customers")
                        info["equity_to_assets"] = _g("equity_total_assets")
                        if info["equity_to_assets"] and info["equity_to_assets"] > 0:
                            info["debt_to_equity"] = round((100.0 - info["equity_to_assets"]) / info["equity_to_assets"], 2)

                    # Solvency & Turnovers for non-banks
                    if info["debt_to_equity"] is None and _g("debt_to_equity") is not None:
                        # KBS returns debt_to_equity as percentage (e.g., 39.42% = 0.39x)
                        de_raw = _g("debt_to_equity")
                        info["debt_to_equity"] = round(de_raw / 100.0, 2) if de_raw > 5 else round(de_raw, 2)
                    if _g("liabilities_to_equity") is not None:
                        le_raw = _g("liabilities_to_equity")
                        info["liabilities_to_equity"] = round(le_raw / 100.0, 2) if le_raw > 5 else round(le_raw, 2)

                    info["current_ratio"] = _g("short_term_ratio")
                    info["quick_ratio"] = _g("quick_ratio")
                    info["cash_ratio"] = _g("cash_ratio")
                    info["interest_coverage"] = _g("interest_coverage")
                    info["asset_turnover"] = _g("total_asset_turnover")
                    info["equity_turnover"] = _g("equity_turnover")

                    # Growth YoY
                    info["revenue_growth_yoy"] = _g("net_revenue") if _g("net_revenue") is not None else _g("net_interest_income")
                    info["profit_growth_yoy"] = _g("profit_after_tax_for_shareholders_of_the_parent_company")
                    if info["profit_growth_yoy"] is None:
                        info["profit_growth_yoy"] = _g("profit_before_tax")
                    info["prev_profit_growth_yoy"] = prev_map.get("profit_after_tax_for_shareholders_of_the_parent_company", prev_map.get("profit_before_tax"))

                    # Forensics
                    info["accrual_ratio_cf"] = _g("accrual_ratio_cf")
                    info["cash_to_income"] = _g("cash_to_income_2") if _g("cash_to_income_2") is not None else _g("cash_to_income")
                    info["cash_return_on_equity"] = _g("cash_return_on_equity")
                    info["cps"] = _g("cash_flow_per_share_cps")

                    # Keep official split-adjusted P/E and P/B from KBS, and normalize EPS/BVPS to post-split basis
                    if info["pe"] and info["pe"] > 0 and curr_price > 0:
                        info["pe"] = round(float(info["pe"]), 2)
                        info["eps"] = round(curr_price / info["pe"], 0)
                    elif curr_price > 0 and info["eps"] and info["eps"] > 0:
                        info["pe"] = round(curr_price / info["eps"], 2)

                    if info["pb"] and info["pb"] > 0 and curr_price > 0:
                        info["pb"] = round(float(info["pb"]), 2)
                        info["bvps"] = round(curr_price / info["pb"], 0)
                    elif curr_price > 0 and info["bvps"] and info["bvps"] > 0:
                        info["pb"] = round(curr_price / info["bvps"], 2)
        except Exception:
            pass

        # 2. Fetch KBS Company.overview() for company profile, charter capital, outstanding shares
        try:
            if Company is not None:
                c = Company(symbol=symbol, source="KBS")
                ov = c.overview()
                if ov is not None and not ov.empty:
                    row = ov.iloc[0]
                    if pd.notna(row.get("company_type")) and str(row.get("company_type")).strip():
                        if symbol not in SECTOR_MAP:
                            info["industry"] = str(row.get("company_type")).strip()
                    if pd.notna(row.get("exchange")):
                        info["exchange"] = str(row.get("exchange")).strip()
                    if pd.notna(row.get("business_model")):
                        info["company_profile"] = str(row.get("business_model")).strip()
                    out_shares = row.get("outstanding_shares")
                    if pd.notna(out_shares) and float(out_shares) > 0:
                        info["outstanding_shares"] = int(float(out_shares))
                        if curr_price > 0:
                            mcap_b = (info["outstanding_shares"] * curr_price) / 1e9
                            info["market_cap_billion"] = round(mcap_b, 1)
                            info["market_cap"] = f"{mcap_b:,.0f} tỷ VNĐ"
        except Exception:
            pass

        DataEngine._shared_overview_cache[symbol] = (now_ts, info)
        return info.copy()

    def prefetch_universe_parallel(self, symbols: list, days: int = 400):
        """
        Tải song song (Multi-threaded) bảng giá và lịch sử OHLCV cho danh sách cổ phiếu.
        Nhờ KBS + ThreadPoolExecutor, 35-65 mã được nạp đầy đủ chỉ trong ~1.5 - 2.5 giây!
        """
        if not symbols:
            return
        # 1. Batch price board in 1 call (0.35s)
        self.get_batch_price_board(symbols)

        # 2. Parallel history fetch for any symbol not yet in _shared_master_history
        now_ts = time.time()
        to_fetch = [
            s for s in symbols
            if s not in DataEngine._shared_master_history
            or (now_ts - DataEngine._shared_master_history[s][0] >= 43200)
        ]
        if to_fetch:
            with ThreadPoolExecutor(max_workers=10) as ex:
                futures = {ex.submit(self.get_history, s, days=days): s for s in to_fetch}
                for _ in as_completed(futures):
                    pass
            DataEngine.save_disk_cache()

    def get_market_overview(self) -> dict:
        """Lấy chỉ số VN-INDEX, VN30, Phái sinh VN30F1M và trạng thái chung của thị trường."""
        vnindex_quote = self.get_latest_quote("VNINDEX")
        vn30_quote = self.get_latest_quote("VN30")
        vn30f1m_quote = self.get_latest_quote("VN30F1M")

        return {
            "vnindex": vnindex_quote,
            "vn30": vn30_quote,
            "vn30f1m": vn30f1m_quote,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
