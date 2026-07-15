"""知识库管理业务逻辑"""
import os
import uuid
import shutil
from pathlib import Path

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.kb.models import Document
from app.kb.schemas import DocumentResponse, DocumentListResponse, DocumentDetailResponse
from app.kb.loader import load_document
from app.kb.splitter import split_documents
from app.kb.embedder import get_embeddings
from app.logging import logger

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".xls"}


class DocumentService:
    """文档管理服务"""

    @staticmethod
    async def upload(db: AsyncSession, file: UploadFile, user_id: str) -> DocumentResponse:
        """上传文档并返回文档记录"""
        if not file.filename:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件名不能为空")

        ext = Path(file.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件类型: {ext}。支持: {', '.join(ALLOWED_EXTENSIONS)}",
            )

        # 保存文件
        doc_id = str(uuid.uuid4())
        saved_filename = f"{doc_id}{ext}"
        upload_path = Path(settings.upload_dir) / saved_filename

        content = await file.read()
        file_size = len(content)

        if file_size > settings.max_upload_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"文件大小超过限制 ({settings.max_upload_size // 1024 // 1024}MB)",
            )

        upload_path.write_bytes(content)

        # 创建数据库记录
        doc = Document(
            id=doc_id,
            filename=saved_filename,
            original_filename=file.filename,
            file_path=str(upload_path),
            file_type=ext.lstrip("."),
            file_size=file_size,
            status="uploaded",
            uploaded_by=user_id,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        return DocumentResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=str(doc.created_at) if doc.created_at else "",
            updated_at=str(doc.updated_at) if doc.updated_at else "",
        )

    @staticmethod
    async def list_documents(
        db: AsyncSession,
        page: int = 1,
        size: int = 10,
        status_filter: str | None = None,
    ) -> DocumentListResponse:
        """分页获取文档列表"""
        query = select(Document)
        count_query = select(func.count(Document.id))

        if status_filter:
            query = query.where(Document.status == status_filter)
            count_query = count_query.where(Document.status == status_filter)

        query = query.order_by(Document.created_at.desc()).offset((page - 1) * size).limit(size)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        result = await db.execute(query)
        documents = result.scalars().all()

        items = [
            DocumentResponse(
                id=doc.id,
                original_filename=doc.original_filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                status=doc.status,
                error_message=doc.error_message,
                chunk_count=doc.chunk_count,
                created_at=str(doc.created_at) if doc.created_at else "",
                updated_at=str(doc.updated_at) if doc.updated_at else "",
            )
            for doc in documents
        ]

        return DocumentListResponse(items=items, total=total, page=page, size=size)

    @staticmethod
    async def get_document(db: AsyncSession, doc_id: str) -> DocumentDetailResponse:
        """获取文档详情（不返回内部文件路径）"""
        doc = await DocumentService._get_or_404(db, doc_id)
        return DocumentDetailResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            error_message=doc.error_message,
            chunk_count=doc.chunk_count,
            uploaded_by=doc.uploaded_by,
            created_at=str(doc.created_at) if doc.created_at else "",
            updated_at=str(doc.updated_at) if doc.updated_at else "",
        )

    @staticmethod
    async def delete_document(db: AsyncSession, doc_id: str) -> dict:
        """删除文档及其向量数据"""
        doc = await DocumentService._get_or_404(db, doc_id)

        # 删除 ChromaDB 中的向量
        try:
            from app.rag.retriever import get_vector_store
            vector_store = get_vector_store()
            # 按 document_id 过滤删除
            vector_store._collection.delete(
                where={"document_id": doc_id}
            )
        except Exception as e:
            logger.warning(f"删除向量数据失败 doc={doc_id}: {e}")

        # 删除磁盘上的文件
        try:
            if os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception as e:
            logger.warning(f"删除文件失败 path={doc.file_path}: {e}")

        # 删除数据库记录
        await db.delete(doc)
        await db.commit()

        # 重建 BM25 索引
        from app.rag.bm25_retriever import build_bm25_index
        build_bm25_index()

        return {"message": "文档已删除"}

    @staticmethod
    async def reprocess_document(db: AsyncSession, doc_id: str) -> DocumentResponse:
        """重新处理文档：先删除旧向量，再重新处理"""
        doc = await DocumentService._get_or_404(db, doc_id)

        # 删除旧向量数据
        try:
            from app.rag.retriever import get_vector_store
            vector_store = get_vector_store()
            vector_store._collection.delete(
                where={"document_id": doc_id}
            )
            logger.info(f"已删除旧向量: doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"删除旧向量失败: {e}")

        # 删除旧 BM25 索引（会重建）
        try:
            from app.rag.bm25_retriever import build_bm25_index
            build_bm25_index()
        except Exception as e:
            logger.warning(f"重建 BM25 索引失败: {e}")

        doc.status = "uploaded"
        doc.error_message = None
        doc.chunk_count = 0
        await db.commit()
        await db.refresh(doc)

        return DocumentResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count,
            created_at=str(doc.created_at) if doc.created_at else "",
            updated_at=str(doc.updated_at) if doc.updated_at else "",
        )

    @staticmethod
    async def process_document(doc_id: str):
        """后台处理文档：解析 → 父子分块 → 向量化 → 存储

        参考: All-in-RAG C8 — Small-to-Big Retrieval (Parent Document Retriever)
        - 子块（250字符）：用于精确向量检索
        - 父块（1200字符）：检索命中子块后，将父块喂给 LLM 生成回答

        此方法在 BackgroundTasks 中异步执行。
        """
        from app.database import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()
            if doc is None:
                return

            try:
                # 1. 更新状态为处理中
                doc.status = "processing"
                await db.commit()

                # 2. 加载文档
                lc_docs = load_document(doc.file_path, doc.original_filename)

                # 3. 父子分块（Small-to-Big）
                from app.kb.parent_splitter import split_documents_with_parents
                child_chunks, parent_map = split_documents_with_parents(
                    lc_docs,
                    doc_id=doc.id,
                    doc_title=doc.original_filename,
                    parent_chunk_size=1200,
                    child_chunk_size=250,
                )

                if not child_chunks:
                    raise ValueError("文档解析后没有有效内容")

                # 4. 向量化 & 存储（子块 + 父块一起存）
                embeddings = get_embeddings()
                from app.rag.retriever import get_vector_store, tag_embedding_model
                vector_store = get_vector_store()

                # 存储子块（用于检索）
                vector_store.add_documents(child_chunks)

                # 存储父块（用于生成）
                parent_docs = list(parent_map.values())
                if parent_docs:
                    vector_store.add_documents(parent_docs)

                # 标记 Embedding 模型版本
                tag_embedding_model()

                # 5. 更新状态为就绪
                doc.status = "ready"
                doc.chunk_count = len(child_chunks)  # 只统计子块数量
                doc.error_message = None
                await db.commit()

                # 6. 重建 BM25 索引
                from app.rag.bm25_retriever import build_bm25_index
                build_bm25_index()

                logger.info(f"文档处理完成: {doc.original_filename}, {len(child_chunks)} child chunks, {len(parent_docs)} parent chunks")

            except Exception as e:
                doc.status = "error"
                doc.error_message = str(e)
                await db.commit()
                logger.error(f"文档处理失败: {doc.original_filename}: {e}")

    @staticmethod
    async def _get_or_404(db: AsyncSession, doc_id: str) -> Document:
        """获取文档，不存在则抛出 404"""
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
        return doc
