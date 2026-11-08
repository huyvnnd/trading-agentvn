#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vietnam Quantitative Multi-Agent Hedge Fund & Algorithmic Trading Platform
Automated System Self-Diagnostic & Integrity Verification Suite (SDD Protocol)

Verification Areas:
1. Environment & Package Imports (packaging, modules)
2. DataEngine Feed Latency & VNINDEX Cache
3. Quantitative Technical Structure (Weinstein Stages, Minervini SEPA, RS Rating)
4. Three-Tier Screener Separation & Invariant Checks (NKG in Watchlist, 0 Stage 1/4 in Buy)
5. CIO Investment Committee Consensus & Invariant Guard (NKG 0%, VIC Buy, TCM Veto)
6. Streamlit Daemon Process & HTTP 200 Health Check
"""

import os
import sys
import time
import urllib.request
import pandas as pd
import numpy as np

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
vnstock_dir = os.path.join(PROJECT_ROOT, "vnstock")
if vnstock_dir not in sys.path:
    sys.path.insert(0, vnstock_dir)


class DiagnosticTestRunner:
    def __init__(self):
        self.results = []
        self.start_time = time.time()

    def record_result(self, name: str, passed: bool, message: str, elapsed: float):
        self.results.append({
            "name": name,
            "passed": passed,
            "message": message,
            "elapsed": elapsed
        })
        badge = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{badge}] {name:<45} ({elapsed:.3f}s) — {message}")

    def test_environment_and_packaging(self):
        t0 = time.time()
        try:
            import trading_agent
            from trading_agent.data_engine import DataEngine
            from trading_agent.technical_structure_agent import TechnicalStructureAgent
            from trading_agent.vsa_smc_screener import VSASMCScreener
            from trading_agent.cio_agent import CIOAgent
            
            pkg_version = getattr(trading_agent, "__version__", "2.0.0")
            msg = f"trading_agent v{pkg_version} imported successfully, Python {sys.version.split()[0]}"
            self.record_result("Packaging & Module Imports", True, msg, time.time() - t0)
            return True
        except Exception as e:
            self.record_result("Packaging & Module Imports", False, f"Import error: {e}", time.time() - t0)
            return False

    def test_data_engine_feed(self):
        t0 = time.time()
        try:
            from trading_agent.data_engine import DataEngine
            de = DataEngine()
            
            # Test batch quote retrieval
            symbols = ["VIC", "VHM", "HPG", "SSI", "FPT", "NKG", "VPB", "TCB", "MSN", "MWG"]
            quotes = de.get_batch_price_board(symbols)
            assert len(quotes) == len(symbols), f"Expected {len(symbols)} quotes, got {len(quotes)}"
            
            # Test VNINDEX history
            hist = de.get_history("VNINDEX", days=100)
            assert not hist.empty, "VNINDEX history is empty"
            assert len(hist) >= 30, f"Expected at least 30 bars, got {len(hist)}"
            
            elapsed = time.time() - t0
            assert elapsed < 12.0, f"DataEngine latency too high: {elapsed:.2f}s (network timeout)"
            
            msg = f"Retrieved {len(quotes)} quotes & VNINDEX {len(hist)} bars in {elapsed:.3f}s"
            self.record_result("DataEngine Feed & Latency", True, msg, elapsed)
            return True
        except Exception as e:
            self.record_result("DataEngine Feed & Latency", False, f"DataEngine error: {e}", time.time() - t0)
            return False

    def test_quantitative_structure(self):
        t0 = time.time()
        try:
            from trading_agent.data_engine import DataEngine
            from trading_agent.technical_structure_agent import TechnicalStructureAgent
            de = DataEngine()
            ts = TechnicalStructureAgent(de)
            
            res_vpb = ts.analyze_multi_timeframe_structure("VPB")
            assert "market_stage" in res_vpb, "Missing market_stage in VPB"
            assert "rs_info" in res_vpb, "Missing rs_info in VPB"
            assert "sepa_vcp" in res_vpb, "Missing sepa_vcp in VPB"
            assert "volume_profile" in res_vpb, "Missing volume_profile in VPB"
            
            res_nkg = ts.analyze_multi_timeframe_structure("NKG")
            assert res_nkg["market_stage"] == 1, f"NKG must be Stage 1 Accumulation, got Stage {res_nkg['market_stage']}"
            
            rs_score = res_vpb["rs_info"].get("rs_score", 0)
            sepa_score = res_vpb["sepa_vcp"].get("sepa_score", 0)
            msg = f"NKG: Stage {res_nkg['market_stage']} (Base) | VPB: Stage {res_vpb['market_stage']} RS={rs_score} SEPA={sepa_score}/8"
            self.record_result("Quantitative Structure & Formulas", True, msg, time.time() - t0)
            return True
        except Exception as e:
            self.record_result("Quantitative Structure & Formulas", False, f"Formula error: {e}", time.time() - t0)
            return False

    def test_three_tier_screener_separation(self):
        t0 = time.time()
        try:
            from trading_agent.data_engine import DataEngine
            from trading_agent.vsa_smc_screener import VSASMCScreener
            de = DataEngine()
            screener = VSASMCScreener(de)
            
            df_buy, df_watchlist, df_avoid = screener.scan_three_tier_universe()
            
            # Check Buy List: Must NOT contain any Stage 1 or Stage 4 stocks
            if not df_buy.empty and "Giai Đoạn" in df_buy.columns:
                stages = df_buy["Giai Đoạn"].astype(str).tolist()
                for st in stages:
                    assert "Stage 1" not in st, f"Constitutional Violation: Stage 1 found in Buy List: {st}"
                    assert "Stage 4" not in st, f"Constitutional Violation: Stage 4 found in Buy List: {st}"
            
            # Check Watchlist: Should contain Stage 1 accumulation or pullback
            if not df_watchlist.empty and "Mã CP" in df_watchlist.columns:
                wl_symbols = df_watchlist["Mã CP"].tolist()
                assert "NKG" in wl_symbols, f"Expected NKG in Watchlist, but not found. Got: {wl_symbols}"
                
            msg = f"Three-Tier Invariants Intact: Approved={len(df_buy)}, Watchlist={len(df_watchlist)} (incl NKG), Avoid={len(df_avoid)}"
            self.record_result("Three-Tier Screener Separation", True, msg, time.time() - t0)
            return True
        except Exception as e:
            self.record_result("Three-Tier Screener Separation", False, f"Screener invariant violation: {e}", time.time() - t0)
            return False

    def test_cio_consensus_and_regression_guard(self):
        t0 = time.time()
        try:
            from trading_agent.cio_agent import CIOAgent
            cio = CIOAgent()
            
            # 1. NKG Invariant: MUST NEVER have allocation > 0% (Stage 1)
            res_nkg = cio.evaluate_and_decide("NKG")
            assert res_nkg["allocation_pct"] == 0, f"CONSTITUTIONAL BREACH: NKG allocation is {res_nkg['allocation_pct']}%, MUST BE 0%!"
            assert "STAGE 1" in res_nkg["final_decision"].upper() or "THEO DÕI" in res_nkg["final_decision"].upper(), f"Unexpected NKG decision: {res_nkg['final_decision']}"
            
            # 2. VIC Invariant: Overvalued (MoS < -25%) & Disagreement -> MUST BE 0% Watchlist
            res_vic = cio.evaluate_and_decide("VIC")
            assert res_vic["allocation_pct"] == 0, f"CONSTITUTIONAL BREACH: VIC allocation is {res_vic['allocation_pct']}%, MUST BE 0% (Overvalued/Watchlist)!"
            assert "THEO DÕI" in res_vic["final_decision"].upper() or "TẠM DỪNG" in res_vic["final_decision"].upper(), f"Unexpected VIC decision: {res_vic['final_decision']}"

            # 3. HDB Invariant: Near Overhead Resistance Peak (22.5k vs 23.45k Pivot) -> MUST BE 0% Watchlist (No buying into resistance)
            res_hdb = cio.evaluate_and_decide("HDB")
            assert res_hdb["allocation_pct"] == 0, f"Expected HDB allocation == 0% (Near Resistance Peak), got {res_hdb['allocation_pct']}%"
            assert "THEO DÕI" in res_hdb["final_decision"].upper() or "TẠM DỪNG" in res_hdb["final_decision"].upper(), f"Expected Watchlist for HDB, got: {res_hdb['final_decision']}"
            
            # 4. TCM: Downtrend / Avoid
            res_tcm = cio.evaluate_and_decide("TCM")
            assert res_tcm["allocation_pct"] == 0, f"TCM allocation must be 0%, got {res_tcm['allocation_pct']}%"
            
            msg = f"CIO Invariants Verified: NKG=0% (Stage 1), VIC=0% (Overvalued Watchlist), HDB=0% (Near Peak Resistance Watchlist), TCM=0% (Veto)"
            self.record_result("CIO Consensus & Regression Guard", True, msg, time.time() - t0)
            return True
        except Exception as e:
            self.record_result("CIO Consensus & Regression Guard", False, f"CIO consensus error: {e}", time.time() - t0)
            return False

    def test_daemon_and_health_check(self):
        t0 = time.time()
        port = 8502
        url = f"http://localhost:{port}/_stcore/health"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TradingAgentVerifier/2.0"})
            with urllib.request.urlopen(req, timeout=3.0) as response:
                status_code = response.getcode()
                body = response.read().decode("utf-8").strip()
                assert status_code == 200, f"Expected status 200, got {status_code}"
                
            pid_file = os.path.join(PROJECT_ROOT, "trading_agent.pid")
            assert os.path.exists(pid_file), "PID file trading_agent.pid missing"
            with open(pid_file, "r") as f:
                pid = int(f.read().strip())
            
            msg = f"Daemon running on PID {pid}, port {port}, HTTP {status_code} ({body})"
            self.record_result("Streamlit Daemon & HTTP Health", True, msg, time.time() - t0)
            return True
        except Exception as e:
            self.record_result("Streamlit Daemon & HTTP Health", False, f"Health check failed on {url}: {e}", time.time() - t0)
            return False

    def test_desktop_launchers_and_gui(self):
        t0 = time.time()
        try:
            desktop_dir = os.path.expanduser("~/Desktop")
            icon_1 = os.path.join(desktop_dir, "TradingAgentVnstock.desktop")
            icon_2 = os.path.join(desktop_dir, "VietnamTradingAgent.desktop")
            start_sh = os.path.join(PROJECT_ROOT, "start_trading_agent.sh")
            logo_img = os.path.join(PROJECT_ROOT, "vnstock", "assets", "images", "vnstock_rgb_logo_trans_sqr.png")

            assert os.path.exists(icon_1) and os.access(icon_1, os.X_OK), f"Missing or non-executable {icon_1}"
            assert os.path.exists(icon_2) and os.access(icon_2, os.X_OK), f"Missing or non-executable {icon_2}"
            assert os.path.exists(start_sh) and os.access(start_sh, os.X_OK), f"Missing or non-executable {start_sh}"
            assert os.path.exists(logo_img), f"Missing logo {logo_img}"

            # Verify Exec and Icon paths inside desktop files
            with open(icon_1, "r", encoding="utf-8") as f:
                c1 = f.read()
                assert "start_trading_agent.sh" in c1, "icon_1 does not reference start_trading_agent.sh"
            with open(icon_2, "r", encoding="utf-8") as f:
                c2 = f.read()
                assert "start_trading_agent.sh" in c2, "icon_2 does not reference start_trading_agent.sh"

            msg = "Desktop launchers verified (TradingAgentVnstock & VietnamTradingAgent both executable with valid icons)"
            self.record_result("Desktop Launchers & 1-Click GUI", True, msg, time.time() - t0)
            return True
        except Exception as e:
            self.record_result("Desktop Launchers & 1-Click GUI", False, f"Desktop launcher error: {e}", time.time() - t0)
            return False

    def run_all(self):
        print("=" * 80)
        print("   KIỂM ĐỊNH TỰ ĐỘNG TOÀN DIỆN HỆ THỐNG TRADING AGENT VNSTOCK (SDD)")
        print("=" * 80)
        
        self.test_environment_and_packaging()
        self.test_data_engine_feed()
        self.test_quantitative_structure()
        self.test_three_tier_screener_separation()
        self.test_cio_consensus_and_regression_guard()
        self.test_daemon_and_health_check()
        self.test_desktop_launchers_and_gui()
        
        total_time = time.time() - self.start_time
        passed_count = sum(1 for r in self.results if r["passed"])
        total_count = len(self.results)
        
        print("=" * 80)
        if passed_count == total_count:
            print(f"🎉 TẤT CẢ {total_count}/{total_count} BỘ KIỂM ĐỊNH ĐÃ HOÀN TOÀN ĐẠT CHUẨN (100% PASS) TRONG {total_time:.2f}s!")
            print("🏛️ Hệ thống sẵn sàng cho hoạt động giao dịch định lượng chuẩn Institutional Grade.")
            print("=" * 80)
            return 0
        else:
            failed_count = total_count - passed_count
            print(f"⚠️ CẢNH BÁO: CÓ {failed_count}/{total_count} BỘ KIỂM ĐỊNH THẤT BẠI TRONG {total_time:.2f}s!")
            print("=" * 80)
            return 1


if __name__ == "__main__":
    runner = DiagnosticTestRunner()
    sys.exit(runner.run_all())
