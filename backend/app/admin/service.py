"""管理员业务逻辑"""
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.auth.models import User
from app.kb.models import Document
from app.chat.models import Session, Message
from app.logging import logger


class AdminService:
    """管理员服务"""

    @staticmethod
    async def get_stats(db: AsyncSession) -> dict:
        """获取系统统计数据"""
        user_count = await db.scalar(select(func.count(User.id)))
        doc_count = await db.scalar(select(func.count(Document.id)))
        ready_doc_count = await db.scalar(
            select(func.count(Document.id)).where(Document.status == "ready")
        )
        session_count = await db.scalar(select(func.count(Session.id)))
        message_count = await db.scalar(select(func.count(Message.id)))

        # 计算总向量数（从文档的 chunk_count 求和）
        chunk_sum = await db.scalar(
            select(func.sum(Document.chunk_count)).where(Document.status == "ready")
        )

        return {
            "user_count": user_count or 0,
            "document_count": doc_count or 0,
            "ready_document_count": ready_doc_count or 0,
            "session_count": session_count or 0,
            "message_count": message_count or 0,
            "chunk_count": chunk_sum or 0,
        }

    @staticmethod
    async def list_users(
        db: AsyncSession,
        page: int = 1,
        size: int = 20,
    ) -> dict:
        """获取用户列表"""
        query = (
            select(User)
            .order_by(User.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        count_query = select(func.count(User.id))

        total = await db.scalar(count_query) or 0
        result = await db.execute(query)
        users = result.scalars().all()

        items = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "created_at": str(u.created_at),
            }
            for u in users
        ]

        return {"items": items, "total": total, "page": page, "size": size}

    @staticmethod
    async def update_user_status(db: AsyncSession, user_id: str, is_active: bool, current_user_id: str) -> dict:
        """启用/禁用用户"""
        # 不能禁用自己
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能禁用当前登录的管理员账号"
            )

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        # 如果要禁用最后一个管理员，阻止
        if not is_active and user.role == "admin":
            admin_count = await db.scalar(
                select(func.count(User.id)).where(User.role == "admin", User.is_active == True)
            )
            if admin_count and admin_count <= 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能禁用最后一个管理员账号"
                )

        user.is_active = is_active
        await db.commit()
        logger.info(f"用户状态更新: user_id={user_id}, is_active={is_active}")
        return {"message": f"用户已{'启用' if is_active else '禁用'}"}
