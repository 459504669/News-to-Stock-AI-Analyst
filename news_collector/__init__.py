"""
News Collector - 新闻采集模块
支持多源财经新闻抓取，智能去重
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# 支持的新闻源列表
AVAILABLE_SOURCES = [
    "cailianshe",      # 财联社
    "sina_finance",    # 新浪财经
    "eastmoney",       # 东方财富
    "yicai",          # 第一财经
    "xinhua_finance", # 新华社财经
    "cctv_finance",   # 央视财经
    "reuters",         # 路透社
    "bloomberg",       # 彭博社
    "ft",              # 金融时报
    "cnbc",           # CNBC
    "marketwatch",     # MarketWatch
    "wsj",            # 华尔街日报
]
