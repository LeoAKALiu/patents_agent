"""工具模块 —— 日志、去重哈希、重试装饰器。"""
import hashlib
import functools
import time
import logging
from typing import Callable, Any


def setup_logging(verbose: bool = False) -> logging.Logger:
    """配置带时间戳的结构化日志。"""
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    logging.basicConfig(level=level, format=fmt, datefmt="%Y-%m-%d %H:%M:%S")
    return logging.getLogger("issuer")


logger = setup_logging()


def hash_title(title: str) -> str:
    """对 title 做 sha256 取前 12 位 hex，用于 issue 去重。"""
    return hashlib.sha256(title.strip().encode()).hexdigest()[:12]


def retry(max_attempts: int = 3, backoff: float = 2.0) -> Callable:
    """装饰器：自动重试，指数退避。所有异常统一使用 backoff^attempt 退避重试。"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(
                        "[%s/%s] %s 失败: %s",
                        attempt, max_attempts, func.__name__, e,
                    )
                    if attempt < max_attempts:
                        wait = backoff ** attempt
                        logger.info("等待 %.1f 秒后重试...", wait)
                        time.sleep(wait)
            raise last_exception  # type: ignore[misc]
        return wrapper
    return decorator


def safe_filename(path: str) -> bool:
    """校验文件路径不包含危险操作（.. / 遍历）。"""
    import os
    if not path or not path.strip():
        return False
    normalized = os.path.normpath(path)
    if normalized.startswith("..") or os.path.isabs(normalized):
        return False
    return True
