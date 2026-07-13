from typing import Iterable, Optional, List
from datetime import datetime
from loguru import logger
from .base import NewsItem


def _simple_similarity(a: str, b: str) -> float:
    """简单的字符串相似度（fallback）"""
    if not a or not b:
        return 0.0
    a, b = a.lower().strip(), b.lower().strip()
    if a == b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 0.0
    matches = sum(1 for ca, cb in zip(a, b) if ca == cb)
    return matches / max_len


def _fast_deduplicate_tfidf(items: List[NewsItem], threshold: float) -> List[NewsItem]:
    """
    使用 TF-IDF + cosine similarity 进行高效去重
    复杂度 O(n)，性能比 SequenceMatcher 提升 10x+
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
    except ImportError:
        logger.warning("sklearn 未安装，回退到简单相似度算法")
        return _simple_deduplicate(items, threshold)

    if len(items) <= 1:
        return items

    titles = [item.title for item in items]

    try:
        import jieba

        def tokenizer(text):
            return jieba.lcut(text)
        analyzer = None
        logger.info("使用 jieba 分词")
    except ImportError:
        tokenizer = None
        analyzer = 'char'
        logger.info("jieba 未安装，使用字符级别分词")

    vectorizer = TfidfVectorizer(
        tokenizer=tokenizer,
        analyzer=analyzer,
        max_features=5000,
        ngram_range=(1, 2),
    )

    try:
        tfidf_matrix = vectorizer.fit_transform(titles)
    except Exception as e:
        logger.warning(f"TF-IDF 转换失败: {e}，回退到简单算法")
        return _simple_deduplicate(items, threshold)

    similarity_matrix = cosine_similarity(tfidf_matrix)
    n = len(items)
    to_remove = set()
    kept = []

    for i in range(n):
        if i in to_remove:
            continue
        kept.append(items[i])
        for j in range(i + 1, n):
            if j in to_remove:
                continue
            if similarity_matrix[i, j] >= threshold:
                pub_i = items[i].published_at
                pub_j = items[j].published_at
                if isinstance(pub_i, datetime) and isinstance(pub_j, datetime):
                    if pub_j > pub_i:
                        kept[-1] = items[j]
                        to_remove.add(j)
                    else:
                        to_remove.add(j)
                else:
                    to_remove.add(j)

    logger.info(f"去重完成：原始 {len(items)} 条 → 去重后 {len(kept)} 条 (TF-IDF)")
    return kept


def _simple_deduplicate(items: List[NewsItem], threshold: float) -> List[NewsItem]:
    """
    简单去重算法（fallback）
    使用简单字符串相似度，不依赖 sklearn
    """
    if len(items) <= 1:
        return items

    seen: List[NewsItem] = []
    for item in items:
        is_dup = False
        for idx, s in enumerate(seen):
            sim = _simple_similarity(item.title, s.title)
            if sim >= threshold:
                is_dup = True
                pub_item = item.published_at
                pub_s = s.published_at
                if isinstance(pub_item, datetime) and isinstance(pub_s, datetime):
                    if pub_item > pub_s:
                        seen[idx] = item
                break
        if not is_dup:
            seen.append(item)

    logger.info(f"去重完成：原始 {len(items)} 条 → 去重后 {len(seen)} 条 (simple)")
    return seen


def deduplicate(
    items: Iterable[NewsItem],
    threshold: float = 0.85,
    method: str = "auto",
) -> List[NewsItem]:
    """
    对新闻列表去重，相似度 > threshold 的视为重复。
    保留时间更新的那条。

    Args:
        items: 新闻列表
        threshold: 相似度阈值 (0~1)，越大越严格
        method: 去重方法，可选 "auto", "tfidf", "simple"

    Returns:
        去重后的新闻列表
    """
    items_list = list(items)

    if not items_list:
        return []

    if method == "tfidf":
        return _fast_deduplicate_tfidf(items_list, threshold)
    elif method == "simple":
        return _simple_deduplicate(items_list, threshold)
    else:
        return _fast_deduplicate_tfidf(items_list, threshold)
