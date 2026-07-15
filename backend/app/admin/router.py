"""管理员路由"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import require_admin
from app.auth.models import User as UserModel
from app.database import get_db
from app.admin.service import AdminService
from app.model_settings import (
    get_all_available_models,
    switch_llm_model,
    switch_embedding_model,
)
from app.rag.retriever import reset_vector_store, check_embedding_model_mismatch

router = APIRouter(prefix="/api/admin", tags=["管理员"])


@router.get("/stats")
async def get_stats(
    current_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取系统统计数据（管理员专属）"""
    return await AdminService.get_stats(db)


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """获取用户列表（管理员专属）"""
    return await AdminService.list_users(db, page, size)


@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    data: dict,
    current_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用用户（管理员专属）"""
    return await AdminService.update_user_status(db, user_id, data.get("is_active", True), current_user.id)


# ==================== 模型管理 ====================

@router.get("/models")
async def get_models(current_user: UserModel = Depends(require_admin)):
    """获取当前模型配置和可用模型列表"""
    models = get_all_available_models()
    mismatch = check_embedding_model_mismatch()
    models["embedding_mismatch"] = mismatch
    return models


@router.put("/models/llm")
async def switch_llm(data: dict, current_user: UserModel = Depends(require_admin)):
    """切换 LLM 模型，无需重启"""
    model_name = data.get("model", "")
    try:
        result = switch_llm_model(model_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/models/embedding")
async def switch_embedding(data: dict, current_user: UserModel = Depends(require_admin)):
    """切换 Embedding 模型，无需重启（⚠️ 切换后需重新处理所有文档）"""
    model_name = data.get("model", "")
    try:
        result = switch_embedding_model(model_name)
        reset_vector_store()  # 强制重建 ChromaDB 实例
        return {
            **result,
            "warning": "Embedding模型已切换！已有向量是用旧模型生成的，建议进入知识库管理页面，对所有文档点击「重新处理」。"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
