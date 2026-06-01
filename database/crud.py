"""
CRUD 操作 - 数据库读写
"""
from typing import Optional, list
from loguru import logger
from sqlalchemy.orm import Session
from .models import News, AnalysisResult


# -------- News 操作 --------

def get_news_by_url(db: Session, url: str) -> Optional[News]:
    return db.query(News).filter(News.url == url).first()


def create_news(db: Session, **kwargs) -> News:
    news = News(**kwargs)
    db.add(news)
    db.commit()
    db.refresh(news)
    return news


def list_recent_news(db: Session, limit: int = 50) -> list[News]:
    return (
        db.query(News)
        .order_by(News.published_at.desc())
        .limit(limit)
        .all()
    )


# -------- AnalysisResult 操作 --------

def get_analysis_by_news_id(db: Session, news_id: int) -> Optional[AnalysisResult]:
    return db.query(AnalysisResult).filter(AnalysisResult.news_id == news_id).first()


def create_analysis(db: Session, **kwargs) -> AnalysisResult:
    result = AnalysisResult(**kwargs)
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def list_recent_analyses(db: Session, limit: int = 50) -> list[AnalysisResult]:
    return (
        db.query(AnalysisResult)
        .order_by(AnalysisResult.created_at.desc())
        .limit(limit)
        .all()
    )


def get_analysis_with_news(db: Session, analysis_id: int) -> Optional[dict]:
    """联表查询，返回 news + analysis 合并字典"""
    from sqlalchemy import text
    sql = text("""
        SELECT n.title, n.source, n.published_at, n.url,
               a.rating, a.rating_label, a.summary,
               a.beneficiary_sectors, a.recommended_stocks,
               a.risks, a.time_horizon, a.confidence,
               a.image_path, a.created_at as analyzed_at
        FROM analysis_results a
        JOIN news n ON n.id = a.news_id
        WHERE a.id = :aid
    """)
    row = db.execute(sql, {"aid": analysis_id}).first()
    return dict(row._mapping) if row else None
