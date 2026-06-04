"""
批量分析引擎 - 对多条新闻进行综合分析，生成市场日报
v0.4.0: 两阶段分析 — 先用标题预筛选，再完整分析
"""
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional
from loguru import logger
from .llm_client import LLMClient
from .rating_system import RatingLevel

# 预筛选上限
PREFILTER_MAX = 50


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
        total_count: int = 0,
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
        self.total_count = total_count
        self.analyzed_at = analyzed_at or datetime.now()

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["analyzed_at"] = self.analyzed_at.isoformat()
        return d


class BatchAnalyzer:
    """批量新闻分析器（两阶段：预筛选 → 完整分析）"""

    def __init__(
        self,
        llm_provider: str = "qwen",
        llm_model: str = "auto",
    ):
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        base = Path(__file__).parent / "prompts"
        self.system_prompt = (base / "batch_system_prompt.txt").read_text(encoding="utf-8")
        self.user_template = (base / "batch_analysis_template.txt").read_text(encoding="utf-8")
        self.prefilter_sys = (base / "prefilter_system_prompt.txt").read_text(encoding="utf-8")
        self.prefilter_tpl = (base / "prefilter_template.txt").read_text(encoding="utf-8")

    def analyze(self, news_items: list) -> Optional[BatchAnalysisResult]:
        """
        两阶段分析：
        阶段1 — 将所有新闻标题发给大模型，筛选最重要的 PREFILTER_MAX 条
        阶段2 — 将筛选后的新闻（含摘要）发给大模型做完整分析
        """
        # ── 预处理：过滤24小时 + 统一格式 ──
        cutoff = datetime.now() - timedelta(hours=24)
        filtered = []
        for item in news_items:
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
                pub = item.published_at if hasattr(item, "published_at") else None
            else:
                title = item.get("title", "")
                summary = item.get("summary", "")
                source = item.get("source", "")
                pub = item.get("published_at")

            if title and len(title) > 5:
                # 提取发布日期（统一只显示 MM-DD，不显示时分）
                pub_str = ""
                if isinstance(pub, datetime):
                    pub_str = pub.strftime("%m-%d")
                elif isinstance(pub, str):
                    pub_str = pub[:16]

                filtered.append({
                    "title": title,
                    "summary": summary[:150] if summary else "",
                    "source": source,
                    "pub_time": pub_str,
                })

        if not filtered:
            logger.warning("没有找到24小时内符合条件的新闻")
            return None

        total_count = len(filtered)
        logger.info(f"24h内有效新闻: {total_count} 条")

        # ── 阶段1：预筛选（仅当超过上限时执行） ──
        if total_count > PREFILTER_MAX:
            logger.info(f"[阶段1] 新闻数 {total_count} > {PREFILTER_MAX}，调用大模型预筛选...")
            selected_indices = self._prefilter(filtered)
            if selected_indices:
                filtered = [filtered[i] for i in selected_indices if i < len(filtered)]
                logger.info(f"[阶段1] 筛选完成，选中 {len(filtered)} 条")
            else:
                logger.warning("[阶段1] 预筛选失败，fallback 到前 {PREFILTER_MAX} 条")
                filtered = filtered[:PREFILTER_MAX]
        else:
            logger.info(f"新闻数 {total_count} <= {PREFILTER_MAX}，跳过预筛选")

        # ── 阶段2：完整分析 ──
        analyze_count = len(filtered)
        logger.info(f"[阶段2] 发送 {analyze_count} 条新闻给大模型做完整分析...")

        news_text = ""
        for i, news in enumerate(filtered, 1):
            news_text += f"{i}. 【{news['source']}】{news['title']}"
            if news["pub_time"]:
                news_text += f" ({news['pub_time']})"
            news_text += "\n"
            if news["summary"]:
                news_text += f"   摘要: {news['summary']}\n"
            news_text += "\n"

        user_prompt = self.user_template.format(
            count=analyze_count,
            news_list=news_text.strip(),
        )

        try:
            raw = self.llm.chat(self.system_prompt, user_prompt)
            logger.info(f"[阶段2] 分析完成，LLM返回 {len(raw)} 字符")
            return self._parse_json_result(raw, analyze_count, total_count)
        except Exception as e:
            logger.error(f"[阶段2] 批量分析失败: {e}")
            return None

    def _prefilter(self, news_list: list) -> Optional[list[int]]:
        """
        阶段1：用标题列表让大模型筛选最重要的 PREFILTER_MAX 条。
        返回选中的索引列表（0-based），失败返回 None。
        """
        # 构造标题列表（轻量，不含摘要）
        title_text = ""
        for i, news in enumerate(news_list, 1):
            title_text += f"{i}. 【{news['source']}】{news['title']}\n"

        prompt = self.prefilter_tpl.format(
            count=len(news_list),
            news_list=title_text.strip(),
        )

        try:
            raw = self.llm.chat(self.prefilter_sys, prompt)
            logger.debug(f"预筛选原始输出: {raw[:500]}")

            # 提取所有数字（逗号分隔格式）
            nums = re.findall(r'\b(\d{1,3})\b', raw)
            if not nums:
                logger.warning("预筛选未提取到数字，fallback 到前50条")
                return None

            # 转为 0-based，去重，限制范围
            result = []
            seen = set()
            for idx in nums:
                i = int(idx) - 1  # 1-based → 0-based
                if 0 <= i < len(news_list) and i not in seen:
                    result.append(i)
                    seen.add(i)

            logger.info(f"预筛选完成，选中 {len(result)} 条")
            return result[:PREFILTER_MAX]

        except Exception as e:
            logger.error(f"预筛选失败: {e}")
            return None

    def _parse_json_result(self, raw: str, news_count: int, total_count: int = 0) -> Optional[BatchAnalysisResult]:
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
                    logger.error(f"JSON解析失败，原始输出片段: {raw[:200]}...")
                    return None
            else:
                logger.error(f"未找到有效JSON，原始输出片段: {raw[:200]}...")
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
            total_count=total_count,
        )
