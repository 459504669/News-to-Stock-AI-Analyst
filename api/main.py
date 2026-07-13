"""
FastAPI 主入口
提供 REST API 服务
"""
import asyncio
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy.orm import Session
from pathlib import Path
from . import schemas
from database.models import Database
from database.crud import (
    list_recent_news, list_recent_analyses,
    get_analysis_with_news, create_news, create_analysis,
    get_news_by_url, get_analysis_by_news_id,
)
from ai_analyst.analyzer import Analyzer
from visualizer.generator import Visualizer
from config.settings import settings
from utils.error_handler import setup_exception_handlers, ErrorHandler, LLMException


try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=[settings.api.rate_limit])
    HAS_SLOWAPI = True
except ImportError:
    logger.warning("slowapi 未安装，API 频率限制功能不可用")
    HAS_SLOWAPI = False


db_instance = Database()


latest_daily_report_path: Path = None
latest_daily_report_result = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_instance.create_tables()
    logger.info("数据库表已初始化")

    def _run_daily_analysis():
        global latest_daily_report_path, latest_daily_report_result
        try:
            from daily_pipeline import run_daily_pipeline
            logger.info("启动时自动运行每日分析...")
            report_path = run_daily_pipeline(theme=settings.api.daily_report_theme)
            if report_path:
                latest_daily_report_path = report_path
                latest_daily_report_result = _load_latest_report(report_path)
                logger.info("启动时每日分析完成")
        except Exception as e:
            logger.error(f"启动时每日分析失败: {e}")

    thread = threading.Thread(target=_run_daily_analysis, daemon=True)
    thread.start()

    yield
    db_instance.close()
    logger.info("数据库已关闭")


def _load_latest_report(path: Path) -> dict:
    return {
        "path": str(path),
        "filename": path.name,
        "exists": path.exists(),
    }


app = FastAPI(
    title="News-to-Stock AI Analyst API",
    description="AI 驱动的实时新闻股市分析工具 API - 自动抓取新闻、分析市场影响、生成日报图",
    version="0.4.0",
    lifespan=lifespan,
)

if HAS_SLOWAPI:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.api.cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def get_db():
    db = db_instance.get_session()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root():
    return {
        "name": "News-to-Stock AI Analyst",
        "version": "0.4.0",
        "status": "running",
        "endpoints": {
            "GET  /api/news/latest": "获取最新新闻列表",
            "POST /api/analyze": "提交新闻进行分析",
            "GET  /api/analysis/latest": "获取最新分析结果",
            "GET  /api/image/{id}": "获取分析图片",
            "POST /api/daily-report": "手动触发每日分析（抓取+分析+生成图）",
            "GET  /api/daily-report": "获取最新每日报告",
            "GET  /api/daily-report/image": "查看最新每日报告图片",
            "GET  /health": "健康检查",
            "GET  /docs": "API 文档（Swagger UI）",
        },
    }


@app.get("/health")
def health_check():
    try:
        db = db_instance.get_session()
        db.execute("SELECT 1")
        db.close()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)[:50]}"

    try:
        from ai_analyst.llm_client import LLMClient
        llm_status = "configured"
    except Exception as e:
        llm_status = f"error: {str(e)[:50]}"

    return {
        "status": "healthy",
        "database": db_status,
        "llm": llm_status,
        "rate_limit": settings.api.rate_limit,
        "timestamp": str(_load_latest_report(latest_daily_report_path) if latest_daily_report_path else "no report"),
    }


@app.get("/api/news/latest", response_model=list[schemas.NewsItemOut])
@limiter.limit("30/minute") if HAS_SLOWAPI else lambda x: x
def list_latest_news(request: Request, limit: int = 20, db: Session = Depends(get_db)):
    return list_recent_news(db, limit=limit)


@app.post("/api/analyze", response_model=schemas.AnalysisOut)
@limiter.limit("10/minute") if HAS_SLOWAPI else lambda x: x
def analyze_news(request: Request, payload: schemas.AnalyzeRequest, db: Session = Depends(get_db)):
    try:
        if payload.url:
            existing = get_news_by_url(db, payload.url)
            if existing:
                analysis = get_analysis_by_news_id(db, existing.id)
                if analysis:
                    return analysis

        news = create_news(
            db=db,
            title=payload.title,
            summary=payload.content[:200],
            content=payload.content,
            source=payload.source or "手动提交",
            url=payload.url or "",
            published_at=payload.published_at,
        )

        analyzer = Analyzer(
            llm_provider=settings.llm.provider,
            llm_model=settings.llm.model,
        )
        result = analyzer.analyze(
            title=payload.title,
            content=payload.content,
            source=payload.source or "手动提交",
            published_at=str(payload.published_at) if payload.published_at else "",
        )

        if not result:
            raise LLMException("AI 分析失败")

        viz = Visualizer(theme=settings.visualizer.theme)
        image_path = viz.generate(
            news_title=payload.title,
            news_source=payload.source or "手动提交",
            news_time=str(payload.published_at) if payload.published_at else "",
            rating_score=result.rating,
            analysis_summary=result.summary,
            beneficiary_sectors=result.beneficiary_sectors,
            recommended_stocks=result.recommended_stocks,
            risks=result.risks,
        )

        analysis = create_analysis(
            db=db,
            news_id=news.id,
            rating=result.rating,
            rating_label=result.rating_label,
            summary=result.summary,
            beneficiary_sectors=result.beneficiary_sectors,
            recommended_stocks=result.recommended_stocks,
            risks=result.risks,
            time_horizon=result.time_horizon,
            confidence=result.confidence,
            image_path=str(image_path),
        )

        return {
            "id": analysis.id,
            "news_id": news.id,
            "title": payload.title,
            "rating": result.rating,
            "rating_label": result.rating_label,
            "summary": result.summary,
            "beneficiary_sectors": result.beneficiary_sectors,
            "recommended_stocks": result.recommended_stocks,
            "risks": result.risks,
            "image_path": str(image_path),
        }
    except LLMException:
        raise
    except Exception as e:
        logger.error(f"分析接口异常: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.get("/api/analysis/latest", response_model=list[schemas.AnalysisOut])
@limiter.limit("30/minute") if HAS_SLOWAPI else lambda x: x
def list_latest_analyses(request: Request, limit: int = 20, db: Session = Depends(get_db)):
    return list_recent_analyses(db, limit=limit)


@app.get("/api/image/{analysis_id}")
@limiter.limit("60/minute") if HAS_SLOWAPI else lambda x: x
def get_analysis_image(request: Request, analysis_id: int, db: Session = Depends(get_db)):
    result = get_analysis_with_news(db, analysis_id)
    if not result or not result.get("image_path"):
        raise HTTPException(status_code=404, detail="图片未找到")
    path = Path(result["image_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="图片文件不存在")
    return FileResponse(path, media_type="image/png")


@app.post("/api/daily-report")
@limiter.limit("5/hour") if HAS_SLOWAPI else lambda x: x
def trigger_daily_report(request: Request):
    global latest_daily_report_path, latest_daily_report_result
    try:
        from daily_pipeline import run_daily_pipeline
        report_path = run_daily_pipeline(theme=settings.api.daily_report_theme)
        if report_path:
            latest_daily_report_path = report_path
            latest_daily_report_result = _load_latest_report(report_path)
            return {
                "success": True,
                "message": "每日分析完成",
                "image_path": str(report_path),
            }
        else:
            raise HTTPException(status_code=500, detail="每日分析失败，请检查日志")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"每日报告触发异常: {e}")
        raise HTTPException(status_code=500, detail=f"分析出错: {str(e)}")


@app.get("/api/daily-report")
def get_daily_report():
    if not latest_daily_report_path:
        raise HTTPException(status_code=404, detail="暂无每日报告，请等待启动分析完成或手动触发 POST /api/daily-report")
    return {
        "path": str(latest_daily_report_path),
        "filename": latest_daily_report_path.name,
        "exists": latest_daily_report_path.exists(),
    }


@app.get("/api/daily-report/image")
@limiter.limit("60/minute") if HAS_SLOWAPI else lambda x: x
def get_daily_report_image(request: Request):
    if not latest_daily_report_path or not latest_daily_report_path.exists():
        raise HTTPException(status_code=404, detail="暂无每日报告图片")
    return FileResponse(latest_daily_report_path, media_type="image/png")
