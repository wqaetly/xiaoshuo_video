"""
Wan 本地视频生成器适配器

使用 ComfyUI + Wan 2.2 模型进行本地视频生成。
"""
import base64
import io
from pathlib import Path
from typing import Optional, Dict, Any

from ..base import (
    VideoGenerator,
    VideoGenerateParams,
    GenerateResult,
    GenerateOptions,
    GeneratorError,
)
from ...image.comfyui_client import ComfyUIClient
from ...video.wan_local import WanLocalVideoGenerator
from ...utils.logger import get_logger
from ...utils.config import get_config

logger = get_logger(__name__)


class WanVideoGenerator(VideoGenerator):
    """Wan 本地视频生成器
    
    使用 ComfyUI + Wan 2.2 模型从图像生成视频。
    适合本地 GPU 推理，支持 GGUF 量化。
    """
    
    def __init__(
        self,
        comfyui_url: Optional[str] = None,
        workflow_path: Optional[Path] = None,
        timeout: int = 600,
        default_fps: int = 16,
        default_frames: int = 81,
    ):
        """初始化 Wan 视频生成器
        
        Args:
            comfyui_url: ComfyUI 服务地址
            workflow_path: I2V 工作流文件路径
            timeout: 超时时间（秒）
            default_fps: 默认帧率
            default_frames: 默认帧数
        """
        super().__init__(provider="wan")
        
        # 从配置读取默认值
        config = get_config()
        self.comfyui_url = comfyui_url or config.local.comfyui_url
        self.timeout = timeout
        self.default_fps = default_fps
        self.default_frames = default_frames
        
        # 初始化 ComfyUI 客户端
        self.client = ComfyUIClient(
            base_url=self.comfyui_url,
            timeout=timeout
        )
        
        # 初始化 Wan 生成器
        self.wan_generator = WanLocalVideoGenerator(
            comfyui_client=self.client,
            workflow_path=workflow_path,
            default_video_length=default_frames,
            default_fps=default_fps
        )
    
    async def _do_generate(self, params: VideoGenerateParams) -> GenerateResult:
        """执行视频生成"""
        import tempfile
        import httpx
        
        # 检查服务可用性
        if not self.client.check_health():
            raise GeneratorError(
                code="COMFYUI_UNAVAILABLE",
                message=f"ComfyUI 服务不可用: {self.comfyui_url}"
            )
        
        # 解析选项
        options = params.options or GenerateOptions()
        width, height = self._parse_resolution(options)
        frames = self._calculate_frames(options)
        
        logger.info(f"[Wan] 开始生成视频: {width}x{height}, frames={frames}")
        
        try:
            # 下载图像到临时文件
            image_path = await self._download_image(params.image_url)
            
            # 生成视频
            output_path = self.wan_generator.generate_video(
                image_path=image_path,
                motion_prompt=params.prompt or "",
                width=width,
                height=height,
                video_length=frames,
            )
            
            # 清理临时图像
            image_path.unlink(missing_ok=True)
            
            if output_path:
                logger.info(f"[Wan] 视频生成成功: {output_path}")
                return GenerateResult(
                    success=True,
                    local_path=str(output_path),
                    metadata={
                        "provider": "wan",
                        "width": width,
                        "height": height,
                        "frames": frames,
                        "fps": self.default_fps,
                    }
                )
            else:
                return GenerateResult(
                    success=False,
                    error="Wan 视频生成失败",
                    error_code="WAN_GENERATION_FAILED"
                )
                
        except Exception as e:
            logger.error(f"[Wan] 视频生成失败: {e}")
            raise GeneratorError(
                code="WAN_ERROR",
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
    
    def _parse_resolution(self, options: GenerateOptions) -> tuple[int, int]:
        """解析分辨率"""
        if options.resolution:
            if "x" in options.resolution:
                parts = options.resolution.lower().split("x")
                return int(parts[0]), int(parts[1])
        # Wan 2.2 推荐分辨率
        return 832, 480
    
    def _calculate_frames(self, options: GenerateOptions) -> int:
        """计算帧数"""
        if options.duration:
            return int(options.duration * self.default_fps) + 1
        return self.default_frames

