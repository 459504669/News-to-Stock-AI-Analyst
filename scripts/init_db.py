"""
数据库初始化脚本
用法：python scripts/init_db.py
"""
from pathlib import Path
import sys

# 将项目根目录加入 sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from loguru import logger
from database.models import Database, Base


def init_db(db_url: str = "sqlite+aiosqlite:///./data/news_analyst.db"):
    db = Database(url=db_url)
    db.create_tables()
    logger.info(f"✅ 数据库初始化完成：{db_url}")


if __name__ == "__main__":
    init_db()
