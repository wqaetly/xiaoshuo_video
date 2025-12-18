"""视频生成API抽象基类"""
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union
import requests
from ..utils.logger import get_logger

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


class VideoAPIClient(ABC):
    """视频生成API抽象基类"""

    def __init__(self, api_key: str, timeout: int = 600):
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()

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
        """等待任务完成"""
        timeout = timeout or self.timeout
        start_time = time.time()

        while time.time() - start_time < timeout:
            status = self.check_status(task_id)
            state = status.get("state", "unknown")

            if state == "completed":
                logger.info(f"视频生成完成: {task_id}")
                return status
            elif state == "failed":
                error_msg = status.get("error", "未知错误")
                logger.error(f"视频生成失败: {error_msg}")
                raise RuntimeError(f"视频生成失败: {error_msg}")
            elif state in ["pending", "processing"]:
                logger.debug(f"视频生成中... {task_id}")
            else:
                logger.warning(f"未知状态: {state}")

            time.sleep(poll_interval)

        raise TimeoutError(f"视频生成超时: {task_id}")

    def download_video(self, url: str) -> bytes:
        """下载视频"""
        try:
            response = self._session.get(url, timeout=120)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"视频下载失败: {e}")
            raise


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
