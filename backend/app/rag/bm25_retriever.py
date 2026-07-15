"""BM25 关键词检索器（纯 Python 实现，无外部依赖）

使用字符级 bigram 处理中文，避免 jieba 分词器的依赖问题。
BM25 用于精确关键词匹配（人名、型号、SKU 等），
弥补向量语义搜索对专有名词不敏感的缺陷。

BM25 公式:
  Score(D,Q) = Σ IDF(qi) * (f(qi,D) * (k1+1)) / (f(qi,D) + k1*(1-b+b*|D|/avgdl))

参考: Okapi BM25 (Robertson et al., 1995)
"""
import math
from typing import List
from langchain_core.documents import Document
from app.rag.retriever import get_vector_store
from app.logging import logger


class SimpleBM25:
    """轻量 BM25 实现（字符 bigram 分词）"""

    def __init__(self, documents: List[str], k1: float = 1.5, b: float = 0.75):
        """
        Args:
            documents: 文档文本列表
            k1: 词频饱和参数 (1.2-2.0)
            b: 文档长度归一化参数 (0.5-0.75)
        """
        self.k1 = k1
        self.b = b
        self.documents = documents
        self.n = len(documents)

        # 计算平均文档长度
        self.doc_lens = [len(self._tokenize(d)) for d in documents]
        self.avgdl = sum(self.doc_lens) / max(self.n, 1)

        # 计算 IDF
        self.idf = {}
        self._compute_idf()

    def _tokenize(self, text: str) -> List[str]:
        """字符级 bigram 分词（无需 jieba）

        中文用 bigram： "代向辉" → ["代向", "向辉"]
        英文用空格分词后再 bigram
        """
        tokens = []
        # 简单的中文识别：CJK 统一汉字范围
        i = 0
        while i < len(text):
            ch = text[i]
            if '一' <= ch <= '鿿':
                # 中文字符：取 bigram
                if i + 1 < len(text):
                    next_ch = text[i + 1]
                    if '一' <= next_ch <= '鿿':
                        tokens.append(ch + next_ch)
                    else:
                        tokens.append(ch)
                else:
                    tokens.append(ch)
                i += 1
            elif ch.isalnum():
                # 英文/数字单词
                start = i
                while i < len(text) and text[i].isalnum():
                    i += 1
                word = text[start:i].lower()
                tokens.append(word)
                # 单词内 bigram
                for j in range(len(word) - 1):
                    tokens.append(word[j:j + 2])
            else:
                i += 1
        return [t for t in tokens if len(t.strip()) >= 1]

    def _compute_idf(self):
        """计算每个 token 的 IDF 值"""
        doc_freq = {}
        for doc in self.documents:
            tokens = set(self._tokenize(doc))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        for token, df in doc_freq.items():
            # IDF = log((N - df + 0.5) / (df + 0.5) + 1)
            self.idf[token] = math.log((self.n - df + 0.5) / (df + 0.5) + 1)

    def search(self, query: str, k: int = 8) -> List[tuple]:
        """搜索并返回 [(doc_index, score), ...]，按分数降序

        Args:
            query: 查询文本
            k: 返回数量

        Returns:
            [(doc_index, bm25_score), ...]
        """
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        scores = []
        for idx, doc in enumerate(self.documents):
            doc_tokens = self._tokenize(doc)
            doc_len = len(doc_tokens)
            if doc_len == 0:
                continue

            # 计算词频
            tf = {}
            for t in doc_tokens:
                tf[t] = tf.get(t, 0) + 1

            score = 0.0
            for qt in query_tokens:
                if qt not in self.idf:
                    continue
                f = tf.get(qt, 0)
                if f == 0:
                    continue

                # BM25 核心公式
                numerator = self.idf[qt] * f * (self.k1 + 1)
                denominator = f + self.k1 * (1 - self.b + self.b * doc_len / self.avgdl)
                score += numerator / denominator

            if score > 0:
                scores.append((idx, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:k]


# 全局 BM25 索引
_bm25: SimpleBM25 | None = None
_docs_meta: list = []  # 文档元数据


def build_bm25_index():
    """从 ChromaDB 加载所有文档，构建 BM25 索引"""
    global _bm25, _docs_meta

    try:
        vs = get_vector_store()
        all_data = vs.get(include=["documents", "metadatas"])
    except Exception:
        _bm25 = None
        _docs_meta = []
        return

    if not all_data["ids"]:
        _bm25 = None
        _docs_meta = []
        return

    texts = []
    metas = []
    for i in range(len(all_data["ids"])):
        texts.append(all_data["documents"][i])
        metas.append(all_data["metadatas"][i])

    _bm25 = SimpleBM25(texts)
    _docs_meta = metas
    logger.info(f"BM25 索引已构建: {len(texts)} chunks")


def bm25_search(query: str, k: int = 8) -> List[Document]:
    """BM25 关键词搜索"""
    global _bm25, _docs_meta

    if _bm25 is None:
        build_bm25_index()

    if _bm25 is None or not _docs_meta:
        return []

    results = _bm25.search(query, k=k)
    docs = []
    for idx, score in results:
        doc = Document(
            page_content=_bm25.documents[idx],
            metadata=_docs_meta[idx],
        )
        docs.append(doc)

    return docs
