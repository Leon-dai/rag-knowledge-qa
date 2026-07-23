"""SSE 流式响应处理"""
import json
import asyncio
from typing import AsyncGenerator


async def emit_status(text: str) -> str:
    """发送状态更新事件"""
    return f"data: {json.dumps({'status': text}, ensure_ascii=False)}\n\n"


async def stream_response(
    llm_generator,
    citations: list[dict],
) -> AsyncGenerator[str, None]:
    """将 LLM 流式输出转为 SSE 格式

    支持两种 chunk 格式：
    - 字符串/标准 LangChain chunk：直接作为 token 输出
    - 字典 {"type": "thinking"/"token", "content": "..."}：分别输出 thinking 和 token 事件

    Yields:
        SSE 格式字符串
    """
    token_index = 0

    async for chunk in llm_generator:
        # 字典格式：来自 _astream_llm_with_retry 的结构化输出
        if isinstance(chunk, dict):
            event_type = chunk.get("type", "token")
            content = chunk.get("content", "")
            if content:
                if event_type == "thinking":
                    yield f"data: {json.dumps({'thinking': content}, ensure_ascii=False)}\n\n"
                else:
                    yield f"data: {json.dumps({'token': content, 'index': token_index}, ensure_ascii=False)}\n\n"
                    token_index += 1
            continue

        # 原始 LangChain chunk / 字符串
        content = ""
        if hasattr(chunk, "content"):
            content = chunk.content
        elif isinstance(chunk, str):
            content = chunk
        else:
            content = str(chunk)

        if content:
            yield f"data: {json.dumps({'token': content, 'index': token_index}, ensure_ascii=False)}\n\n"
            token_index += 1

    # 发送引用来源
    if citations:
        yield f"data: {json.dumps({'sources': citations}, ensure_ascii=False)}\n\n"

    # 发送完成信号
    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"


def format_citations(search_results) -> list[dict]:
    """格式化检索结果为引用列表，按文档去重合并

    Args:
        search_results: [(Document, score), ...] 检索结果

    Returns:
        引用列表，格式 [{"source": "doc.pdf", "pages": [1, 3]}]
    """
    # 按文档名分组
    groups: dict[str, dict] = {}

    for doc, score in search_results:
        source = doc.metadata.get("doc_title", doc.metadata.get("source", "未知来源"))
        doc_id = doc.metadata.get("document_id", "")
        page = doc.metadata.get("page", None)
        chunk_index = doc.metadata.get("chunk_index", 0)

        if source not in groups:
            groups[source] = {"source": source, "doc_id": doc_id, "pages": set(), "seen_chunks": set()}

        g = groups[source]
        chunk_key = f"{page}:{chunk_index}"
        if chunk_key not in g["seen_chunks"]:
            g["seen_chunks"].add(chunk_key)
            if page is not None and page > 0:  # 过滤掉 page=0（未知页码）
                g["pages"].add(page)

    # 转换为列表，每个文档一条
    citations = []
    for source, g in groups.items():
        pages = sorted(g["pages"])
        citations.append({
            "source": source,
            "doc_id": g["doc_id"],
            "pages": pages if pages else None,  # 无有效页码时返回 null
        })

    return citations[:5]
