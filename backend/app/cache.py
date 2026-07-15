"""diskcache 缓存管理模块"""
import hashlib
from functools import wraps
from typing import Any, Callable, Optional

import diskcache

from app.config import settings

# 全局缓存实例
cache = diskcache.Cache(settings.cache_dir)


def cache_key(*args, **kwargs) -> str:
    """生成缓存键（SHA256 哈希）"""
    raw = str(args) + str(sorted(kwargs.items()))
    return hashlib.sha256(raw.encode()).hexdigest()


def cached(ttl: int = 300):
    """缓存装饰器

    Args:
        ttl: 缓存过期时间（秒），默认 5 分钟
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            key = f"{func.__name__}:{cache_key(*args, **kwargs)}"
            result = cache.get(key)
            if result is not None:
                return result
            result = await func(*args, **kwargs)
            cache.set(key, result, expire=ttl)
            return result
        return wrapper
    return decorator


def cache_get(key: str) -> Optional[Any]:
    """获取缓存"""
    return cache.get(key)


def cache_set(key: str, value: Any, ttl: int = 300):
    """设置缓存"""
    cache.set(key, value, expire=ttl)


def cache_delete(key: str):
    """删除缓存"""
    cache.delete(key)


def get_embedding_cache(text: str) -> Optional[list[float]]:
    """获取向量化缓存（永久有效，因为相同文本的向量不变）"""
    key = f"embed:{hashlib.sha256(text.encode()).hexdigest()}"
    return cache.get(key)


def set_embedding_cache(text: str, embedding: list[float]):
    """设置向量化缓存"""
    key = f"embed:{hashlib.sha256(text.encode()).hexdigest()}"
    cache.set(key, embedding, expire=None)  # 永不过期
