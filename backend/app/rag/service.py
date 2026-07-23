"""RAG 问答服务：混合检索 → Reranker精排 → 流式生成"""
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
    RAG_SYSTEM_PROMPT_DEEP,
    CHAT_SYSTEM_PROMPT,
    CHAT_SYSTEM_PROMPT_DEEP,
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
        """带错误处理的流式 LLM 调用

        解析 LangChain chunk，当存在 reasoning_content 时拆分为 thinking 事件。
        返回字典：{"type": "thinking"/"token", "content": "..."}
        """
        try:
            generator = llm.astream(prompt)
            async for chunk in generator:
                reasoning = None
                content = None

                if hasattr(chunk, "additional_kwargs") and chunk.additional_kwargs:
                    reasoning = chunk.additional_kwargs.get("reasoning_content")

                if hasattr(chunk, "content"):
                    content = chunk.content

                if reasoning:
                    yield {"type": "thinking", "content": reasoning}
                if content:
                    yield {"type": "token", "content": content}
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            yield await emit_status(f"生成回答时出错，请重试: {str(e)}")

    @staticmethod
    async def _astream_dashscope_deep_think(
        messages: list[dict],
    ) -> AsyncGenerator:
        """使用 httpx 直接调 DashScope REST API，真正的逐 token 流式

        绕过 DashScope SDK 的同步生成器，用 httpx 异步读取 SSE 流，
        确保每个 token 实时推送到前端。
        """
        import httpx
        import json as json_mod

        try:
            url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.dashscope_api_key}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            }
            body = {
                "model": "qwen3.7-plus",
                "messages": messages,
                "stream": True,
                "stream_options": {"include_usage": True},
                "enable_thinking": True,
            }

            logger.info(f"深度思考请求开始 model=qwen3.7-plus")

            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, json=body, headers=headers) as resp:
                    logger.info(f"DashScope 响应 status={resp.status_code}")
                    if resp.status_code != 200:
                        body_text = await resp.aread()
                        logger.error(f"DashScope 错误: {body_text[:500]}")
                        yield await emit_status(f"调用失败: HTTP {resp.status_code}")
                        return

                    thinking_chunks = 0
                    token_chunks = 0
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        if not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            logger.info(f"深度思考完成: thinking={thinking_chunks} token={token_chunks}")
                            break
                        try:
                            data = json_mod.loads(data_str)
                            choices = data.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                reasoning = delta.get("reasoning_content", "") or ""
                                content = delta.get("content", "") or ""

                                if reasoning:
                                    thinking_chunks += 1
                                    yield {"type": "thinking", "content": reasoning}
                                if content:
                                    token_chunks += 1
                                    yield {"type": "token", "content": content}
                            else:
                                # usage chunk
                                pass
                        except json_mod.JSONDecodeError:
                            if raw_line_count <= 3:
                                logger.info(f"DashScope non-JSON: {data_str[:200]}")
        except Exception as e:
            logger.error(f"深度思考流式调用失败: {e}")
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
    def _extract_search_keyword(question: str, rewritten_queries: list[str]) -> str:
        """为联网搜索提取关键词。规则清理口语词，不依赖 LLM。"""
        import re

        # 如果改写结果可用（短且无对话语气），直接用
        if rewritten_queries:
            candidate = rewritten_queries[0]
            chatter_markers = ["好的", "我将帮助", "以下是", "首先", "步骤", "请稍等", "现在我开始"]
            if not any(m in candidate for m in chatter_markers) and len(candidate) < 100:
                return candidate

        # 规则清理：去掉常见口语前后缀
        cleaned = question
        # 去掉前缀：我(需要/想/要)你查/搜/找 + 帮我/麻烦/请 + 查/搜/找 + 一下/个
        cleaned = re.sub(r'^(我(需要|想要|要|想)你?|你(能|可以)|(请|麻烦|帮忙|帮我)你?)\s*(帮我?)?\s*(查|搜|找|搜索|查询|看看|看一下)\s*(一下|一个|个)?\s*', '', cleaned)
        # 去掉后缀：大哥/兄弟/大佬/吗/好吗/行吗/可以吗/能做到吗/谢谢
        cleaned = re.sub(r'[，,!\s]*(大哥|兄弟|大佬|好吗|行吗|可以吗|能做到吗|能查到吗|谢谢|多谢|拜托|哈|哦|啊)[!！?？。]*$', '', cleaned)
        cleaned = cleaned.strip('，,!！?？。 \t\n\r')

        return cleaned if cleaned else question

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
        search_mode: str = "local",  # "local" (不联网), "web" (联网)
        deep_think: bool = False,
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
        history_text = RAGService._build_chat_history(chat_history or [])

        # 0. 意图检测
        yield await emit_status("正在分析问题...")
        from app.rag.intent_detector import detect_intent
        intent = detect_intent(question)
        logger.info(f"意图检测: question='{question[:60]}...' → {intent}")

        # 0.1 闲聊：跳过搜索，直接 LLM
        if intent == "chitchat":
            yield await emit_status("AI 自由回答...")
            citations = []
            system_prompt = CHAT_SYSTEM_PROMPT_DEEP if deep_think else CHAT_SYSTEM_PROMPT
            prompt_text = CHAT_PROMPT_TEMPLATE.format(
                system_prompt=system_prompt,
                chat_history=history_text,
                question=question,
            )

            if deep_think:
                messages = [{"role": "system", "content": system_prompt}]
                if history_text and history_text != "（无历史对话）":
                    user_content = f"对话历史：\n{history_text}\n\n用户的问题是：{question}"
                else:
                    user_content = f"用户的问题是：{question}"
                messages.append({"role": "user", "content": user_content})
                generator = RAGService._astream_dashscope_deep_think(messages)
            else:
                llm = RAGService._get_llm(streaming=True)
                generator = RAGService._astream_llm_with_retry(llm, prompt_text)

            async for sse_event in stream_response(generator, citations):
                yield sse_event
            return

        # 1. 查询路由：根据问题类型选择检索策略
        from app.rag.query_router import get_search_strategy
        strategy = get_search_strategy(question)
        vector_weight = strategy["vector_weight"]
        bm25_weight = strategy["bm25_weight"]

        # 2. 根据 search_mode 执行搜索
        local_candidates = []
        web_results = []

        # 本地搜索
        if search_mode in ["local", "web"]:
            yield await emit_status(f"正在检索本地知识库... (策略: {strategy['description']})")

            # 智能查询改写：只在需要搜本地 KB 时才调用
            from app.rag.query_rewriter import smart_rewrite_query
            rewritten_queries = smart_rewrite_query(question, chat_history)

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
        if search_mode == "web":
            yield await emit_status("正在搜索互联网...")
            from app.web import web_search
            # 直接提取检索关键词（不用 smart_rewrite_query，它太慢且输出不可靠）
            web_query = RAGService._extract_search_keyword(question, [])
            logger.info(f"联网搜索关键词: {web_query}")
            web_results = web_search(web_query, max_results=5)
            if web_results:
                logger.info(f"联网搜索成功: {len(web_results)} 条结果")
            else:
                logger.warning("联网搜索无结果或失败")

        # 4. LLM-as-Judge：判断哪些本地文档真正与问题相关
        if local_candidates:
            yield await emit_status(f"本地检索到 {len(local_candidates)} 篇候选，AI 正在判断相关性...")
            relevant = RAGService._judge_relevance(question, local_candidates)
        else:
            relevant = []

        # 5. 根据结果选择模式
        # 关键：只有 LLM Judge 判定相关的文档才触发 RAG 模式，
        # 否则降级为 Chat 模式，不强制加引用
        if relevant or web_results:
            # === RAG 模式：有相关文档 ===
            reranked = rerank(question, [doc for doc, _ in relevant], top_k=3) if relevant else []

            # 扩展子块为父块（Small-to-Big）
            expanded_docs = RAGService._expand_to_parent_docs([doc for doc, _ in reranked]) if reranked else []

            # 构建状态信息
            status_parts = []
            if expanded_docs:
                status_parts.append(f"找到 {len(expanded_docs)} 篇本地文档")
            if web_results:
                status_parts.append(f"{len(web_results)} 条网络资料")

            yield await emit_status(f"{', '.join(status_parts)}，正在生成回答...")

            # 构建引用
            citations = format_citations(reranked) if reranked else []
            for i, web_result in enumerate(web_results[:5], 1):
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

            system_prompt = RAG_SYSTEM_PROMPT_DEEP if deep_think else RAG_SYSTEM_PROMPT
            prompt_text = RAG_PROMPT_TEMPLATE.format(
                system_prompt=system_prompt,
                context=context,
                chat_history=history_text,
                question=question,
            )
        else:
            # === Chat 模式：无相关文档，LLM 自由回答，不引用 ===
            yield await emit_status("未找到相关内容，AI 自由回答...")
            citations = []
            system_prompt = CHAT_SYSTEM_PROMPT_DEEP if deep_think else CHAT_SYSTEM_PROMPT
            prompt_text = CHAT_PROMPT_TEMPLATE.format(
                system_prompt=system_prompt,
                chat_history=history_text,
                question=question,
            )

        # 6. 流式生成
        if deep_think:
            messages = [{"role": "system", "content": system_prompt}]

            if citations:
                # RAG 模式：资料 + 指令融合为一段
                user_content = (
                    f"以下是与用户问题相关的资料：\n\n{context}\n\n"
                    f"用户的问题是：{question}\n\n"
                    f"只使用以上资料中的信息回答。有相关信息就引用；没有就说暂无相关资料。"
                )
            else:
                # Chat 模式
                if history_text and history_text != "（无历史对话）":
                    user_content = f"对话历史：\n{history_text}\n\n用户的问题是：{question}"
                else:
                    user_content = f"用户的问题是：{question}"

            messages.append({"role": "user", "content": user_content})
            generator = RAGService._astream_dashscope_deep_think(messages)
        else:
            llm = RAGService._get_llm(streaming=True)
            generator = RAGService._astream_llm_with_retry(llm, prompt_text)

        async for sse_event in stream_response(generator, citations):
            yield sse_event

    @staticmethod
    async def query_sync(question: str) -> dict:
        """非流式 RAG 问答（用于标题生成等场景）"""
        candidates = hybrid_search(question, top_k=4)
        relevant = RAGService._judge_relevance(question, candidates) if candidates else []

        llm = RAGService._get_llm(streaming=False)

        if relevant:
            citations = format_citations(relevant)
            context = RAGService._build_context(relevant)
            prompt = RAG_PROMPT_TEMPLATE.format(
                system_prompt=RAG_SYSTEM_PROMPT,
                context=context,
                chat_history="",
                question=question,
            )
        else:
            citations = []
            prompt = CHAT_PROMPT_TEMPLATE.format(
                system_prompt=CHAT_SYSTEM_PROMPT,
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
