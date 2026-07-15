"""Reranker 精排模块

对融合后的候选文档重新打分排序。
优先使用 Cross-Encoder，不可用时使用字符级匹配 fallback。
"""
import math
from typing import List, Tuple
from langchain_core.documents import Document
from app.logging import logger

_reranker = None


def get_reranker():
    """获取 Cross-Encoder 实例（可选，网络不通时用 fallback）"""
    global _reranker
    if _reranker is None:
        try:
            from sentence_transformers import CrossEncoder
            _reranker = CrossEncoder('BAAI/bge-reranker-large')
            logger.info("Reranker 已加载: BAAI/bge-reranker-large")
        except Exception:
            logger.info("Cross-Encoder 不可用，使用 fallback 评分")
            _reranker = False
    return _reranker if _reranker is not False else None


def _fallback_score(query: str, doc: Document) -> float:
    """Fallback 评分：基于字符匹配 + 文本长度归一化

    用于 Cross-Encoder 不可用时的替代方案。
    虽然不如 Cross-Encoder 精确，但结合 RRF 融合后质量可接受。
    """
    content = doc.page_content
    query_chars = set(query.replace(" ", ""))

    # 字符匹配度
    match_count = sum(1 for c in query_chars if c in content)
    match_ratio = match_count / max(len(query_chars), 1)

    # 连续片段匹配奖励
    bonus = 0.0
    for i in range(len(query) - 2):
        if query[i:i + 3] in content:
            bonus += 0.15
    for i in range(len(query) - 1):
        if query[i:i + 2] in content:
            bonus += 0.05

    score = 0.25 + match_ratio * 0.25 + min(bonus, 0.5)
    return min(score, 0.95)


def rerank(
    query: str,
    docs: List[Document],
    top_k: int = 3,
) -> List[Tuple[Document, float]]:
    """对文档列表重新打分排序

    Args:
        query: 用户查询
        docs: 候选文档列表
        top_k: 最终保留数量

    Returns:
        [(Document, score), ...] 按分数降序排列
    """
    if not docs:
        return []

    model = get_reranker()

    if model is not None:
        # Cross-Encoder 精排
        pairs = [(query, doc.page_content[:512]) for doc in docs]
        scores = model.predict(pairs)
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return ranked[:top_k]
    else:
        # Fallback 评分
        ranked = [(d, _fallback_score(query, d)) for d in docs]
        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:top_k]


def get_rerank_threshold() -> float:
    """获取相关度阈值"""
    model = get_reranker()
    return 0.3 if model else 0.60
