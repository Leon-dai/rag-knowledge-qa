"""会话与对话路由"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.models import User
from app.chat.schemas import (
    SessionCreate,
    SessionUpdate,
    SessionListResponse,
    SessionResponse,
    SendMessageRequest,
    MessageListResponse,
)
from app.chat.service import ChatService
from app.database import get_db

router = APIRouter(tags=["会话与对话"])


# ==================== 会话 ====================

@router.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    data: SessionCreate | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新会话"""
    title = data.title if data else "新对话"
    return await ChatService.create_session(db, current_user.id, title)


@router.get("/api/sessions", response_model=SessionListResponse)
async def list_sessions(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的会话列表"""
    return await ChatService.list_sessions(db, current_user.id, page, size)


# 搜索路由必须在 /{session_id} 前面，否则 "search" 会被匹配为 session_id
@router.get("/api/sessions/search")
async def search_sessions(
    q: str = Query(..., min_length=1, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """搜索会话（标题 + 消息内容）"""
    return await ChatService.search(db, current_user.id, q)


@router.get("/api/sessions/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话详情"""
    return await ChatService.get_session(db, session_id, current_user.id)


@router.put("/api/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    data: SessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新会话（如重命名）"""
    return await ChatService.update_session(db, session_id, current_user.id, data.title)


@router.delete("/api/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话"""
    return await ChatService.delete_session(db, session_id, current_user.id)


# ==================== 消息 ====================

@router.get("/api/sessions/{session_id}/messages", response_model=MessageListResponse)
async def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话的消息列表"""
    return await ChatService.get_messages(db, session_id, current_user.id, page, size)


@router.post("/api/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息，返回 SSE 流式响应"""
    return await ChatService.send_message(
        db, session_id, current_user.id, data.content, data.search_mode
    )
