"""知识库管理业务逻辑"""
import os
import uuid
import shutil
from pathlib import Path

from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.kb.models import Document
from app.kb.schemas import DocumentResponse, DocumentListResponse, DocumentDetailResponse
from app.kb.loader import load_document
from app.kb.splitter import split_documents
from app.kb.embedder import get_embeddings
from app.logging import logger

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".md", ".csv", ".xlsx", ".xls"}


def _parse_tags(tags_str: str | None) -> list[str] | None:
    """解析数据库中存储的 JSON 标签字符串"""
    if not tags_str:
        return None
    try:
        import json as _json
        return _json.loads(tags_str)
    except Exception:
        return None


class DocumentService:
    """文档管理服务"""

    # ==================== AI 智能分类 ====================

    ANALYZE_PROMPT = """你是一个知识管理专家。分析以下文档内容，判断它属于什么类型。

文档内容（开头+结尾）：
{content}

请根据文档内容，给出最精准的分类名称（2-6个字，如"简历""行业报告""会议纪要""产品需求""技术方案""学术论文""数据报表""操作指南""录取名单""试题解析""产品介绍""个人简历"等，越具体越好）。不要使用"其他"作为分类，除非文档内容实在无法归类。

用 JSON 格式回复（不要其他内容）：
{{"category": "你判断的分类名称", "tags": ["标签1", "标签2", "标签3"], "summary": "一句话概括文档核心内容，限80字"}}"""

    @staticmethod
    async def _analyze_document(doc, lc_docs: list, db):
        """AI 分析文档：提取分类、标签、摘要，存入数据库"""
        import json as json_mod

        try:
            # 拼接文档内容：前 3000 字 + 后 1000 字
            full_text = "\n".join([d.page_content for d in lc_docs])
            if len(full_text) <= 4000:
                sample = full_text
            else:
                sample = full_text[:3000] + "\n...(中间省略)...\n" + full_text[-1000:]

            prompt = DocumentService.ANALYZE_PROMPT.format(content=sample)

            from app.rag.service import RAGService
            llm = RAGService._get_llm(model="qwen-turbo", streaming=False)
            response = llm.invoke(prompt)
            result = response.content.strip()

            # 解析 JSON
            json_match = __import__('re').search(r'\{[^}]+\}', result)
            if json_match:
                data = json_mod.loads(json_match.group())
                doc.category = data.get("category", "其他")[:20]
                doc.tags = json_mod.dumps(data.get("tags", []), ensure_ascii=False)
                doc.summary = data.get("summary", "")[:200]
                await db.commit()
                logger.info(f"AI 分类完成: {doc.original_filename} → {doc.category}")
            else:
                logger.warning(f"AI 分类 JSON 解析失败: {result[:100]}")

        except Exception as e:
            logger.warning(f"AI 分类失败: {doc.original_filename}: {e}")
            # 分类失败不影响主流程，字段保持为 None

    # ==================== 文档 CRUD ====================

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
            category=doc.category,
            tags=_parse_tags(doc.tags),
            summary=doc.summary,
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
                category=doc.category,
                tags=_parse_tags(doc.tags),
                summary=doc.summary,
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
            category=doc.category,
            tags=_parse_tags(doc.tags),
            summary=doc.summary,
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

                # 2.5 AI 智能分类：异步分析文档内容，提取分类、标签、摘要
                await DocumentService._analyze_document(doc, lc_docs, db)

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
    async def get_dashboard(db: AsyncSession) -> dict:
        """知识库仪表盘：返回全量文档（含状态）和分类统计"""
        result = await db.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        all_docs = result.scalars().all()

        # 状态统计
        status_counts = {"total": len(all_docs), "ready": 0, "processing": 0, "error": 0, "uploaded": 0}
        for doc in all_docs:
            if doc.status in status_counts:
                status_counts[doc.status] += 1

        # 已就绪文档按分类分组
        ready_docs = [d for d in all_docs if d.status == "ready"]
        categories: dict[str, list] = {}
        for doc in ready_docs:
            cat = doc.category or "未分类"
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "id": doc.id,
                "original_filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "chunk_count": doc.chunk_count,
                "summary": doc.summary,
                "tags": _parse_tags(doc.tags),
                "created_at": str(doc.created_at) if doc.created_at else "",
            })

        # 完整文档列表
        items = [
            {
                "id": doc.id,
                "original_filename": doc.original_filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status,
                "error_message": doc.error_message,
                "chunk_count": doc.chunk_count,
                "category": doc.category,
                "tags": _parse_tags(doc.tags),
                "summary": doc.summary,
                "created_at": str(doc.created_at) if doc.created_at else "",
            }
            for doc in all_docs
        ]

        return {
            "total": len(all_docs),
            "status_counts": status_counts,
            "categories": [
                {"name": cat, "count": len(items), "items": items}
                for cat, items in sorted(categories.items(), key=lambda x: -len(x[1]))
            ],
            "items": items,
        }

    @staticmethod
    async def get_daily_review(db: AsyncSession) -> dict | None:
        """每日回顾：随机返回一条已处理文档"""
        result = await db.execute(
            select(Document)
            .where(Document.status == "ready", Document.summary.isnot(None))
            .order_by(func.random())
            .limit(1)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            return None

        return {
            "id": doc.id,
            "original_filename": doc.original_filename,
            "file_type": doc.file_type,
            "category": doc.category,
            "tags": _parse_tags(doc.tags),
            "summary": doc.summary,
            "created_at": str(doc.created_at) if doc.created_at else "",
        }

    @staticmethod
    async def update_metadata(
        db: AsyncSession,
        doc_id: str,
        original_filename: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        summary: str | None = None,
    ) -> DocumentResponse:
        """手动更新文档的分类、标签、摘要、文件名"""
        import json as json_mod

        doc = await DocumentService._get_or_404(db, doc_id)

        if original_filename is not None:
            doc.original_filename = original_filename[:200] if original_filename else doc.original_filename
        if category is not None:
            doc.category = category[:20] if category else None
        if tags is not None:
            doc.tags = json_mod.dumps(tags, ensure_ascii=False) if tags else None
        if summary is not None:
            doc.summary = summary[:200] if summary else None

        await db.commit()
        await db.refresh(doc)

        logger.info(f"文档元数据已更新: {doc.original_filename}")

        return DocumentResponse(
            id=doc.id,
            original_filename=doc.original_filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            chunk_count=doc.chunk_count,
            category=doc.category,
            tags=_parse_tags(doc.tags),
            summary=doc.summary,
            created_at=str(doc.created_at) if doc.created_at else "",
            updated_at=str(doc.updated_at) if doc.updated_at else "",
        )

    @staticmethod
    async def reclassify_all(db: AsyncSession) -> dict:
        """批量重新分类所有已处理文档（覆盖旧分类）"""
        result = await db.execute(
            select(Document).where(Document.status == "ready")
        )
        docs = result.scalars().all()

        if not docs:
            return {"message": "没有已处理的文档", "count": 0}

        success = 0
        failed = 0
        for doc in docs:
            try:
                # 清除旧分类，重新 AI 分析
                doc.category = None
                doc.tags = None
                doc.summary = None
                await db.commit()

                from app.kb.loader import load_document
                lc_docs = load_document(doc.file_path, doc.original_filename)
                await DocumentService._analyze_document(doc, lc_docs, db)
                success += 1
            except Exception as e:
                logger.warning(f"重新分类失败: {doc.original_filename}: {e}")
                failed += 1

        return {
            "message": f"重新分类完成: {success} 成功, {failed} 失败",
            "count": success,
            "failed": failed,
        }

    @staticmethod
    async def _get_or_404(db: AsyncSession, doc_id: str) -> Document:
        """获取文档，不存在则抛出 404"""
        result = await db.execute(select(Document).where(Document.id == doc_id))
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")
        return doc
