"""应用配置模块"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置，从 .env 文件和环境变量加载"""

    # 阿里云百炼
    dashscope_api_key: str = ""

    # Tavily 搜索 API
    tavily_api_key: str = ""

    # JWT
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # 数据库
    database_url: str = "sqlite+aiosqlite:///./data/app.db"

    # ChromaDB
    chroma_persist_dir: str = "./data/chroma_db"

    # 文件上传
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 20 * 1024 * 1024  # 20MB

    # 缓存
    cache_dir: str = "./data/cache"

    # 服务
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 数据库同步 URL（Alembic 迁移用）
    @property
    def database_url_sync(self) -> str:
        return self.database_url.replace("sqlite+aiosqlite://", "sqlite://")

    # LLM 模型配置
    # qwen-turbo: 有免费额度，适合开发测试
    # qwen-plus: 付费，效果更好（额度充足时推荐）
    # qwen-max: 付费，最强效果
    llm_model: str = "qwen-turbo"
    llm_model_light: str = "qwen-turbo"
    # text-embedding-v1: 免费额度 100万 tokens/月
    # text-embedding-v2: 付费，效果更好
    embedding_model: str = "text-embedding-v1"

    # ChromaDB collection 名
    chroma_collection_name: str = "ecommerce_kb"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

settings = Settings()

# 确保数据目录存在
_data_dirs = [
    settings.upload_dir,
    settings.chroma_persist_dir,
    settings.cache_dir,
]
for _d in _data_dirs:
    Path(_d).mkdir(parents=True, exist_ok=True)
