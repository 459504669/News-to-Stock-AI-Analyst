"""
API 请求/响应模型（Pydantic Schema）
"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime


# -------- 请求模型 --------

class AnalyzeRequest(BaseModel):
    """提交新闻分析请求"""
    title: str
    content: str
    source: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None


# -------- 响应模型 --------

class NewsItemOut(BaseModel):
    """新闻列表输出"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    summary: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[datetime] = None


class AnalysisOut(BaseModel):
    """分析结果输出"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    news_id: int
    title: Optional[str] = None   # 联表字段
    rating: int
    rating_label: str
    summary: str
    beneficiary_sectors: list[str]
    recommended_stocks: list[dict]
    risks: list[str]
    image_path: Optional[str] = None
