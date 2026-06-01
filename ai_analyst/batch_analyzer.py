"""
批量分析引擎 - 对多条新闻进行综合分析，生成市场日报
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from .llm_client import LLMClient
from .rating_system import RatingLevel


class BatchAnalysisResult:
    """批量新闻综合分析结果"""

    def __init__(
        self,
        overall_rating: int,
        overall_sentiment: str,
        market_summary: str,
        hot_sectors: list[str],
        hot_stocks: list[dict],
        key_risks: list[str],
        top_news: list[dict],
        time_horizon: str,
        time_horizon_label: str,
        confidence: float,
        news_count: int = 0,
        analyzed_at: Optional[datetime] = None,
    ):
        self.overall_rating = overall_rating
        self.overall_sentiment = overall_sentiment
        self.market_summary = market_summary
        self.hot_sectors = hot_sectors
        self.hot_stocks = hot_stocks
        self.key_risks = key_risks
        self.top_news = top_news
        self.time_horizon = time_horizon
        self.time_horizon_label = time_horizon_label
        self.confidence = confidence
        self.news_count = news_count
        self.analyzed_at = analyzed_at or datetime.now()

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["analyzed_at"] = self.analyzed_at.isoformat()
        return d


class BatchAnalyzer:
    """批量新闻分析器"""

    def __init__(
        self,
        llm_provider: str = "qwen",
        llm_model: str = "auto",
    ):
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        base = Path(__file__).parent / "prompts"
        self.system_prompt = (base / "batch_system_prompt.txt").read_text(encoding="utf-8")
        self.user_template = (base / "batch_analysis_template.txt").read_text(encoding="utf-8")

    def analyze(self, news_items: list) -> Optional[BatchAnalysisResult]:
        """
        对多条新闻进行综合分析。
        news_items: list[NewsItem] 或 list[dict]（至少含 title, summary, source, published_at）
        """
        # 过滤24小时内的新闻
        cutoff = datetime.now() - timedelta(hours=24)
        filtered = []
        for item in news_items:
            # 统一适配 NewsItem dataclass 和 dict
            if hasattr(item, "published_at"):
                pub = item.published_at
            else:
                pub = item.get("published_at")
            if isinstance(pub, datetime) and pub < cutoff:
                continue

            if hasattr(item, "title"):
                title = item.title
                summary = item.summary if hasattr(item, "summary") else ""
                source = item.source if hasattr(item, "source") else ""
            else:
                title = item.get("title", "")
                summary = item.get("summary", "")
                source = item.get("source", "")

            if title and len(title) > 5:
                filtered.append({
                    "title": title,
                    "summary": summary[:150] if summary else "",
                    "source": source,
                })

        if not filtered:
            logger.warning("没有找到24小时内符合条件的新闻")
            return None

        # 按重要性取前30条（避免超token限制）
        filtered = filtered[:30]

        # 构造新闻列表文本
        news_text = ""
        for i, news in enumerate(filtered, 1):
            news_text += (
                f"{i}. 【{news['source']}】{news['title']}\n"
            )
            if news["summary"]:
                news_text += f"   摘要: {news['summary']}\n"
            news_text += "\n"

        user_prompt = self.user_template.format(
            count=len(filtered),
            news_list=news_text.strip(),
        )

        try:
            raw = self.llm.chat(self.system_prompt, user_prompt)
            logger.info(f"批量分析完成，LLM返回 {len(raw)} 字符")
            return self._parse_json_result(raw, len(filtered))
        except Exception as e:
            logger.error(f"批量分析失败: {e}")
            return None

    def _parse_json_result(self, raw: str, news_count: int) -> Optional[BatchAnalysisResult]:
        """从 LLM 输出中解析 JSON"""
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = raw.strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            brace_match = re.search(r"\{[\s\S]*\}", json_str)
            if brace_match:
                try:
                    data = json.loads(brace_match.group())
                except json.JSONDecodeError:
                    logger.error("无法解析批量分析的 JSON 输出")
                    return None
            else:
                logger.error("无法解析批量分析的 JSON 输出")
                return None

        rating = int(data.get("overall_rating", 3))
        rating = max(1, min(5, rating))

        return BatchAnalysisResult(
            overall_rating=rating,
            overall_sentiment=data.get("overall_sentiment", ""),
            market_summary=data.get("market_summary", ""),
            hot_sectors=data.get("hot_sectors", []),
            hot_stocks=data.get("hot_stocks", []),
            key_risks=data.get("key_risks", []),
            top_news=data.get("top_news", []),
            time_horizon=data.get("time_horizon", "short"),
            time_horizon_label=data.get("time_horizon_label", "短期"),
            confidence=float(data.get("confidence", 0.5)),
            news_count=news_count,
        )
