"""重试机制模块 - 指数退避重试"""
import asyncio
import functools
import random
import time
from typing import Callable, Type, Tuple, Optional, Any, Union
from .logger import get_logger

logger = get_logger(__name__)


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        retryable_status_codes: Tuple[int, ...] = (429, 500, 502, 503, 504),
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions
        self.retryable_status_codes = retryable_status_codes


DEFAULT_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    base_delay=2.0,
    max_delay=120.0,
    exponential_base=2.0,
    jitter=True,
    retryable_exceptions=(
        ConnectionError,
        TimeoutError,
        OSError,
    ),
)


def calculate_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float,
    jitter: bool
) -> float:
    """计算指数退避延迟时间"""
    delay = base_delay * (exponential_base ** attempt)
    delay = min(delay, max_delay)
    if jitter:
        delay = delay * (0.5 + random.random())
    return delay


def is_retryable_response(response: Any, config: RetryConfig) -> bool:
    """检查响应是否可重试 (针对HTTP响应)"""
    if hasattr(response, 'status_code'):
        return response.status_code in config.retryable_status_codes
    return False


def retry_sync(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable:
    """
    同步重试装饰器 (指数退避)
    
    Args:
        config: 重试配置
        on_retry: 重试回调函数 (attempt, exception, delay)
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = func(*args, **kwargs)
                    
                    if is_retryable_response(result, config) and attempt < config.max_retries:
                        delay = calculate_delay(
                            attempt, 
                            config.base_delay, 
                            config.max_delay,
                            config.exponential_base,
                            config.jitter
                        )
                        logger.warning(
                            f"{func.__name__} 返回状态码 {result.status_code}, "
                            f"第 {attempt + 1}/{config.max_retries + 1} 次尝试, "
                            f"等待 {delay:.1f}s 后重试"
                        )
                        if on_retry:
                            on_retry(attempt, None, delay)
                        time.sleep(delay)
                        continue
                    
                    return result
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_retries:
                        delay = calculate_delay(
                            attempt,
                            config.base_delay,
                            config.max_delay,
                            config.exponential_base,
                            config.jitter
                        )
                        logger.warning(
                            f"{func.__name__} 失败: {e}, "
                            f"第 {attempt + 1}/{config.max_retries + 1} 次尝试, "
                            f"等待 {delay:.1f}s 后重试"
                        )
                        if on_retry:
                            on_retry(attempt, e, delay)
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} 重试 {config.max_retries} 次后仍失败: {e}"
                        )
            
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def retry_async(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable:
    """
    异步重试装饰器 (指数退避)
    
    Args:
        config: 重试配置
        on_retry: 重试回调函数 (attempt, exception, delay)
    """
    if config is None:
        config = DEFAULT_RETRY_CONFIG
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)
                    
                    if is_retryable_response(result, config) and attempt < config.max_retries:
                        delay = calculate_delay(
                            attempt,
                            config.base_delay,
                            config.max_delay,
                            config.exponential_base,
                            config.jitter
                        )
                        logger.warning(
                            f"{func.__name__} 返回状态码 {result.status_code}, "
                            f"第 {attempt + 1}/{config.max_retries + 1} 次尝试, "
                            f"等待 {delay:.1f}s 后重试"
                        )
                        if on_retry:
                            on_retry(attempt, None, delay)
                        await asyncio.sleep(delay)
                        continue
                    
                    return result
                    
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt < config.max_retries:
                        delay = calculate_delay(
                            attempt,
                            config.base_delay,
                            config.max_delay,
                            config.exponential_base,
                            config.jitter
                        )
                        logger.warning(
                            f"{func.__name__} 失败: {e}, "
                            f"第 {attempt + 1}/{config.max_retries + 1} 次尝试, "
                            f"等待 {delay:.1f}s 后重试"
                        )
                        if on_retry:
                            on_retry(attempt, e, delay)
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"{func.__name__} 重试 {config.max_retries} 次后仍失败: {e}"
                        )
            
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


class RetryableMixin:
    """可重试的Mixin类，为API客户端提供重试能力"""
    
    retry_config: RetryConfig = DEFAULT_RETRY_CONFIG
    
    def _execute_with_retry(
        self,
        func: Callable,
        *args,
        config: Optional[RetryConfig] = None,
        **kwargs
    ) -> Any:
        """执行带重试的函数"""
        cfg = config or self.retry_config
        last_exception = None
        
        for attempt in range(cfg.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                
                if is_retryable_response(result, cfg) and attempt < cfg.max_retries:
                    delay = calculate_delay(
                        attempt, cfg.base_delay, cfg.max_delay,
                        cfg.exponential_base, cfg.jitter
                    )
                    logger.warning(f"HTTP {result.status_code}, 等待 {delay:.1f}s 后重试")
                    time.sleep(delay)
                    continue
                    
                return result
                
            except cfg.retryable_exceptions as e:
                last_exception = e
                if attempt < cfg.max_retries:
                    delay = calculate_delay(
                        attempt, cfg.base_delay, cfg.max_delay,
                        cfg.exponential_base, cfg.jitter
                    )
                    logger.warning(f"请求失败: {e}, 等待 {delay:.1f}s 后重试")
                    time.sleep(delay)
                else:
                    logger.error(f"重试 {cfg.max_retries} 次后失败: {e}")
        
        if last_exception:
            raise last_exception


# API错误码定义
class APIErrorCode:
    """API错误码常量"""
    # 通用错误
    UNKNOWN = "UNKNOWN"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_REQUEST = "INVALID_REQUEST"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    INSUFFICIENT_QUOTA = "INSUFFICIENT_QUOTA"
    
    # 视频生成错误
    VIDEO_GENERATION_FAILED = "VIDEO_GENERATION_FAILED"
    VIDEO_CONTENT_FILTERED = "VIDEO_CONTENT_FILTERED"
    VIDEO_TASK_TIMEOUT = "VIDEO_TASK_TIMEOUT"
    
    # TTS错误
    TTS_SYNTHESIS_FAILED = "TTS_SYNTHESIS_FAILED"
    TTS_VOICE_NOT_FOUND = "TTS_VOICE_NOT_FOUND"
    
    # 图像生成错误
    IMAGE_GENERATION_FAILED = "IMAGE_GENERATION_FAILED"
    COMFYUI_WORKFLOW_ERROR = "COMFYUI_WORKFLOW_ERROR"


class APIError(Exception):
    """API错误异常"""
    
    def __init__(
        self,
        code: str,
        message: str,
        details: Optional[dict] = None,
        retryable: bool = False,
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        self.retryable = retryable
        super().__init__(f"[{code}] {message}")
    
    def __repr__(self) -> str:
        return f"APIError(code={self.code!r}, message={self.message!r}, retryable={self.retryable})"
