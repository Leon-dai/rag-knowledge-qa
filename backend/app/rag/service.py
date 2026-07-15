"""RAG 问答服务：混合检索 → Reranker精排 → 流式生成"""
from datetime import date
from typing import AsyncGenerator

from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings
from app.model_settings import get_current_llm_model
from app.rag.retriever import hybrid_search
from app.rag.reranker import rerank
from app.rag.prompts import (
    RAG_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT,
    RAG_PROMPT_TEMPLATE,
    CHAT_PROMPT_TEMPLATE,
)
from app.rag.streaming import stream_response, format_citations, emit_status
from app.logging import logger


class RAGService:
    """RAG 问答服务"""

    # ==================== LLM-as-Judge 相关性判断 ====================

    @staticmethod
    def _judge_relevance(question: str, candidates: list) -> list:
        """LLM-as-Judge：让轻量模型判断哪些候选文档与问题真正相关。

        这是 2024-2025 学术界 Adaptive-RAG / RJAG 的标准做法：
        用 LLM 做裁判，而不是调向量阈值。

        Args:
            question: 用户问题
            candidates: [(Document, score), ...]

        Returns:
            被判定为相关的文档列表
        """
        if not candidates:
            return []

        # 构建判断提示词：让 LLM 从候选文档中选出相关的
        doc_list = []
        for i, (doc, _score) in enumerate(candidates[:8], 1):
            snippet = doc.page_content[:150].replace("\n", " ")
            doc_list.append(f"[{i}] {snippet}")

        judge_prompt = f"""你是一个检索质量评估员。判断以下文档片段是否与用户问题相关。

用户问题：{question}

候选文档：
{chr(10).join(doc_list)}

请回复："相关：[编号]" 列出所有相关的文档编号（如 "相关：1,3,5"），如果都不相关回复 "相关：无"。
只回复上述格式，不要解释。"""

        try:
            judge_llm = RAGService._get_llm(model="qwen-turbo", streaming=False)
            response = judge_llm.invoke(judge_prompt)
            result = response.content.strip()

            # 解析结果
            if "相关：无" in result or "相关: 无" in result:
                return []

            # 提取编号
            import re
            nums = re.findall(r'\d+', result)
            indices = [int(n) - 1 for n in nums if 1 <= int(n) <= len(candidates)]

            return [candidates[i] for i in indices if i < len(candidates)]
        except Exception:
            # Judge 不可用时，回退到前3个向量结果
            return candidates[:3]

    # ==================== LLM 实例 ====================

    @staticmethod
    def _get_llm(model: str | None = None, streaming: bool = True, enable_thinking: bool = False):
        kwargs = {
            "model": model or get_current_llm_model(),
            "api_key": settings.dashscope_api_key,
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "streaming": streaming,
            "temperature": 0.3,
        }
        if enable_thinking:
            kwargs["model_kwargs"] = {"extra_body": {"enable_thinking": True}}
        return ChatOpenAI(**kwargs)

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )
    async def _invoke_llm_with_retry(llm, prompt: str):
        """带重试的 LLM 调用"""
        return await llm.ainvoke(prompt)

    @staticmethod
    async def _astream_llm_with_retry(llm, prompt: str) -> AsyncGenerator:
        """带错误处理的流式 LLM 调用"""
        try:
            generator = llm.astream(prompt)
            async for chunk in generator:
                yield chunk
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            # 发送错误事件给前端
            yield await emit_status(f"生成回答时出错，请重试: {str(e)}")

    @staticmethod
    def _build_context(search_results, include_web_results: list = None) -> str:
        """构建上下文，支持本地文档和联网结果"""
        parts = []

        # 本地文档
        if search_results:
            for i, (doc, _score) in enumerate(search_results, 1):
                source = doc.metadata.get("doc_title", "未知来源")
                page = doc.metadata.get("page", "")
                page_info = f" (第{page}页)" if page else ""
                parts.append(f"[本地资料{i} | 来源: {source}{page_info}]\n{doc.page_content}")

        # 联网结果
        if include_web_results:
            for i, web_result in enumerate(include_web_results, 1):
                parts.append(f"[网络资料{i} | 来源: {web_result.title} ({web_result.url})]\n{web_result.content}")

        if not parts:
            return "暂无相关资料"

        return "\n\n---\n\n".join(parts)

    @staticmethod
    def _build_chat_history(history: list[dict]) -> str:
        if not history:
            return "（无历史对话）"
        messages = []
        for msg in history[-6:]:
            role = "用户" if msg["role"] == "user" else "助手"
            messages.append(f"{role}: {msg['content'][:200]}")
        return "\n".join(messages)

    @staticmethod
    def _expand_to_parent_docs(child_docs: list) -> list:
        """将子块扩展为父块（Small-to-Big Retrieval）

        参考: All-in-RAG C8 — Parent Document Retriever

        策略：
        - 检索命中的是子块（小块，用于精确匹配）
        - 生成回答时扩展为父块（大块，上下文更完整）

        Args:
            child_docs: 子块文档列表

        Returns:
            父块文档列表（去重后）
        """
        from app.rag.retriever import get_vector_store

        vector_store = get_vector_store()
        parent_docs = []
        seen_parent_ids = set()

        for child_doc in child_docs:
            parent_id = child_doc.metadata.get("parent_id")

            # 如果没有 parent_id，说明是旧数据，直接用子块
            if not parent_id:
                parent_docs.append(child_doc)
                continue

            # 如果已经添加过这个父块，跳过
            if parent_id in seen_parent_ids:
                continue

            # 从向量库查找父块
            try:
                parent_results = vector_store.get(
                    where={"parent_id": parent_id, "is_parent": True},
                    include=["documents", "metadatas"],
                )

                if parent_results and parent_results["ids"]:
                    # 取第一个父块
                    parent_doc = Document(
                        page_content=parent_results["documents"][0],
                        metadata=parent_results["metadatas"][0],
                    )
                    parent_docs.append(parent_doc)
                    seen_parent_ids.add(parent_id)
                else:
                    # 找不到父块，用子块兜底
                    parent_docs.append(child_doc)
            except Exception as e:
                from app.logging import logger
                logger.warning(f"扩展父块失败: {e}")
                parent_docs.append(child_doc)

        return parent_docs

    @staticmethod
    async def query(
        question: str,
        chat_history: list[dict] | None = None,
        search_mode: str = "local",  # "local", "web", "mixed"
    ) -> AsyncGenerator[str, None]:
        """RAG 问答主流程：支持本地/联网/混合搜索

        检索链路:
        1. 根据 search_mode 决定搜索范围
        2. 本地搜索：混合检索（向量 + BM25 → RRF融合）
        3. 联网搜索：Tavily/DuckDuckGo
        4. Reranker Cross-Encoder 精排 → 保留 top-3
        5. Reranker 分数判断 → RAG模式 or Chat模式
        6. LLM 流式生成 → SSE 推送

        Yields:
            SSE 格式字符串
        """
        today = date.today().strftime("%Y年%m月%d日")
        history_text = RAGService._build_chat_history(chat_history or [])

        # 0. 查询路由：根据问题类型选择检索策略
        # 参考: All-in-RAG Chapter 4 — 查询分发与路由
        yield await emit_status("正在分析查询类型...")
        from app.rag.query_router import get_search_strategy
        strategy = get_search_strategy(question)
        vector_weight = strategy["vector_weight"]
        bm25_weight = strategy["bm25_weight"]

        # 1. 智能查询改写：分解复合问题 + 改写为检索关键词
        yield await emit_status("正在理解问题...")
        from app.rag.query_rewriter import smart_rewrite_query
        rewritten_queries = smart_rewrite_query(question, chat_history)

        # 2. 根据 search_mode 执行搜索
        local_candidates = []
        web_results = []

        # 本地搜索
        if search_mode in ["local", "mixed"]:
            yield await emit_status(f"正在检索本地知识库... (策略: {strategy['description']})")

            # 用分解后的多个子问题分别检索，合并去重
            all_candidates = {}  # doc_key -> (doc, score)
            for q in rewritten_queries[:5]:  # 最多5个子问题
                results = hybrid_search(
                    q,
                    top_k=6,
                    vector_weight=vector_weight,
                    bm25_weight=bm25_weight,
                )
                for doc, score in results:
                    doc_key = f"{doc.metadata.get('doc_title', '')}:{doc.metadata.get('chunk_index', 0)}"
                    if doc_key not in all_candidates:
                        all_candidates[doc_key] = (doc, score)

            local_candidates = list(all_candidates.values())[:8]  # 最多8条

        # 联网搜索
        if search_mode in ["web", "mixed"]:
            yield await emit_status("正在搜索互联网...")
            from app.web import web_search
            # 用原始问题搜索互联网
            web_results = web_search(question, max_results=12)
            if web_results:
                logger.info(f"联网搜索成功: {len(web_results)} 条结果")
            else:
                logger.warning("联网搜索无结果或失败")

        # 3. 合并结果
        all_docs = local_candidates
        if not all_docs and not web_results:
            yield await emit_status("未找到相关内容，切换为通用对话...")

        # 4. LLM-as-Judge：判断哪些本地文档真正与问题相关
        if local_candidates:
            yield await emit_status(f"本地检索到 {len(local_candidates)} 篇候选，AI 正在判断相关性...")
            relevant = RAGService._judge_relevance(question, local_candidates)
        else:
            relevant = []

        # 5. 根据结果选择模式
        if relevant or web_results:
            # === RAG 模式：有相关文档 ===
            reranked = rerank(question, [doc for doc, _ in relevant], top_k=3) if relevant else []

            # 扩展子块为父块（Small-to-Big）
            # 参考: All-in-RAG C8 — Parent Document Retriever
            expanded_docs = RAGService._expand_to_parent_docs([doc for doc, _ in reranked]) if reranked else []

            # 构建状态信息
            status_parts = []
            if expanded_docs:
                status_parts.append(f"找到 {len(expanded_docs)} 篇本地文档")
            if web_results:
                status_parts.append(f"{len(web_results)} 条网络资料")

            yield await emit_status(f"{', '.join(status_parts)}，正在生成回答...")

            # 构建引用（区分本地和网络）
            citations = format_citations(reranked) if reranked else []
            # 添加网络引用
            for i, web_result in enumerate(web_results, 1):
                citations.append({
                    "source": f"🌐 {web_result.title}",
                    "doc_id": f"web_{i}",
                    "pages": None,
                    "url": web_result.url,
                })

            # 构建上下文
            context = RAGService._build_context(
                [(doc, 0) for doc in expanded_docs],
                include_web_results=web_results
            )

            system_prompt = RAG_SYSTEM_PROMPT.format(current_date=today)
            prompt_text = RAG_PROMPT_TEMPLATE.format(
                system_prompt=system_prompt,
                context=context,
                chat_history=history_text,
                question=question,
            )
        else:
            # === Chat 模式：无相关文档 ===
            yield await emit_status("未找到相关内容，AI 自由回答...")
            citations = []
            system_prompt = CHAT_SYSTEM_PROMPT.format(current_date=today)
            prompt_text = CHAT_PROMPT_TEMPLATE.format(
                system_prompt=system_prompt,
                chat_history=history_text,
                question=question,
            )

        # 6. 流式生成（带错误处理）
        llm = RAGService._get_llm(streaming=True)
        generator = RAGService._astream_llm_with_retry(llm, prompt_text)

        async for sse_event in stream_response(generator, citations):
            yield sse_event

    @staticmethod
    async def query_sync(question: str) -> dict:
        """非流式 RAG 问答（用于标题生成等场景）"""
        candidates = hybrid_search(question, top_k=4)
        relevant = RAGService._judge_relevance(question, candidates) if candidates else []

        today = date.today().strftime("%Y年%m月%d日")
        llm = RAGService._get_llm(streaming=False)

        if relevant:
            citations = format_citations(relevant)
            context = RAGService._build_context(relevant)
            prompt = RAG_PROMPT_TEMPLATE.format(
                system_prompt=RAG_SYSTEM_PROMPT.format(current_date=today),
                context=context,
                chat_history="",
                question=question,
            )
        else:
            citations = []
            prompt = CHAT_PROMPT_TEMPLATE.format(
                system_prompt=CHAT_SYSTEM_PROMPT.format(current_date=today),
                chat_history="",
                question=question,
            )

        # 带重试的 LLM 调用
        try:
            response = await RAGService._invoke_llm_with_retry(llm, prompt)
            return {"answer": response.content, "citations": citations}
        except Exception as e:
            logger.error(f"非流式问答失败: {e}")
            return {"answer": "生成回答时出错，请重试", "citations": []}
