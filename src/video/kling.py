"""可灵AI API客户端"""
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


class KlingClient(VideoAPIClient):
    """可灵AI视频生成API客户端"""

    def __init__(
        self,
        api_key: str,
        timeout: int = 600
    ):
        super().__init__(api_key, timeout)
        # 可灵API基础URL (示例，实际URL需根据官方文档)
        self.base_url = "https://api.klingai.com/v1"
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
        """使用图片生成视频 (带重试)"""
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()

        payload = {
            "image": image_data,
            "prompt": motion_prompt,
            "duration": int(duration),
            "model_version": "kling-v1",
            "cfg_scale": 0.5,
            "mode": "std"
        }

        last_exception = None
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                response = self._session.post(
                    f"{self.base_url}/images/generations",
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
                elif response.status_code == 401:
                    raise APIError(
                        code=APIErrorCode.AUTHENTICATION_FAILED,
                        message="API密钥无效",
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
                
                task_id = data.get("task_id") or data.get("id")
                logger.info(f"可灵视频生成任务创建: {task_id}")

                result = self.wait_for_completion(task_id)

                video_url = result.get("video_url")
                if not video_url:
                    raise APIError(
                        code=APIErrorCode.VIDEO_GENERATION_FAILED,
                        message="未获取到视频URL",
                        details=result,
                        retryable=False
                    )

                video_bytes = self.download_video(video_url)

                return VideoData(
                    data=video_bytes,
                    duration=result.get("duration", duration),
                    resolution=result.get("resolution", "1280x720")
                )
                
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
            logger.warning(f"可灵视频生成失败: {last_exception}, 等待 {delay:.1f}s 后重试")
            time.sleep(delay)
        
        logger.error(f"可灵视频生成失败: {last_exception}")
        raise APIError(
            code=APIErrorCode.VIDEO_GENERATION_FAILED,
            message=f"视频生成失败: {last_exception}",
            retryable=False
        )

    def check_status(self, task_id: str) -> dict:
        """检查任务状态"""
        try:
            response = self._session.get(
                f"{self.base_url}/tasks/{task_id}",
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # 标准化状态
            status = data.get("status", "unknown")
            state_map = {
                "submitted": "pending",
                "processing": "processing",
                "succeed": "completed",
                "failed": "failed"
            }

            result = {
                "state": state_map.get(status, status),
                "error": data.get("error_msg")
            }

            # 获取视频信息
            if "works" in data and data["works"]:
                work = data["works"][0]
                result["video_url"] = work.get("resource", {}).get("resource")
                result["duration"] = work.get("duration")

            return result
        except Exception as e:
            logger.error(f"获取任务状态失败: {e}")
            return {"state": "unknown", "error": str(e)}

    def extend_video(
        self,
        video_path: Path,
        prompt: str,
        extend_duration: float = 5.0
    ) -> VideoData:
        """延长视频"""
        with open(video_path, "rb") as f:
            video_data = base64.b64encode(f.read()).decode()

        payload = {
            "video": video_data,
            "prompt": prompt,
            "extend_duration": int(extend_duration)
        }

        try:
            response = self._session.post(
                f"{self.base_url}/videos/extend",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            task_id = data.get("task_id")

            result = self.wait_for_completion(task_id)
            video_bytes = self.download_video(result["video_url"])

            return VideoData(
                data=video_bytes,
                duration=result.get("duration", extend_duration),
                resolution=result.get("resolution", "1280x720")
            )
        except Exception as e:
            logger.error(f"视频延长失败: {e}")
            raise
