"""父子文档分块策略

参考 All-in-RAG C8 — Small-to-Big Retrieal (Parent Document Retriever)

策略：
- 子块（Child Chunk）：200-300 字符，用于精确向量检索
- 父块（Parent Chunk）：1000-1500 字符，检索命中子块后，将父块喂给 LLM 生成回答

好处：
- 小块检索：向量匹配更精确，不会截断上下文
- 大块生成：LLM 看到完整上下文，回答质量更高
"""
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


# 中文优化分隔符
CHINESE_SEPARATORS = [
    "\n\n",
    "\n",
    "。",
    "！",
    "？",
    "；",
    "，",
    "、",
    " ",
    "",
]


def get_parent_splitter(
    chunk_size: int = 1200,
    chunk_overlap: int = 100,
) -> RecursiveCharacterTextSplitter:
    """获取父块分块器（大块，用于生成）

    Args:
        chunk_size: 父块最大字符数（默认1200）
        chunk_overlap: 重叠字符数

    Returns:
        RecursiveCharacterTextSplitter 实例
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=CHINESE_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def get_child_splitter(
    chunk_size: int = 250,
    chunk_overlap: int = 30,
) -> RecursiveCharacterTextSplitter:
    """获取子块分块器（小块，用于检索）

    Args:
        chunk_size: 子块最大字符数（默认250）
        chunk_overlap: 重叠字符数

    Returns:
        RecursiveCharacterTextSplitter 实例
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=CHINESE_SEPARATORS,
        length_function=len,
        is_separator_regex=False,
    )


def split_documents_with_parents(
    documents: list[Document],
    doc_id: str,
    doc_title: str,
    parent_chunk_size: int = 1200,
    child_chunk_size: int = 250,
) -> tuple[list[Document], dict[str, Document]]:
    """分块文档，同时创建父子关系

    参考: All-in-RAG C8 — Small-to-Big Retrieval

    Args:
        documents: LangChain Document 列表
        doc_id: 数据库中的文档 ID
        doc_title: 文档标题（原始文件名）
        parent_chunk_size: 父块大小
        child_chunk_size: 子块大小

    Returns:
        (child_chunks, parent_map)
        - child_chunks: 子块列表（用于向量存储和检索）
        - parent_map: 父块映射表 {parent_id: Document}
    """
    # 1. 先切父块
    parent_splitter = get_parent_splitter(chunk_size=parent_chunk_size)
    parent_docs = parent_splitter.split_documents(documents)

    # 2. 为每个父块创建子块
    child_chunks = []
    parent_map = {}
    child_index = 0

    for parent_idx, parent_doc in enumerate(parent_docs):
        # 生成父块 ID
        parent_id = f"{doc_id}:parent:{parent_idx}"

        # 将父块存入映射表
        parent_map[parent_id] = Document(
            page_content=parent_doc.page_content,
            metadata={
                **parent_doc.metadata,
                "document_id": doc_id,
                "doc_title": doc_title,
                "parent_id": parent_id,
                "is_parent": True,
            }
        )

        # 切子块
        child_splitter = get_child_splitter(chunk_size=child_chunk_size)
        child_docs = child_splitter.split_documents([parent_doc])

        for child_doc in child_docs:
            # 子块 metadata 记录父块 ID
            child_doc.metadata.update({
                "document_id": doc_id,
                "doc_title": doc_title,
                "parent_id": parent_id,
                "chunk_index": child_index,
                "page": child_doc.metadata.get("page", 0),
                "is_parent": False,
            })
            child_chunks.append(child_doc)
            child_index += 1

    return child_chunks, parent_map


def get_parent_chunk(
    child_chunk: Document,
    parent_map: dict[str, Document],
) -> Document | None:
    """根据子块获取对应的父块

    Args:
        child_chunk: 子块文档
        parent_map: 父块映射表

    Returns:
        父块文档，如果不存在则返回 None
    """
    parent_id = child_chunk.metadata.get("parent_id")
    if not parent_id:
        return None
    return parent_map.get(parent_id)
