"""会话与消息业务逻辑"""
import json
import uuid
from datetime import datetime

from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.models import Session, Message
from app.chat.schemas import (
    SessionResponse,
    SessionListResponse,
    MessageResponse,
    MessageListResponse,
)
from app.rag.service import RAGService


def count_tokens(text: str) -> int:
    """使用 tiktoken 精确计算 token 数量"""
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(encoding.encode(text))
    except Exception:
        # tiktoken 不可用时，使用粗略估算（中文约 1.5 token/字）
        return int(len(text) * 1.5)


class ChatService:
    """会话与消息服务"""

    # ==================== 会话管理 ====================

    @staticmethod
    async def create_session(db: AsyncSession, user_id: str, title: str = "新对话") -> SessionResponse:
        """创建新会话"""
        session = Session(user_id=user_id, title=title)
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            message_count=session.message_count,
            created_at=str(session.created_at),
            updated_at=str(session.updated_at),
        )

    @staticmethod
    async def list_sessions(
        db: AsyncSession,
        user_id: str,
        page: int = 1,
        size: int = 20,
    ) -> SessionListResponse:
        """获取会话列表（按最后活跃时间倒序）"""
        query = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.updated_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        count_query = (
            select(func.count(Session.id))
            .where(Session.user_id == user_id)
        )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        result = await db.execute(query)
        sessions = result.scalars().all()

        items = [
            SessionResponse(
                id=s.id,
                user_id=s.user_id,
                title=s.title,
                message_count=s.message_count,
                created_at=str(s.created_at),
                updated_at=str(s.updated_at),
            )
            for s in sessions
        ]

        return SessionListResponse(items=items, total=total, page=page, size=size)

    @staticmethod
    async def get_session(db: AsyncSession, session_id: str, user_id: str) -> SessionResponse:
        """获取会话详情（验证归属）"""
        session = await ChatService._get_session_or_404(db, session_id, user_id)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            message_count=session.message_count,
            created_at=str(session.created_at),
            updated_at=str(session.updated_at),
        )

    @staticmethod
    async def update_session(
        db: AsyncSession, session_id: str, user_id: str, title: str | None
    ) -> SessionResponse:
        """更新会话标题"""
        session = await ChatService._get_session_or_404(db, session_id, user_id)
        if title is not None:
            session.title = title
        await db.commit()
        await db.refresh(session)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            message_count=session.message_count,
            created_at=str(session.created_at),
            updated_at=str(session.updated_at),
        )

    @staticmethod
    async def delete_session(db: AsyncSession, session_id: str, user_id: str) -> dict:
        """删除会话及其所有消息"""
        session = await ChatService._get_session_or_404(db, session_id, user_id)
        await db.delete(session)
        await db.commit()
        return {"message": "会话已删除"}

    # ==================== 消息管理 ====================

    @staticmethod
    async def get_messages(
        db: AsyncSession,
        session_id: str,
        user_id: str,
        page: int = 1,
        size: int = 50,
    ) -> MessageListResponse:
        """获取会话消息列表"""
        # 验证归属
        await ChatService._get_session_or_404(db, session_id, user_id)

        query = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.asc())
            .offset((page - 1) * size)
            .limit(size)
        )
        count_query = (
            select(func.count(Message.id))
            .where(Message.session_id == session_id)
        )

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        result = await db.execute(query)
        messages = result.scalars().all()

        items = []
        for m in messages:
            citations = None
            if m.citations:
                try:
                    citations = json.loads(m.citations)
                except json.JSONDecodeError:
                    citations = []

            items.append(MessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                citations=citations,
                created_at=str(m.created_at),
            ))

        return MessageListResponse(items=items, total=total, page=page, size=size)

    @staticmethod
    async def send_message(
        db: AsyncSession,
        session_id: str,
        user_id: str,
        content: str,
        search_mode: str = "local",
    ) -> StreamingResponse:
        """发送消息并返回 SSE 流式响应"""
        # 验证会话归属
        session = await ChatService._get_session_or_404(db, session_id, user_id)

        # 1. 保存用户消息
        user_msg = Message(
            id=str(uuid.uuid4()),
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=content,
        )
        db.add(user_msg)

        # 2. 获取对话历史
        history_result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        history = history_result.scalars().all()
        chat_history = [
            {"role": m.role, "content": m.content}
            for m in reversed(history)
        ]

        # 3. 更新会话消息数
        session.message_count = (session.message_count or 0) + 1
        await db.commit()

        # 4. 创建流式响应
        async def generate_and_save():
            full_answer = ""
            citations = []

            # 使用独立的数据库会话保存 AI 响应
            from app.database import async_session_factory
            async with async_session_factory() as save_db:
                assistant_msg = Message(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    session_id=session_id,
                    role="assistant",
                    content="",
                )

                async for sse_data in RAGService.query(content, chat_history, search_mode):
                    # 解析 SSE 数据获取 token 和 citations
                    if "data:" in sse_data or sse_data.startswith("data:"):
                        # 直接透传 SSE 给客户端
                        pass
                    yield sse_data

                    # 解析累积的文本
                    try:
                        data_str = sse_data.strip()
                        if data_str.startswith("data: "):
                            parsed = json.loads(data_str[6:])
                            if "token" in parsed:
                                full_answer += parsed["token"]
                            elif "sources" in parsed:
                                citations = parsed["sources"]
                    except (json.JSONDecodeError, IndexError):
                        pass

                # 保存 AI 回答
                assistant_msg.content = full_answer
                assistant_msg.citations = json.dumps(citations, ensure_ascii=False)
                assistant_msg.output_tokens = count_tokens(full_answer)
                save_db.add(assistant_msg)

                # 更新会话消息数和标题
                result = await save_db.execute(select(Session).where(Session.id == session_id))
                session_to_update = result.scalar_one_or_none()
                if session_to_update:
                    session_to_update.message_count = (session_to_update.message_count or 0) + 1
                    # 首次对话后自动生成标题
                    if session_to_update.title == "新对话" and session_to_update.message_count >= 2:
                        try:
                            session_to_update.title = content[:30]  # 用第一个问题截取作为标题
                        except Exception:
                            pass

                await save_db.commit()

        return StreamingResponse(
            generate_and_save(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream; charset=utf-8",
            },
        )

    # ==================== 搜索 ====================

    @staticmethod
    async def search(db: AsyncSession, user_id: str, query: str) -> dict:
        """搜索会话（标题 + 消息内容）"""
        keyword = f"%{query}%"
        seen = set()

        # 1. 标题匹配的会话
        session_result = await db.execute(
            select(Session).where(
                and_(Session.user_id == user_id, Session.title.like(keyword))
            ).order_by(Session.updated_at.desc()).limit(20)
        )
        matched = {s.id: s for s in session_result.scalars().all()}
        seen.update(matched.keys())

        # 2. 消息内容匹配的会话
        msg_result = await db.execute(
            select(Message.session_id, Session)
            .join(Session, Session.id == Message.session_id)
            .where(
                and_(
                    Message.content.like(keyword),
                    or_(Session.user_id == user_id, Message.user_id == user_id),
                )
            ).distinct().limit(50)
        )
        for sid, s in msg_result.all():
            if sid not in seen:
                matched[sid] = s
                seen.add(sid)

        # 3. 构建结果
        items = []
        for s in list(matched.values())[:20]:
            match_msg = await db.execute(
                select(Message).where(
                    Message.session_id == s.id, Message.content.like(keyword)
                ).order_by(Message.created_at.asc()).limit(1)
            )
            first_hit = match_msg.scalar_one_or_none()
            items.append({
                "id": s.id,
                "title": s.title,
                "message_count": s.message_count,
                "updated_at": str(s.updated_at),
                "match_preview": _hilight(first_hit.content, query) if first_hit else None,
                "match_message_id": first_hit.id if first_hit else None,
            })

        return {"items": items, "total": len(items), "query": query}

    # ==================== 工具方法 ====================

    @staticmethod
    async def _get_session_or_404(db: AsyncSession, session_id: str, user_id: str) -> Session:
        """获取会话并验证归属"""
        result = await db.execute(
            select(Session).where(
                and_(Session.id == session_id, Session.user_id == user_id)
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在",
            )
        return session


def _hilight(text: str, query: str, ctx: int = 40) -> str:
    """提取关键词周围上下文"""
    i = text.lower().find(query.lower())
    if i == -1:
        return text[:80] + ("..." if len(text) > 80 else "")
    s = max(0, i - ctx)
    e = min(len(text), i + len(query) + ctx)
    return ("..." if s > 0 else "") + text[s:e] + ("..." if e < len(text) else "")
