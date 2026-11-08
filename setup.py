from setuptools import setup, find_packages

setup(
    name="trading-agent-vnstock",
    version="2.0.0",
    description="Vietnam Quantitative Multi-Agent Hedge Fund & Algorithmic Trading Platform",
    author="Antigravity Quantitative Investment Committee",
    packages=find_packages(include=["trading_agent*"]),
    python_requires=">=3.10",
    install_requires=[
        "streamlit>=1.30.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "plotly>=5.18.0",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "ta>=0.11.0",
        "psutil>=5.9.0",
    ],
    entry_points={
        "console_scripts": [
            "trading-agent = trading_agent.cli:main",
        ],
    },
)
