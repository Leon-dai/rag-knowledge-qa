"""查询路由模块

参考 All-in-RAG Chapter 4 — 查询分发与路由

根据问题类型自动选择最优检索策略：
1. 精确匹配路由（Exact Match）：包含具体型号、人名、编号等 → 加重 BM25 权重
2. 语义搜索路由（Semantic）：开放性问题、概念性问题 → 加重向量权重
3. 对比分析路由（Comparison）：包含"对比"、"区别"、"比较"等 → 对每个实体分别检索
"""
import re
from enum import Enum
from app.logging import logger


class QueryType(Enum):
    """查询类型"""
    EXACT = "exact"        # 精确匹配：型号、人名、编号
    SEMANTIC = "semantic"  # 语义搜索：开放性、概念性问题
    COMPARISON = "comparison"  # 对比分析：A vs B


# 精确匹配特征：型号、编号、英文单词、数字
EXACT_PATTERNS = [
    r'\b[A-Z]{2,}\d+',      # 如 "iPhone15", "SKU12345"
    r'\b\d{4,}\b',           # 4位以上数字
    r'[A-Za-z]+[-_]?\d+',    # 如 "A17", "Pro-Max"
]

# 对比分析特征
COMPARISON_KEYWORDS = ["对比", "比较", "区别", "差异", "vs", "versus", "哪个好", "哪个更"]


class QueryRouter:
    """查询路由器：根据问题类型选择检索策略"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        """懒加载轻量 LLM"""
        if self._llm is None:
            from app.rag.service import RAGService
            self._llm = RAGService._get_llm(model="qwen-turbo", streaming=False)
        return self._llm

    def classify(self, question: str) -> QueryType:
        """基于规则 + LLM 的查询分类

        策略：
        1. 先用规则快速判断（精确匹配、对比分析）
        2. 规则不确定时用 LLM 判断
        """
        # 规则1：对比分析
        for keyword in COMPARISON_KEYWORDS:
            if keyword in question.lower():
                logger.info(f"查询路由 → 对比分析 (关键词: {keyword})")
                return QueryType.COMPARISON

        # 规则2：精确匹配
        for pattern in EXACT_PATTERNS:
            if re.search(pattern, question):
                logger.info(f"查询路由 → 精确匹配 (模式: {pattern})")
                return QueryType.EXACT

        # 规则3：LLM 判断（当规则不确定时）
        try:
            return self._llm_classify(question)
        except Exception as e:
            logger.warning(f"LLM 分类失败，默认语义搜索: {e}")
            return QueryType.SEMANTIC

    def _llm_classify(self, question: str) -> QueryType:
        """用 LLM 判断查询类型"""
        prompt = f"""判断以下问题属于哪种类型：

问题：{question}

类型选项：
1. exact - 精确匹配：包含具体型号、人名、编号、SKU等
2. semantic - 语义搜索：开放性问题、概念解释、使用方法等
3. comparison - 对比分析：多个事物的对比、区别、优劣

只输出类型（exact/semantic/comparison），不要解释。"""

        llm = self._get_llm()
        response = llm.invoke(prompt)
        result = response.content.strip().lower()

        if "exact" in result:
            logger.info("查询路由 → 精确匹配 (LLM)")
            return QueryType.EXACT
        elif "comparison" in result:
            logger.info("查询路由 → 对比分析 (LLM)")
            return QueryType.COMPARISON
        else:
            logger.info("查询路由 → 语义搜索 (LLM)")
            return QueryType.SEMANTIC

    def get_search_strategy(self, query_type: QueryType) -> dict:
        """根据查询类型返回检索策略

        Returns:
            策略配置，包含 bm25_weight 和 vector_weight
        """
        strategies = {
            QueryType.EXACT: {
                "bm25_weight": 0.8,
                "vector_weight": 0.2,
                "description": "精确匹配优先",
            },
            QueryType.SEMANTIC: {
                "bm25_weight": 0.3,
                "vector_weight": 0.7,
                "description": "语义搜索优先",
            },
            QueryType.COMPARISON: {
                "bm25_weight": 0.5,
                "vector_weight": 0.5,
                "description": "均衡检索",
            },
        }
        return strategies[query_type]


# 全局实例
_router: QueryRouter | None = None


def get_query_router() -> QueryRouter:
    """获取查询路由器单例"""
    global _router
    if _router is None:
        _router = QueryRouter()
    return _router


def classify_query(question: str) -> QueryType:
    """便捷函数：分类查询"""
    return get_query_router().classify(question)


def get_search_strategy(question: str) -> dict:
    """便捷函数：获取检索策略"""
    query_type = classify_query(question)
    return get_query_router().get_search_strategy(query_type)
