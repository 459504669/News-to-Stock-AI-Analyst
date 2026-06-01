"""
AI 分析引擎核心逻辑
调用 LLM 对新闻进行深度分析，解析结构化输出
"""
import json
import re
from pathlib import Path
from typing import Optional
from loguru import logger
from .llm_client import LLMClient
from .rating_system import RatingLevel


class NewsAnalysisResult:
    """新闻分析结果"""

    def __init__(
        self,
        rating: int,
        rating_label: str,
        summary: str,
        beneficiary_sectors: list[str],
        recommended_stocks: list[dict],
        risks: list[str],
        time_horizon: str,
        time_horizon_label: str,
        confidence: float,
    ):
        self.rating = rating
        self.rating_label = rating_label
        self.summary = summary
        self.beneficiary_sectors = beneficiary_sectors
        self.recommended_stocks = recommended_stocks
        self.risks = risks
        self.time_horizon = time_horizon
        self.time_horizon_label = time_horizon_label
        self.confidence = confidence

    def to_dict(self) -> dict:
        return self.__dict__


class Analyzer:
    """核心分析器"""

    def __init__(
        self,
        llm_provider: str = "openai",
        llm_model: str = "gpt-4o",
        system_prompt_path: Optional[Path] = None,
        template_path: Optional[Path] = None,
    ):
        self.llm = LLMClient(provider=llm_provider, model=llm_model)
        # 读取提示词模板
        base = Path(__file__).parent / "prompts"
        self.system_prompt = (
            system_prompt_path.read_text(encoding="utf-8")
            if system_prompt_path
            else (base / "analyst_system_prompt.txt").read_text(encoding="utf-8")
        )
        self.user_template = (
            template_path.read_text(encoding="utf-8")
            if template_path
            else (base / "analysis_template.txt").read_text(encoding="utf-8")
        )

    def analyze(self, title: str, content: str, source: str, published_at: str) -> Optional[NewsAnalysisResult]:
        """
        对单条新闻进行分析，返回结构化结果。
        """
        user_prompt = self.user_template.format(
            title=title,
            content=content[:3000],  # 截断，避免超 token 限制
            source=source,
            published_at=published_at,
        )

        try:
            raw = self.llm.chat(self.system_prompt, user_prompt)
            logger.debug(f"LLM 原始输出: {raw[:200]}...")
            return self._parse_json_result(raw)
        except Exception as e:
            logger.error(f"分析失败: {e}")
            return None

    def _parse_json_result(self, raw: str) -> Optional[NewsAnalysisResult]:
        """从 LLM 输出中解析 JSON"""
        # 提取 ```json ... ``` 或裸 JSON
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", raw)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接解析整个文本
            json_str = raw.strip()

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            # 尝试提取第一个 { ... } 块
            brace_match = re.search(r"\{[\s\S]*\}", json_str)
            if brace_match:
                data = json.loads(brace_match.group())
            else:
                logger.error("无法解析 LLM 输出的 JSON")
                return None

        return NewsAnalysisResult(
            rating=int(data.get("rating", 3)),
            rating_label=data.get("rating_label", RatingLevel.from_score(data.get("rating", 3)).label),
            summary=data.get("summary", ""),
            beneficiary_sectors=data.get("beneficiary_sectors", []),
            recommended_stocks=data.get("recommended_stocks", []),
            risks=data.get("risks", []),
            time_horizon=data.get("time_horizon", "short"),
            time_horizon_label=data.get("time_horizon_label", "短期"),
            confidence=float(data.get("confidence", 0.5)),
        )
