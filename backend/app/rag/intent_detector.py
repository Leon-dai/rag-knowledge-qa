"""意图检测模块

在检索前判断用户意图，决定是否需要搜索。
用轻量 LLM（qwen-turbo）做意图分类，速度快、成本低。

分类逻辑：
- CHITCHAT: 问候、闲聊、你是谁、创作任务（写/翻译/总结）——不需要搜索
- SEARCH: 需要查资料才能回答的问题——需要搜索
"""
from app.logging import logger

INTENT_PROMPT = """判断以下用户消息属于哪种意图。

用户消息："{question}"

分类规则（按优先级）：
1. 如果消息中包含任何事实性的信息需求（查数据、搜排名、找资料、问XX是什么/多少/怎么办理），即使语气口语化或带质疑，都属于 search
2. chitchat：纯问候（你好/嗨/在吗/谢谢/再见）、询问你自身（你是谁/你能做什么/你有什么功能）、创作任务（帮我写/翻译/润色/总结）、纯情绪表达
3. 不在这两类的，默认归为 search

只输出一个词：chitchat 或 search。不要输出任何其他内容。"""


class IntentDetector:
    """意图检测器"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        """懒加载轻量 LLM"""
        if self._llm is None:
            from app.rag.service import RAGService
            self._llm = RAGService._get_llm(model="qwen-turbo", streaming=False)
        return self._llm

    def detect(self, question: str) -> str:
        """检测用户意图

        Args:
            question: 用户消息

        Returns:
            "chitchat" 或 "search"
        """
        prompt = INTENT_PROMPT.format(question=question)

        try:
            llm = self._get_llm()
            response = llm.invoke(prompt)
            result = response.content.strip().lower()

            if "chitchat" in result:
                logger.info(f"意图检测 → 闲聊，跳过搜索")
                return "chitchat"
            else:
                logger.info(f"意图检测 → 需搜索")
                return "search"
        except Exception as e:
            logger.warning(f"意图检测失败，默认搜索: {e}")
            return "search"  # 失败时默认搜索，宁可多搜不可漏搜


# 全局实例
_detector: IntentDetector | None = None


def get_intent_detector() -> IntentDetector:
    """获取意图检测器单例"""
    global _detector
    if _detector is None:
        _detector = IntentDetector()
    return _detector


def detect_intent(question: str) -> str:
    """便捷函数：检测用户意图"""
    return get_intent_detector().detect(question)
