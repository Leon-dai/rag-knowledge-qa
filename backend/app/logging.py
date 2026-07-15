"""日志配置模块：loguru + 请求ID追踪"""
import sys
import uuid
from contextvars import ContextVar
from pathlib import Path

from loguru import logger

# 请求ID：每个请求唯一，可在任何地方通过 get_request_id() 获取
_request_id: ContextVar[str] = ContextVar("request_id", default="")

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"


def get_request_id() -> str:
    """获取当前请求的 request_id"""
    return _request_id.get()


def set_request_id(rid: str):
    """设置当前请求的 request_id"""
    _request_id.set(rid)


def _log_format(record):
    """自定义日志格式，处理 request_id 缺失的情况"""
    request_id = record["extra"].get("request_id", "")
    if not request_id:
        request_id = "-"

    format_string = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        f"<cyan>{request_id}</cyan> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>\n{exception}"
    )
    return format_string


def configure_logging():
    """配置 loguru：控制台彩色 + 文件持久化"""
    # 移除默认 handler
    logger.remove()

    # 控制台：彩色、带格式
    logger.add(
        sys.stderr,
        format=_log_format,
        level="DEBUG",
        colorize=True,
    )

    # 确保日志目录存在
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # 文件：所有日志（按天轮转，保留30天）
    logger.add(
        LOG_DIR / "app_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[request_id]} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="00:00",  # 每天午夜轮转
        retention="30 days",
        encoding="utf-8",
    )

    # 文件：仅 ERROR 级别（方便快速排查）
    logger.add(
        LOG_DIR / "error_{time:YYYY-MM-DD}.log",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {extra[request_id]} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="00:00",
        retention="30 days",
        encoding="utf-8",
    )

    return logger


# 模块加载时配置
logger = configure_logging()


# 便捷函数：生成新的 request_id
def new_request_id() -> str:
    return uuid.uuid4().hex[:12]
