"""
数据库模型 - SQLAlchemy ORM
支持 SQLite（默认）和 PostgreSQL
"""
from pathlib import Path
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime,
    Float, Boolean, JSON, Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from loguru import logger

Base = declarative_base()

# -------- 数据表定义 --------

class News(Base):
    """新闻表"""
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    summary = Column(Text)
    content = Column(Text)
    source = Column(String(100))
    url = Column(String(1000), unique=True, index=True)
    published_at = Column(DateTime, index=True)
    image_url = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_source_time", "source", "published_at"),
    )


class AnalysisResult(Base):
    """分析结果表"""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True)
    news_id = Column(Integer, index=True)
    rating = Column(Integer)           # 1~5 评分
    rating_label = Column(String(50))
    summary = Column(Text)            # AI 分析文本
    beneficiary_sectors = Column(JSON) # JSON 数组
    recommended_stocks = Column(JSON)  # JSON 数组
    risks = Column(JSON)              # JSON 数组
    time_horizon = Column(String(20))
    confidence = Column(Float)
    image_path = Column(String(1000))
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        Index("idx_news_id", "news_id", unique=True),
    )


# -------- 数据库管理 --------

class Database:
    """数据库管理类"""

    def __init__(self, url: str = "sqlite+aiosqlite:///./data/news_analyst.db"):
        self.engine = create_engine(url, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def create_tables(self):
        Base.metadata.create_all(bind=self.engine)
        logger.info("✅ 数据库表已创建")

    def get_session(self) -> Session:
        return self.SessionLocal()

    def close(self):
        self.engine.dispose()
