"""知识库模块请求/响应模型"""
from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    """文档响应"""
    id: str
    original_filename: str
    file_type: str
    file_size: int
    status: str
    error_message: str | None = None
    chunk_count: int = 0
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    items: list[DocumentResponse]
    total: int
    page: int
    size: int


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应（不包含内部文件路径）"""
    filename: str
    uploaded_by: str | None = None


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
