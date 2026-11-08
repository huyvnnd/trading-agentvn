"""
Root entrypoint for Streamlit Community Cloud and standalone cloud deployments.
Hỗ trợ triển khai độc lập 24/7 trên Streamlit Cloud, Render, Hugging Face Spaces, Fly.io, hoặc VPS.
"""
import sys
import os

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

vnstock_path = os.path.join(PROJECT_ROOT, "vnstock")
if os.path.exists(vnstock_path) and vnstock_path not in sys.path:
    sys.path.insert(0, vnstock_path)

# Chạy trực tiếp module app của trading_agent
import trading_agent.app
