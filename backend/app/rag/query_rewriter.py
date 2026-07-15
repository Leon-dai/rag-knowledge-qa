"""查询改写模块

参考 All-in-RAG Chapter 4 — 查询构建与分发

功能：
1. 查询改写（Query Rewriting）：口语化问题 → 检索关键词
2. 多查询分解（Multi-Query Decomposition）：复合问题 → 多个子问题
3. 指代消解：「它」「那个」→ 具体实体
"""
from app.logging import logger


# ==================== 查询改写 ====================

REWRITE_SYSTEM_PROMPT = """你是一个查询改写专家。你的任务是把用户的模糊口语问题改写成适合搜索引擎检索的关键词。

规则：
1. 如果问题中有指代词（它、他、这个、那个、上次），根据对话历史还原为具体内容
2. 简写、缩写、俗称替换为正式名称
3. 输出2-3个不同角度的检索词，用「||」分隔
4. 每段检索词控制在30字以内
5. 如果用户问题已经很精确（如包含具体型号），直接返回原问题

只输出改写后的检索词，不要解释。"""

REWRITE_USER_PROMPT = """对话历史：
{history}

用户问题：{question}

改写后的检索词："""


# ==================== 多查询分解 ====================

DECOMPOSE_SYSTEM_PROMPT = """你是一个问题分解专家。你的任务是把复杂的复合问题拆解成多个简单的子问题。

规则：
1. 识别问题中的多个独立查询需求
2. 每个子问题应该是独立的、可检索的
3. 子问题数量控制在 2-4 个
4. 每个子问题用「||」分隔
5. 如果问题本身就是简单的，直接返回原问题

示例：
- 输入："iPhone 15 和 14 比有什么提升？"
- 输出："iPhone 15 规格参数||iPhone 14 规格参数||iPhone 15 vs 14 对比"

只输出分解后的子问题，不要解释。"""

DECOMPOSE_USER_PROMPT = """对话历史：
{history}

用户问题：{question}

分解后的子问题："""


class QueryRewriter:
    """查询改写器：支持改写 + 多查询分解"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        """懒加载轻量 LLM"""
        if self._llm is None:
            from app.rag.service import RAGService
            self._llm = RAGService._get_llm(model="qwen-turbo", streaming=False)
        return self._llm

    def _build_history_text(self, history: list[dict]) -> str:
        """构建对话历史文本（最近4轮）"""
        if not history:
            return "（无历史对话）"
        lines = []
        for msg in history[-8:]:  # 最多 4 轮（8 条消息）
            role = "用户" if msg["role"] == "user" else "助手"
            lines.append(f"{role}: {msg['content'][:200]}")
        return "\n".join(lines)

    def rewrite(self, question: str, history: list[dict] | None = None) -> list[str]:
        """改写用户问题为多个检索关键词

        Args:
            question: 用户原始问题
            history: 对话历史

        Returns:
            检索关键词列表，如 ["iPhone 15 Pro 参数", "苹果手机 A17芯片 配置"]
        """
        history_text = self._build_history_text(history or [])
        prompt = REWRITE_USER_PROMPT.format(
            history=history_text,
            question=question,
        )

        try:
            llm = self._get_llm()
            response = llm.invoke(prompt)
            result = response.content.strip()

            # 解析 «||» 分隔的关键词
            queries = [q.strip() for q in result.split("||") if q.strip()]
            if not queries:
                queries = [question]  # fallback：用原问题

            logger.info(f"查询改写: '{question[:50]}...' → {queries}")
            return queries
        except Exception as e:
            logger.warning(f"查询改写失败，使用原问题: {e}")
            return [question]

    def decompose(self, question: str, history: list[dict] | None = None) -> list[str]:
        """将复合问题分解为多个子问题（Multi-Query Decomposition）

        参考: All-in-RAG Chapter 4 - 多查询分解策略

        Args:
            question: 用户原始问题（可能是复合问题）
            history: 对话历史

        Returns:
            子问题列表，如 ["iPhone 15 参数", "iPhone 14 参数", "iPhone 15 vs 14 对比"]
        """
        history_text = self._build_history_text(history or [])
        prompt = DECOMPOSE_USER_PROMPT.format(
            history=history_text,
            question=question,
        )

        try:
            llm = self._get_llm()
            response = llm.invoke(prompt)
            result = response.content.strip()

            # 解析 «||» 分隔的子问题
            sub_queries = [q.strip() for q in result.split("||") if q.strip()]
            if not sub_queries:
                sub_queries = [question]  # fallback：用原问题

            logger.info(f"多查询分解: '{question[:50]}...' → {sub_queries}")
            return sub_queries
        except Exception as e:
            logger.warning(f"多查询分解失败，使用原问题: {e}")
            return [question]

    def smart_rewrite(self, question: str, history: list[dict] | None = None) -> list[str]:
        """智能改写：先尝试分解，再改写

        策略：
        1. 先用 decompose 分解复合问题
        2. 对每个子问题用 rewrite 改写为检索关键词

        Args:
            question: 用户原始问题
            history: 对话历史

        Returns:
            最终检索关键词列表（去重后）
        """
        # 1. 分解复合问题
        sub_queries = self.decompose(question, history)

        # 2. 对每个子问题改写
        all_queries = []
        for sub_q in sub_queries:
            rewritten = self.rewrite(sub_q, history)
            all_queries.extend(rewritten)

        # 3. 去重
        seen = set()
        unique_queries = []
        for q in all_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)

        logger.info(f"智能改写: '{question[:50]}...' → {unique_queries[:5]}")
        return unique_queries[:5]  # 最多返回5个


# 全局实例
_rewriter: QueryRewriter | None = None


def get_query_rewriter() -> QueryRewriter:
    """获取查询改写器单例"""
    global _rewriter
    if _rewriter is None:
        _rewriter = QueryRewriter()
    return _rewriter


def rewrite_query(question: str, history: list[dict] | None = None) -> list[str]:
    """便捷函数：改写查询（仅改写，不分解）"""
    return get_query_rewriter().rewrite(question, history)


def decompose_query(question: str, history: list[dict] | None = None) -> list[str]:
    """便捷函数：分解复合问题"""
    return get_query_rewriter().decompose(question, history)


def smart_rewrite_query(question: str, history: list[dict] | None = None) -> list[str]:
    """便捷函数：智能改写（分解 + 改写）"""
    return get_query_rewriter().smart_rewrite(question, history)
