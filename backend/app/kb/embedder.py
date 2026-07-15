"""DashScope Embedding 封装 + diskcache 缓存 + L2 归一化"""
import math
from typing import List
from langchain_community.embeddings import DashScopeEmbeddings
from app.config import settings
from app.model_settings import get_current_embedding_model
from app.cache import get_embedding_cache, set_embedding_cache


def _normalize(vector: List[float]) -> List[float]:
    """L2 归一化：使向量范数为 1.0

    ChromaDB 的 cosine 距离需要归一化向量，否则计算结果无意义。
    """
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


class CachedDashScopeEmbeddings(DashScopeEmbeddings):
    """带缓存 + L2归一化的 DashScope Embedding 封装

    1. 调用 DashScope API 获取原始向量
    2. L2 归一化（ChromaDB cosine 距离要求）
    3. diskcache 缓存归一化后的向量
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            model=get_current_embedding_model(),
            dashscope_api_key=settings.dashscope_api_key,
            *args,
            **kwargs,
        )

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """批量向量化，带缓存 + 归一化"""
        result = []
        texts_to_embed = []
        cache_indices = []

        # 先查缓存
        for i, text in enumerate(texts):
            cached = get_embedding_cache(text)
            if cached is not None:
                result.append(cached)
            else:
                result.append([])  # placeholder
                texts_to_embed.append(text)
                cache_indices.append(i)

        # 批量调用 API 获取未缓存的
        if texts_to_embed:
            batch_size = 25
            all_embeddings = []
            for j in range(0, len(texts_to_embed), batch_size):
                batch = texts_to_embed[j:j + batch_size]
                batch_embeddings = super().embed_documents(batch)
                # L2 归一化
                batch_embeddings = [_normalize(v) for v in batch_embeddings]
                all_embeddings.extend(batch_embeddings)

            for pos, (cache_idx, embedding) in enumerate(zip(cache_indices, all_embeddings)):
                result[cache_idx] = embedding
                set_embedding_cache(texts_to_embed[pos], embedding)

        return result

    def embed_query(self, text: str) -> List[float]:
        """单个查询向量化，带缓存 + 归一化"""
        cached = get_embedding_cache(text)
        if cached is not None:
            return cached
        embedding = super().embed_query(text)
        embedding = _normalize(embedding)
        set_embedding_cache(text, embedding)
        return embedding


def get_embeddings() -> CachedDashScopeEmbeddings:
    """获取 Embedding 实例"""
    return CachedDashScopeEmbeddings()
