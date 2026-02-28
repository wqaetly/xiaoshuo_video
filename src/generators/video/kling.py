"""
可灵 AI 视频生成器适配器

将可灵 API 封装为统一的 VideoGenerator 接口。
"""
import base64
import os
from pathlib import Path
from typing import Optional, Dict, Any

from ..base import (
    VideoGenerator,
    VideoGenerateParams,
    GenerateResult,
    GenerateOptions,
    GeneratorError,
)
from ...video.kling import KlingClient
from ...utils.logger import get_logger

logger = get_logger(__name__)


class KlingVideoGenerator(VideoGenerator):
    """可灵 AI 视频生成器
    
    使用可灵 API 从图像生成视频。
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 600,
    ):
        """初始化可灵视频生成器
        
        Args:
            api_key: 可灵 API 密钥，默认从环境变量 KLING_API_KEY 读取
            timeout: 超时时间（秒）
        """
        super().__init__(provider="kling")
        
        self.api_key = api_key or os.getenv("KLING_API_KEY", "")
        if not self.api_key:
            logger.warning("可灵 API 密钥未配置")
        
        self.timeout = timeout
        
        # 初始化客户端
        self.client = KlingClient(
            api_key=self.api_key,
            timeout=timeout
        )
    
    async def _do_generate(self, params: VideoGenerateParams) -> GenerateResult:
        """执行视频生成"""
        if not self.api_key:
            raise GeneratorError(
                code="KLING_API_KEY_MISSING",
                message="可灵 API 密钥未配置"
            )
        
        # 解析选项
        options = params.options or GenerateOptions()
        duration = options.duration or 5.0
        
        logger.info(f"[Kling] 开始生成视频: duration={duration}s")
        
        try:
            # 下载图像到临时文件
            image_path = await self._download_image(params.image_url)
            
            # 调用可灵 API 生成视频
            video_data = self.client.generate(
                image_path=image_path,
                motion_prompt=params.prompt or "",
                duration=duration
            )
            
            # 清理临时文件
            image_path.unlink(missing_ok=True)
            
            logger.info(f"[Kling] 视频生成成功: {video_data.resolution}")
            
            return GenerateResult(
                success=True,
                video_url=None,
                local_path=None,
                is_async=False,
                metadata={
                    "provider": "kling",
                    "duration": video_data.duration,
                    "resolution": video_data.resolution,
                }
            )
            
        except Exception as e:
            logger.error(f"[Kling] 视频生成失败: {e}")
            raise GeneratorError(
                code="KLING_ERROR",
                message=str(e)
            )
    
    async def _download_image(self, image_url: str) -> Path:
        """下载图像到临时文件"""
        import tempfile
        import httpx
        
        if image_url.startswith("data:"):
            _, data = image_url.split(",", 1)
            image_bytes = base64.b64decode(data)
        else:
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_bytes = response.content
        
        temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        temp_file.write(image_bytes)
        temp_file.close()
        
        return Path(temp_file.name)
    
    async def poll_status(self, task_id: str) -> GenerateResult:
        """轮询任务状态"""
        try:
            status = self.client.check_status(task_id)
            
            if status["state"] == "completed":
                return GenerateResult(
                    success=True,
                    video_url=status.get("video_url"),
                    metadata={
                        "duration": status.get("duration"),
                    }
                )
            elif status["state"] == "failed":
                return GenerateResult(
                    success=False,
                    error=status.get("error", "生成失败"),
                    error_code="KLING_GENERATION_FAILED"
                )
            else:
                return GenerateResult(
                    success=True,
                    is_async=True,
                    task_id=task_id,
                    external_id=f"KLING:VIDEO:{task_id}",
                    metadata={"state": status["state"]}
                )
        except Exception as e:
            return GenerateResult(
                success=False,
                error=str(e),
                error_code="KLING_STATUS_ERROR"
            )

