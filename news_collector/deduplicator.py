"""
新闻去重器 - 基于标题相似度的智能去重
"""
from difflib import SequenceMatcher
from typing import Iterable
from loguru import logger
from .base import NewsItem


def similarity(a: str, b: str) -> float:
    """计算两段文本的相似度（0~1）"""
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(
    items: Iterable[NewsItem],
    threshold: float = 0.85,
) -> list[NewsItem]:
    """
    对新闻列表去重，相似度 > threshold 的视为重复。
    保留时间更新的那条。
    """
    items_list = list(items)
    seen: list[NewsItem] = []
    for item in items_list:
        dup = False
        for s in seen:
            if similarity(item.title, s.title) >= threshold:
                dup = True
                # 保留更晚的那条
                if item.published_at > s.published_at:
                    seen[seen.index(s)] = item
                break
        if not dup:
            seen.append(item)

    logger.info(f"去重完成：原始 {len(items_list)} 条 → 去重后 {len(seen)} 条")
    return seen
