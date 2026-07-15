"""知识库管理路由"""
import os
from fastapi import APIRouter, Depends, File, UploadFile, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin, get_current_user
from app.auth.models import User
from app.database import get_db
from app.kb.schemas import DocumentListResponse, DocumentDetailResponse
from app.kb.service import DocumentService
from app.kb.models import Document

router = APIRouter(prefix="/api/docs", tags=["知识库管理"])


@router.post("/upload", status_code=202)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """上传文档（管理员专属）。
    文档先保存到磁盘并创建记录，然后通过 BackgroundTasks 异步处理。
    """
    doc = await DocumentService.upload(db, file, current_user.id)
    # 将文档处理加入后台任务
    background_tasks.add_task(DocumentService.process_document, doc.id)
    return doc


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    status: str | None = Query(None, description="状态筛选"),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取文档列表（管理员专属）"""
    return await DocumentService.list_documents(db, page, size, status)


@router.get("/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(
    doc_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取文档详情（管理员专属）"""
    return await DocumentService.get_document(db, doc_id)


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除文档（管理员专属）"""
    return await DocumentService.delete_document(db, doc_id)


@router.post("/{doc_id}/reprocess", status_code=202)
async def reprocess_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """重新处理文档（管理员专属）"""
    doc = await DocumentService.reprocess_document(db, doc_id)
    background_tasks.add_task(DocumentService.process_document, doc.id)
    return doc


@router.get("/{doc_id}/file")
async def download_document(
    doc_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下载文档文件"""
    from sqlalchemy import select
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    if not os.path.exists(doc.file_path):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    return FileResponse(doc.file_path, filename=doc.original_filename)


@router.get("/{doc_id}/preview")
async def preview_document_content(
    doc_id: str,
    page: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取文档的文本内容用于在线预览（所有登录用户）"""
    from sqlalchemy import select
    from app.rag.retriever import get_vector_store

    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if doc is None:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文档不存在")

    # 从 ChromaDB 获取该文档所有 chunk，按页码和chunk排序
    vector_store = get_vector_store()
    try:
        all_data = vector_store.get(
            where={"document_id": doc_id},
            include=["documents", "metadatas"],
        )
    except Exception:
        all_data = {"ids": [], "documents": [], "metadatas": []}

    # 组装预览内容
    chunks = []
    for i in range(len(all_data["ids"])):
        content = all_data["documents"][i]
        meta = all_data["metadatas"][i]
        chunks.append({
            "page": meta.get("page", 0),
            "chunk_index": meta.get("chunk_index", i),
            "content": content,
        })

    # 按页码排序
    chunks.sort(key=lambda c: (c["page"], c["chunk_index"]))

    # 高亮目标页
    highlight_page = page

    return {
        "doc_id": doc_id,
        "filename": doc.original_filename,
        "file_type": doc.file_type,
        "total_chunks": len(chunks),
        "highlight_page": highlight_page,
        "chunks": chunks,
    }
