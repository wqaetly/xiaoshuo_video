"""
ComfyUI 图像生成器适配器

将 ComfyUI 客户端封装为统一的 ImageGenerator 接口。
"""
import base64
import io
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from PIL import Image

from ..base import (
    ImageGenerator,
    ImageGenerateParams,
    GenerateResult,
    GenerateOptions,
    GeneratorError,
)
from ...image.comfyui_client import ComfyUIClient
from ...utils.logger import get_logger
from ...utils.config import get_config

logger = get_logger(__name__)


class ComfyUIImageGenerator(ImageGenerator):
    """ComfyUI 图像生成器
    
    使用本地 ComfyUI 服务生成图像，支持多种工作流模板。
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 300,
        workflow_template: Optional[Dict[str, Any]] = None,
    ):
        """初始化 ComfyUI 图像生成器
        
        Args:
            base_url: ComfyUI 服务地址，默认从配置读取
            timeout: 超时时间（秒）
            workflow_template: 自定义工作流模板，默认使用 Z-Image-Turbo
        """
        super().__init__(provider="comfyui")
        
        # 从配置读取默认值
        config = get_config()
        self.base_url = base_url or config.local.comfyui_url
        self.timeout = timeout
        
        # 初始化 ComfyUI 客户端
        self.client = ComfyUIClient(
            base_url=self.base_url,
            timeout=self.timeout
        )
        
        # 工作流模板（默认使用 Z-Image-Turbo）
        self.workflow_template = workflow_template or self._default_workflow()
    
    def _default_workflow(self) -> Dict[str, Any]:
        """Z-Image-Turbo 默认工作流"""
        return {
            "28": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": "z_image_turbo_bf16.safetensors",
                    "weight_dtype": "default"
                }
            },
            "29": {
                "class_type": "VAELoader",
                "inputs": {"vae_name": "ae.safetensors"}
            },
            "30": {
                "class_type": "CLIPLoader",
                "inputs": {
                    "clip_name": "qwen_3_4b.safetensors",
                    "type": "lumina2",
                    "device": "default"
                }
            },
            "11": {
                "class_type": "ModelSamplingAuraFlow",
                "inputs": {"model": ["28", 0], "shift": 3}
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {"clip": ["30", 0], "text": ""}
            },
            "33": {
                "class_type": "ConditioningZeroOut",
                "inputs": {"conditioning": ["6", 0]}
            },
            "5": {
                "class_type": "EmptySD3LatentImage",
                "inputs": {"width": 1280, "height": 720, "batch_size": 1}
            },
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "model": ["11", 0],
                    "positive": ["6", 0],
                    "negative": ["33", 0],
                    "latent_image": ["5", 0],
                    "seed": 0,
                    "control_after_generate": "randomize",
                    "steps": 4,
                    "cfg": 1,
                    "sampler_name": "res_multistep",
                    "scheduler": "simple",
                    "denoise": 1
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {"samples": ["3", 0], "vae": ["29", 0]}
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {"images": ["8", 0], "filename_prefix": "gen"}
            }
        }
    
    def check_health(self) -> bool:
        """检查 ComfyUI 服务是否可用"""
        return self.client.check_health()
    
    async def _do_generate(self, params: ImageGenerateParams) -> GenerateResult:
        """执行图像生成"""
        import copy
        import random
        
        # 检查服务可用性
        if not self.check_health():
            raise GeneratorError(
                code="COMFYUI_UNAVAILABLE",
                message=f"ComfyUI 服务不可用: {self.base_url}"
            )
        
        # 解析选项
        options = params.options or GenerateOptions()
        width, height = self._parse_resolution(options)
        seed = options.seed if options.seed is not None else random.randint(0, 2**32 - 1)
        steps = options.steps or 4  # Z-Image-Turbo 默认 4 步
        
        # 构建工作流
        workflow = copy.deepcopy(self.workflow_template)
        
        # 设置提示词
        if "6" in workflow:
            workflow["6"]["inputs"]["text"] = params.prompt
        
        # 设置尺寸
        if "5" in workflow:
            workflow["5"]["inputs"]["width"] = width
            workflow["5"]["inputs"]["height"] = height
        
        # 设置采样参数
        if "3" in workflow:
            workflow["3"]["inputs"]["seed"] = seed
            workflow["3"]["inputs"]["steps"] = steps

        # 设置输出文件名
        filename_prefix = f"gen_{uuid.uuid4().hex[:8]}"
        if "9" in workflow:
            workflow["9"]["inputs"]["filename_prefix"] = filename_prefix

        logger.info(f"[ComfyUI] 开始生成图像: {width}x{height}, steps={steps}")
        logger.debug(f"[ComfyUI] Prompt: {params.prompt[:100]}...")

        try:
            # 执行工作流
            images = self.client.execute_workflow(workflow, timeout=self.timeout)

            if not images:
                return GenerateResult(
                    success=False,
                    error="ComfyUI 未返回图像",
                    error_code="NO_IMAGE_RETURNED"
                )

            # 转换为 base64
            image = images[0]
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            logger.info(f"[ComfyUI] 图像生成成功: {image.size}")

            return GenerateResult(
                success=True,
                image_base64=image_base64,
                metadata={
                    "provider": "comfyui",
                    "width": image.width,
                    "height": image.height,
                    "seed": seed,
                    "steps": steps,
                }
            )

        except TimeoutError as e:
            logger.error(f"[ComfyUI] 生成超时: {e}")
            raise GeneratorError(
                code="COMFYUI_TIMEOUT",
                message=f"图像生成超时: {self.timeout}s"
            )
        except Exception as e:
            logger.error(f"[ComfyUI] 生成失败: {e}")
            raise GeneratorError(
                code="COMFYUI_ERROR",
                message=str(e)
            )

    def _parse_resolution(self, options: GenerateOptions) -> tuple[int, int]:
        """解析分辨率选项

        Returns:
            (width, height) 元组
        """
        # 优先使用 resolution
        if options.resolution:
            if "x" in options.resolution:
                parts = options.resolution.lower().split("x")
                return int(parts[0]), int(parts[1])
            elif options.resolution.upper() == "2K":
                return 1920, 1080
            elif options.resolution.upper() == "4K":
                return 3840, 2160

        # 根据宽高比计算
        if options.aspect_ratio:
            base_width = 1280
            ratio_map = {
                "16:9": (16, 9),
                "9:16": (9, 16),
                "4:3": (4, 3),
                "3:4": (3, 4),
                "1:1": (1, 1),
                "3:2": (3, 2),
                "2:3": (2, 3),
            }
            if options.aspect_ratio in ratio_map:
                w_ratio, h_ratio = ratio_map[options.aspect_ratio]
                height = int(base_width * h_ratio / w_ratio)
                # 确保尺寸是 8 的倍数
                height = (height // 8) * 8
                return base_width, height

        # 默认 16:9
        return 1280, 720

