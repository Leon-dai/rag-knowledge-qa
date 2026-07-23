"""联网搜索模块

支持 Tavily API 和 DuckDuckGo 两种搜索引擎。
提供统一的接口，支持降级策略。
"""
from typing import List, Dict, Optional
from dataclasses import dataclass
from app.logging import logger


@dataclass
class WebSearchResult:
    """联网搜索结果"""
    title: str
    url: str
    content: str
    score: float = 0.0


class WebSearcher:
    """联网搜索引擎"""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self._tavily_client = None
        self._ddg_search = None

    def _get_tavily_client(self):
        """获取 Tavily 客户端（懒加载）"""
        if self._tavily_client is None and self.api_key:
            try:
                from tavily import TavilyClient
                self._tavily_client = TavilyClient(api_key=self.api_key)
                logger.info("Tavily 客户端初始化成功")
            except Exception as e:
                logger.error(f"Tavily 客户端初始化失败: {e}")
                self._tavily_client = False
        return self._tavily_client if self._tavily_client is not False else None

    def _get_ddg_search(self):
        """获取 DuckDuckGo 搜索引擎（懒加载）"""
        if self._ddg_search is None:
            try:
                from duckduckgo_search import DDGS
                self._ddg_search = DDGS()
                logger.info("DuckDuckGo 搜索引擎初始化成功")
            except Exception as e:
                logger.error(f"DuckDuckGo 搜索引擎初始化失败: {e}")
                self._ddg_search = False
        return self._ddg_search if self._ddg_search is not False else None

    def search_tavily(self, query: str, max_results: int = 12) -> List[WebSearchResult]:
        """使用 Tavily 搜索"""
        client = self._get_tavily_client()
        if not client:
            logger.warning("Tavily 不可用")
            return []

        try:
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=max_results,
                auto_parameters=True  # 自动根据查询意图设置 time_range 等参数
            )

            results = []
            for item in response.get("results", []):
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    content=item.get("content", ""),
                    score=item.get("score", 0.0)
                ))

            logger.info(f"Tavily 搜索成功: {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"Tavily 搜索失败: {e}")
            return []

    def search_duckduckgo(self, query: str, max_results: int = 12) -> List[WebSearchResult]:
        """使用 DuckDuckGo 搜索"""
        ddgs = self._get_ddg_search()
        if not ddgs:
            logger.warning("DuckDuckGo 不可用")
            return []

        try:
            response = ddgs.text(query, max_results=max_results)

            results = []
            for item in response:
                results.append(WebSearchResult(
                    title=item.get("title", ""),
                    url=item.get("href", ""),
                    content=item.get("body", ""),
                    score=0.0
                ))

            logger.info(f"DuckDuckGo 搜索成功: {len(results)} 条结果")
            return results

        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {e}")
            return []

    def search(self, query: str, max_results: int = 12, use_tavily: bool = True) -> List[WebSearchResult]:
        """
        联网搜索（支持降级）

        Args:
            query: 搜索查询
            max_results: 最大结果数
            use_tavily: 是否优先使用 Tavily

        Returns:
            搜索结果列表（已去重）
        """
        # 优先使用 Tavily
        if use_tavily:
            results = self.search_tavily(query, max_results)
            if results:
                results = self._deduplicate(results)
                return results
            logger.info("Tavily 失败，降级到 DuckDuckGo")

        # 降级到 DuckDuckGo
        results = self.search_duckduckgo(query, max_results)
        if results:
            results = self._deduplicate(results)
            return results

        logger.warning("所有搜索引擎都不可用")
        return []

    @staticmethod
    def _deduplicate(results: List[WebSearchResult]) -> List[WebSearchResult]:
        """按 URL 去重，保留首次出现的"""
        seen = set()
        unique = []
        for r in results:
            if r.url not in seen:
                seen.add(r.url)
                unique.append(r)
        return unique


# 全局搜索引擎实例
_web_searcher: Optional[WebSearcher] = None


def get_web_searcher() -> WebSearcher:
    """获取全局搜索引擎实例"""
    global _web_searcher
    if _web_searcher is None:
        from app.config import settings
        _web_searcher = WebSearcher(api_key=settings.tavily_api_key)
    return _web_searcher


def web_search(query: str, max_results: int = 12) -> List[WebSearchResult]:
    """
    联网搜索便捷函数

    Args:
        query: 搜索查询
        max_results: 最大结果数

    Returns:
        搜索结果列表
    """
    searcher = get_web_searcher()
    return searcher.search(query, max_results)
