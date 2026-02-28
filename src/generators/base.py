"""
生成器基础接口和类型定义

策略模式核心：所有生成器实现统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class GeneratorError(Exception):
    """生成器错误基类"""
    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"{code}: {message}")


class TaskStatus(str, Enum):
    """异步任务状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class GenerateOptions:
    """生成选项"""
    aspect_ratio: Optional[str] = None      # 宽高比，如 '16:9', '3:4'
    resolution: Optional[str] = None        # 分辨率，如 '1280x720', '2K', '4K'
    output_format: Optional[str] = None     # 输出格式，如 'png', 'jpg', 'mp4'
    duration: Optional[float] = None        # 视频时长（秒）
    fps: Optional[int] = None               # 帧率
    steps: Optional[int] = None             # 采样步数
    cfg_scale: Optional[float] = None       # CFG Scale
    seed: Optional[int] = None              # 随机种子
    style: Optional[str] = None             # 风格标签
    extra: Dict[str, Any] = field(default_factory=dict)  # 厂商特定参数


@dataclass
class GenerateResult:
    """生成结果"""
    success: bool
    # 同步结果
    image_url: Optional[str] = None         # 图片 URL
    image_base64: Optional[str] = None      # 图片 base64
    video_url: Optional[str] = None         # 视频 URL
    audio_url: Optional[str] = None         # 音频 URL
    local_path: Optional[str] = None        # 本地文件路径
    # 异步任务
    is_async: bool = False                  # 是否为异步任务
    task_id: Optional[str] = None           # 异步任务 ID
    external_id: Optional[str] = None       # 外部任务标识符 (如 JIMENG:VIDEO:xxx)
    # 错误信息
    error: Optional[str] = None
    error_code: Optional[str] = None
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImageGenerateParams:
    """图像生成参数"""
    prompt: str                                     # 正向提示词
    negative_prompt: Optional[str] = None           # 负向提示词
    reference_images: Optional[List[str]] = None    # 参考图片 URLs 或 base64
    character_ref: Optional[str] = None             # 角色参考图 (用于一致性)
    options: Optional[GenerateOptions] = None


@dataclass
class VideoGenerateParams:
    """视频生成参数"""
    image_url: str                                  # 起始图片 URL
    prompt: Optional[str] = None                    # 动作提示词
    last_frame_url: Optional[str] = None            # 结束帧图片 (首尾帧模式)
    options: Optional[GenerateOptions] = None


@dataclass
class AudioGenerateParams:
    """语音生成参数"""
    text: str                                       # 文本内容
    voice: Optional[str] = None                     # 音色
    speaker: Optional[str] = None                   # 说话人
    rate: Optional[float] = 1.0                     # 语速
    emotion: Optional[str] = None                   # 情感
    options: Optional[GenerateOptions] = None


class ImageGenerator(ABC):
    """图像生成器抽象基类"""
    
    def __init__(self, provider: str):
        self.provider = provider
    
    async def generate(self, params: ImageGenerateParams) -> GenerateResult:
        """生成图片（带重试）"""
        max_retries = 2
        last_error: Optional[Exception] = None
        
        for attempt in range(1, max_retries + 1):
            try:
                return await self._do_generate(params)
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.provider}] 图像生成尝试 {attempt}/{max_retries} 失败: {e}")
                if attempt == max_retries:
                    break
                import asyncio
                await asyncio.sleep(1 * attempt)
        
        return GenerateResult(
            success=False,
            error=str(last_error) if last_error else "生成失败",
            error_code="GENERATION_FAILED"
        )
    
    @abstractmethod
    async def _do_generate(self, params: ImageGenerateParams) -> GenerateResult:
        """子类实现具体生成逻辑"""
        pass


class VideoGenerator(ABC):
    """视频生成器抽象基类"""
    
    def __init__(self, provider: str):
        self.provider = provider
    
    async def generate(self, params: VideoGenerateParams) -> GenerateResult:
        """生成视频（带重试）"""
        max_retries = 2
        last_error: Optional[Exception] = None
        
        for attempt in range(1, max_retries + 1):
            try:
                return await self._do_generate(params)
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.provider}] 视频生成尝试 {attempt}/{max_retries} 失败: {e}")
                if attempt == max_retries:
                    break
                import asyncio
                await asyncio.sleep(1 * attempt)
        
        return GenerateResult(
            success=False,
            error=str(last_error) if last_error else "视频生成失败",
            error_code="VIDEO_GENERATION_FAILED"
        )
    
    @abstractmethod
    async def _do_generate(self, params: VideoGenerateParams) -> GenerateResult:
        """子类实现具体生成逻辑"""
        pass
    
    async def poll_status(self, task_id: str) -> GenerateResult:
        """轮询异步任务状态（子类可覆盖）"""
        raise NotImplementedError(f"{self.provider} 不支持异步任务轮询")


class AudioGenerator(ABC):
    """语音生成器抽象基类"""

    def __init__(self, provider: str):
        self.provider = provider

    async def generate(self, params: AudioGenerateParams) -> GenerateResult:
        """生成语音（带重试）"""
        max_retries = 2
        last_error: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                return await self._do_generate(params)
            except Exception as e:
                last_error = e
                logger.warning(f"[{self.provider}] 语音生成尝试 {attempt}/{max_retries} 失败: {e}")
                if attempt == max_retries:
                    break
                import asyncio
                await asyncio.sleep(1 * attempt)

        return GenerateResult(
            success=False,
            error=str(last_error) if last_error else "语音生成失败",
            error_code="AUDIO_GENERATION_FAILED"
        )

    @abstractmethod
    async def _do_generate(self, params: AudioGenerateParams) -> GenerateResult:
        """子类实现具体生成逻辑"""
        pass


class LLMGenerator(ABC):
    """LLM 生成器抽象基类"""

    def __init__(self, provider: str):
        self.provider = provider

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> str:
        """生成文本"""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """生成 JSON 格式输出"""
        pass

