"""即梦AI API客户端"""
import base64
import time
from pathlib import Path
from typing import Optional, Dict, Any
from .api_client import VideoAPIClient, VideoData
from ..utils.logger import get_logger
from ..utils.retry import (
    RetryConfig,
    APIError,
    APIErrorCode,
    calculate_delay,
)

logger = get_logger(__name__)


class JimengClient(VideoAPIClient):
    """即梦AI视频生成API客户端"""

    def __init__(
        self,
        api_key: str,
        use_idle_time: bool = True,
        timeout: int = 600
    ):
        super().__init__(api_key, timeout)
        self.use_idle_time = use_idle_time
        # 即梦API基础URL (示例，实际URL需根据官方文档)
        self.base_url = "https://api.jimeng.jianying.com/v1"
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def generate(
        self,
        image_path: Path,
        motion_prompt: str,
        duration: float = 5.0
    ) -> VideoData:
        """使用图片生成视频"""
        # 1. 上传图片
        image_id = self._upload_image(image_path)

        # 2. 创建生成任务
        task_id = self._create_task(
            image_id=image_id,
            prompt=motion_prompt,
            duration=duration
        )

        # 3. 等待完成
        result = self.wait_for_completion(task_id)

        # 4. 下载视频
        video_url = result.get("video_url")
        if not video_url:
            raise RuntimeError("未获取到视频URL")

        video_bytes = self.download_video(video_url)

        return VideoData(
            data=video_bytes,
            duration=result.get("duration", duration),
            resolution=result.get("resolution", "1280x720")
        )

    def _upload_image(self, image_path: Path) -> str:
        """上传图片到即梦服务器 (带重试)"""
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        payload = {
            "image": image_data,
            "filename": image_path.name
        }

        last_exception = None
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}/images/upload",
                    json=payload,
                    timeout=60
                )
                
                if response.status_code == 429:
                    raise APIError(
                        code=APIErrorCode.RATE_LIMITED,
                        message="请求过于频繁，请稍后重试",
                        retryable=True
                    )
                elif response.status_code == 401:
                    raise APIError(
                        code=APIErrorCode.AUTHENTICATION_FAILED,
                        message="API密钥无效或已过期",
                        retryable=False
                    )
                
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    raise APIError(
                        code=data.get("error_code", APIErrorCode.UNKNOWN),
                        message=data.get("error", "未知错误"),
                        details=data,
                        retryable=False
                    )
                
                image_id = data.get("image_id")
                logger.debug(f"图片上传成功: {image_id}")
                return image_id
                
            except APIError as e:
                if not e.retryable or attempt >= self.retry_config.max_retries:
                    raise
                last_exception = e
            except Exception as e:
                last_exception = e
                if attempt >= self.retry_config.max_retries:
                    break
                    
            delay = calculate_delay(
                attempt,
                self.retry_config.base_delay,
                self.retry_config.max_delay,
                self.retry_config.exponential_base,
                self.retry_config.jitter
            )
            logger.warning(f"图片上传失败: {last_exception}, 等待 {delay:.1f}s 后重试")
            time.sleep(delay)
        
        logger.error(f"图片上传失败: {last_exception}")
        raise APIError(
            code=APIErrorCode.NETWORK_ERROR,
            message=f"图片上传失败: {last_exception}",
            retryable=False
        )

    def _create_task(
        self,
        image_id: str,
        prompt: str,
        duration: float
    ) -> str:
        """创建视频生成任务 (带重试)"""
        payload = {
            "image_id": image_id,
            "prompt": prompt,
            "duration": duration,
            "model": "video-01",
            "use_idle_time": self.use_idle_time,
            "settings": {
                "motion_strength": 0.7,
                "seed": -1
            }
        }

        last_exception = None
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}/video/generate",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 429:
                    raise APIError(
                        code=APIErrorCode.RATE_LIMITED,
                        message="请求过于频繁",
                        retryable=True
                    )
                elif response.status_code == 402:
                    raise APIError(
                        code=APIErrorCode.INSUFFICIENT_QUOTA,
                        message="账户余额不足",
                        retryable=False
                    )
                    
                response.raise_for_status()
                data = response.json()
                
                if "error" in data:
                    raise APIError(
                        code=data.get("error_code", APIErrorCode.UNKNOWN),
                        message=data.get("error", "创建任务失败"),
                        details=data,
                        retryable=False
                    )
                
                task_id = data.get("task_id")
                logger.info(f"视频生成任务创建成功: {task_id}")
                return task_id
                
            except APIError as e:
                if not e.retryable or attempt >= self.retry_config.max_retries:
                    raise
                last_exception = e
            except Exception as e:
                last_exception = e
                if attempt >= self.retry_config.max_retries:
                    break
            
            delay = calculate_delay(
                attempt,
                self.retry_config.base_delay,
                self.retry_config.max_delay,
                self.retry_config.exponential_base,
                self.retry_config.jitter
            )
            logger.warning(f"创建任务失败: {last_exception}, 等待 {delay:.1f}s 后重试")
            time.sleep(delay)
        
        logger.error(f"创建生成任务失败: {last_exception}")
        raise APIError(
            code=APIErrorCode.VIDEO_GENERATION_FAILED,
            message=f"创建生成任务失败: {last_exception}",
            retryable=False
        )

    def check_status(self, task_id: str) -> dict:
        """检查任务状态"""
        try:
            response = self._session.get(
                f"{self.base_url}/video/status/{task_id}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # 标准化状态
            status = data.get("status", "unknown")
            state_map = {
                "queued": "pending",
                "running": "processing",
                "success": "completed",
                "failed": "failed"
            }

            return {
                "state": state_map.get(status, status),
                "video_url": data.get("video_url"),
                "duration": data.get("duration"),
                "resolution": data.get("resolution"),
                "error": data.get("error_message")
            }
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {"state": "unknown", "error": str(e)}

    def get_quota(self) -> Dict[str, Any]:
        """获取账户配额信息"""
        try:
            response = self._session.get(
                f"{self.base_url}/account/quota",
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"获取配额失败: {e}")
            return {}

    def generate_with_text(
        self,
        prompt: str,
        duration: float = 5.0,
        aspect_ratio: str = "16:9"
    ) -> VideoData:
        """纯文本生成视频（不使用参考图）"""
        payload = {
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "model": "video-01",
            "use_idle_time": self.use_idle_time
        }

        try:
            response = self._session.post(
                f"{self.base_url}/video/generate_text",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("task_id")

            # 等待完成
            result = self.wait_for_completion(task_id)
            video_bytes = self.download_video(result["video_url"])

            return VideoData(
                data=video_bytes,
                duration=result.get("duration", duration),
                resolution=result.get("resolution", "1280x720")
            )
        except Exception as e:
            logger.error(f"文本生成视频失败: {e}")
            raise
