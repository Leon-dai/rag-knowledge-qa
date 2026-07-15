"""会话模块请求/响应模型"""
from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    """创建会话请求"""
    title: str = "新对话"


class SessionUpdate(BaseModel):
    """更新会话请求"""
    title: str | None = None


class SessionResponse(BaseModel):
    """会话响应"""
    id: str
    user_id: str
    title: str
    message_count: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SessionListResponse(BaseModel):
    """会话列表响应"""
    items: list[SessionResponse]
    total: int
    page: int
    size: int


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(..., min_length=1, max_length=5000, description="消息内容")


class MessageResponse(BaseModel):
    """消息响应"""
    id: str
    session_id: str
    role: str
    content: str
    citations: list | None = None
    created_at: str

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    """消息列表响应"""
    items: list[MessageResponse]
    total: int
    page: int
    size: int
