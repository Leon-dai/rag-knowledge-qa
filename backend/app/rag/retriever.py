"""ChromaDB 向量存储 + 混合检索（向量 + BM25 → RRF 融合）"""
from langchain_chroma import Chroma
from app.config import settings
from app.kb.embedder import get_embeddings
from app.model_settings import get_current_embedding_model

_vector_store: Chroma | None = None
_current_embedding_model: str | None = None


def get_vector_store() -> Chroma:
    """获取 ChromaDB 向量存储实例"""
    global _vector_store, _current_embedding_model
    current_model = get_current_embedding_model()

    if _vector_store is not None and _current_embedding_model != current_model:
        _vector_store = None

    if _vector_store is None:
        embeddings = get_embeddings()
        _vector_store = Chroma(
            collection_name=settings.chroma_collection_name,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
            collection_metadata={"hnsw:space": "cosine"},
        )
        _current_embedding_model = current_model

    return _vector_store


def reset_vector_store():
    """强制重置向量存储实例"""
    global _vector_store, _current_embedding_model
    _vector_store = None
    _current_embedding_model = None


def tag_embedding_model():
    """标记 ChromaDB collection 使用的 Embedding 模型"""
    try:
        vs = get_vector_store()
        vs._collection.modify(metadata={"embedding_model": get_current_embedding_model()})
    except Exception:
        pass


def check_embedding_model_mismatch() -> dict:
    """检查当前 Embedding 模型与已存储向量是否匹配"""
    try:
        vs = get_vector_store()
        stored = vs._collection.metadata.get("embedding_model") if vs._collection.metadata else None
    except Exception:
        stored = None
    current = get_current_embedding_model()
    if stored is None:
        tag_embedding_model()
        return {"compatible": True, "stored": None, "current": current, "warning": ""}
    if stored != current:
        return {"compatible": False, "stored": stored, "current": current,
                "warning": f"Embedding模型不匹配！当前用 {current}，已有向量用 {stored} 生成。"}
    return {"compatible": True, "stored": stored, "current": current, "warning": ""}


def similarity_search_with_score(query: str, k: int = 8):
    """向量语义搜索"""
    vector_store = get_vector_store()
    return vector_store.similarity_search_with_score(query, k=k)


# ==================== 混合检索 + RRF 融合 ====================

def _rrf_fusion(
    vector_results: list,
    bm25_results: list,
    k: int = 60,
    vector_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> list:
    """RRF (Reciprocal Rank Fusion) 融合两路检索结果（支持加权）

    RRF Score = vector_weight * Σ 1/(k + rank_vector) + bm25_weight * Σ 1/(k + rank_bm25)

    Args:
        vector_results: [(Document, score), ...] 向量检索结果
        bm25_results: [Document, ...] BM25 检索结果
        k: RRF 平滑参数（默认60）
        vector_weight: 向量检索权重（0-1）
        bm25_weight: BM25 检索权重（0-1）

    Returns:
        [(Document, rrf_score), ...] 按 RRF 分数降序
    """
    rrf_scores = {}
    doc_map = {}  # 用于存储文档引用

    # 向量路（加权）
    for rank, (doc, _) in enumerate(vector_results):
        doc_id = _doc_key(doc)
        doc_map[doc_id] = doc
        base_score = 1.0 / (k + rank + 1)
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + vector_weight * base_score

    # BM25 路（加权）
    for rank, doc in enumerate(bm25_results):
        doc_id = _doc_key(doc)
        doc_map[doc_id] = doc
        base_score = 1.0 / (k + rank + 1)
        rrf_scores[doc_id] = rrf_scores.get(doc_id, 0) + bm25_weight * base_score

    # 按 RRF 分数降序排列
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
    return [(doc_map[doc_id], rrf_scores[doc_id]) for doc_id in sorted_ids]


def _doc_key(doc) -> str:
    """文档唯一标识"""
    return f"{doc.metadata.get('doc_title', '')}:{doc.metadata.get('chunk_index', 0)}"


def hybrid_search(
    query: str,
    top_k: int = 8,
    vector_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> list:
    """混合检索：向量语义 + BM25 关键词 → 加权 RRF 融合

    参考: All-in-RAG Chapter 4 — 查询路由与分发

    Args:
        query: 查询文本
        top_k: 返回数量
        vector_weight: 向量检索权重（0-1，语义搜索时加大）
        bm25_weight: BM25 检索权重（0-1，精确匹配时加大）

    Returns:
        [(Document, rrf_score), ...] RRF 融合后的结果
    """
    from app.rag.bm25_retriever import bm25_search

    # 1. 向量检索
    vector_results = similarity_search_with_score(query, k=top_k)

    # 2. BM25 关键词检索
    try:
        bm25_results = bm25_search(query, k=top_k)
    except Exception:
        bm25_results = []

    # 3. 加权 RRF 融合
    if bm25_results:
        fused = _rrf_fusion(
            vector_results,
            bm25_results,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
        )
        return fused[:top_k]

    # BM25 不可用时仅用向量结果
    return [(doc, 1.0 - score) for doc, score in vector_results]  # 转为相似度分数
