"""视频生成API抽象基类"""
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
import requests
from ..utils.logger import get_logger
from ..utils.retry import (
    RetryConfig,
    RetryableMixin,
    APIError,
    APIErrorCode,
    calculate_delay,
)

logger = get_logger(__name__)


class VideoData:
    """视频数据封装"""

    def __init__(
        self,
        data: bytes,
        duration: float,
        resolution: str = "1280x720",
        format: str = "mp4"
    ):
        self.data = data
        self.duration = duration
        self.resolution = resolution
        self.format = format

    def save(self, path: Union[str, Path]) -> None:
        """保存视频文件"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.write(self.data)

    @classmethod
    def from_file(cls, path: Union[str, Path]) -> "VideoData":
        """从文件加载"""
        path = Path(path)
        with open(path, "rb") as f:
            data = f.read()
        return cls(data=data, duration=0.0)


class VideoAPIClient(ABC, RetryableMixin):
    """视频生成API抽象基类"""

    def __init__(self, api_key: str, timeout: int = 600):
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        
        # 配置重试策略
        self.retry_config = RetryConfig(
            max_retries=3,
            base_delay=5.0,
            max_delay=120.0,
            exponential_base=2.0,
            jitter=True,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                requests.exceptions.RequestException,
            ),
            retryable_status_codes=(429, 500, 502, 503, 504),
        )

    @abstractmethod
    def generate(
        self,
        image_path: Path,
        motion_prompt: str,
        duration: float = 5.0
    ) -> VideoData:
        """生成视频"""
        pass

    @abstractmethod
    def check_status(self, task_id: str) -> dict:
        """检查任务状态"""
        pass

    def wait_for_completion(
        self,
        task_id: str,
        timeout: Optional[int] = None,
        poll_interval: float = 5.0
    ) -> dict:
        """等待任务完成 (带指数退避重试)"""
        timeout = timeout or self.timeout
        start_time = time.time()
        consecutive_errors = 0
        max_consecutive_errors = 5

        while time.time() - start_time < timeout:
            try:
                status = self.check_status(task_id)
                consecutive_errors = 0  # 重置错误计数
                state = status.get("state", "unknown")

                if state == "completed":
                    logger.info(f"视频生成完成: {task_id}")
                    return status
                elif state == "failed":
                    error_msg = status.get("error", "未知错误")
                    error_code = status.get("error_code", APIErrorCode.VIDEO_GENERATION_FAILED)
                    logger.error(f"视频生成失败: {error_msg}")
                    raise APIError(
                        code=error_code,
                        message=f"视频生成失败: {error_msg}",
                        details=status,
                        retryable=False
                    )
                elif state in ["pending", "processing"]:
                    logger.debug(f"视频生成中... {task_id} (状态: {state})")
                else:
                    logger.warning(f"未知状态: {state}")

                time.sleep(poll_interval)
                
            except APIError:
                raise
            except Exception as e:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    logger.error(f"连续 {consecutive_errors} 次获取状态失败，放弃重试")
                    raise APIError(
                        code=APIErrorCode.NETWORK_ERROR,
                        message=f"获取任务状态失败: {e}",
                        retryable=False
                    )
                
                delay = calculate_delay(
                    consecutive_errors - 1,
                    self.retry_config.base_delay,
                    self.retry_config.max_delay,
                    self.retry_config.exponential_base,
                    self.retry_config.jitter
                )
                logger.warning(f"获取状态失败: {e}, 等待 {delay:.1f}s 后重试 ({consecutive_errors}/{max_consecutive_errors})")
                time.sleep(delay)

        raise APIError(
            code=APIErrorCode.VIDEO_TASK_TIMEOUT,
            message=f"视频生成超时: {task_id}",
            retryable=True
        )

    def download_video(self, url: str, max_retries: int = 3) -> bytes:
        """下载视频 (带重试)"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                response = self._session.get(url, timeout=120)
                response.raise_for_status()
                return response.content
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    delay = calculate_delay(
                        attempt,
                        self.retry_config.base_delay,
                        self.retry_config.max_delay,
                        self.retry_config.exponential_base,
                        self.retry_config.jitter
                    )
                    logger.warning(f"视频下载失败: {e}, 等待 {delay:.1f}s 后重试")
                    time.sleep(delay)
        
        logger.error(f"视频下载失败: {last_exception}")
        raise APIError(
            code=APIErrorCode.NETWORK_ERROR,
            message=f"视频下载失败: {last_exception}",
            retryable=True
        )


def create_video_client(
    provider: str,
    api_key: str,
    **kwargs
) -> VideoAPIClient:
    """工厂方法创建视频客户端"""
    from .jimeng import JimengClient
    from .kling import KlingClient

    clients = {
        "jimeng": JimengClient,
        "kling": KlingClient,
    }

    if provider not in clients:
        raise ValueError(f"不支持的视频提供商: {provider}, 可选: {list(clients.keys())}")

    return clients[provider](api_key=api_key, **kwargs)
