"""认证业务逻辑"""
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import User
from app.auth.schemas import (
    ChangePasswordRequest,
    LoginResponse,
    TokenResponse,
    UserRegister,
    UserResponse,
)
from app.auth.utils import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


class AuthService:
    """认证服务"""

    @staticmethod
    async def register(db: AsyncSession, data: UserRegister) -> UserResponse:
        """注册新用户"""
        # 检查用户名是否已存在
        result = await db.execute(select(User).where(User.username == data.username))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="用户名已存在",
            )

        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            email=data.email,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return UserResponse.model_validate(user)

    @staticmethod
    async def login(db: AsyncSession, username: str, password: str) -> LoginResponse:
        """用户登录，返回 token 和用户信息"""
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="账号已被禁用",
            )

        token_data = {"sub": user.id, "username": user.username, "role": user.role}

        return LoginResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
            user=UserResponse.model_validate(user),
        )

    @staticmethod
    async def refresh_token(refresh_token_str: str) -> TokenResponse:
        """刷新访问令牌"""
        payload = decode_token(refresh_token_str)
        if payload is None or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh Token 无效或已过期",
            )

        token_data = {
            "sub": payload["sub"],
            "username": payload.get("username", ""),
            "role": payload.get("role", "user"),
        }

        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )

    @staticmethod
    async def change_password(
        db: AsyncSession, user: User, data: ChangePasswordRequest
    ) -> dict:
        """修改密码"""
        if not verify_password(data.old_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="旧密码错误",
            )

        user.password_hash = hash_password(data.new_password)
        await db.commit()
        return {"message": "密码修改成功"}

    @staticmethod
    async def get_me(user: User) -> UserResponse:
        """获取当前用户信息"""
        return UserResponse.model_validate(user)
