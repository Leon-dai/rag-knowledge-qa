"""文档加载器：支持多种文件格式"""
import os
from pathlib import Path
from langchain_core.documents import Document as LCDocument


def load_document(file_path: str, original_filename: str) -> list[LCDocument]:
    """根据文件类型选择加载器并加载文档

    Args:
        file_path: 文件在磁盘上的路径
        original_filename: 原始文件名（用于判断类型）

    Returns:
        LangChain Document 列表
    """
    ext = Path(original_filename).suffix.lower()
    file_path_str = str(file_path)

    if ext == ".pdf":
        return _load_pdf(file_path_str)
    elif ext in (".docx", ".doc"):
        return _load_docx(file_path_str)
    elif ext in (".txt", ".md", ".markdown"):
        return _load_text(file_path_str)
    elif ext == ".csv":
        return _load_csv(file_path_str)
    elif ext in (".xlsx", ".xls"):
        return _load_excel(file_path_str)
    else:
        raise ValueError(f"不支持的文件类型: {ext}")


def _load_pdf(file_path: str) -> list[LCDocument]:
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(file_path)
    return loader.load()


def _load_docx(file_path: str) -> list[LCDocument]:
    from langchain_community.document_loaders import Docx2txtLoader
    loader = Docx2txtLoader(file_path)
    return loader.load()


def _load_text(file_path: str) -> list[LCDocument]:
    from langchain_community.document_loaders import TextLoader
    loader = TextLoader(file_path, encoding="utf-8")
    return loader.load()


def _load_csv(file_path: str) -> list[LCDocument]:
    from langchain_community.document_loaders import CSVLoader
    loader = CSVLoader(file_path, encoding="utf-8")
    return loader.load()


def _load_excel(file_path: str) -> list[LCDocument]:
    """Excel 加载：使用 pandas 逐行读取"""
    import pandas as pd
    docs = []
    xls = pd.ExcelFile(file_path)
    for sheet_name in xls.sheet_names:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        text = df.to_markdown(index=False) if not df.empty else ""
        if text.strip():
            docs.append(LCDocument(
                page_content=text,
                metadata={"source": file_path, "sheet": sheet_name}
            ))
    return docs
