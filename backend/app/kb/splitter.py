"""文本分块策略"""
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


def get_text_splitter(
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> RecursiveCharacterTextSplitter:
    """获取中文优化的文本分块器

    Args:
        chunk_size: 每块最大字符数
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


def split_documents(
    documents: list[Document],
    doc_id: str,
    doc_title: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[Document]:
    """分块文档并添加元数据

    Args:
        documents: LangChain Document 列表
        doc_id: 数据库中的文档 ID
        doc_title: 文档标题（原始文件名）
        chunk_size: 每块最大字符数
        chunk_overlap: 重叠字符数

    Returns:
        带元数据的分块文档列表
    """
    splitter = get_text_splitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = splitter.split_documents(documents)

    for i, chunk in enumerate(chunks):
        # 合并原始元数据并添加自定义字段
        chunk.metadata.update({
            "document_id": doc_id,
            "doc_title": doc_title,
            "chunk_index": i,
            "page": chunk.metadata.get("page", 0),
        })

    return chunks
