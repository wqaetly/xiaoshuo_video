"""
生成器工厂

根据 provider 名称创建对应的生成器实例。
支持本地服务（ComfyUI/CosyVoice）和云端 API（即梦/可灵）的统一创建。
"""
from typing import Optional, Dict, Any

from .base import ImageGenerator, VideoGenerator, AudioGenerator, GeneratorError
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 提供商名称标准化映射
PROVIDER_ALIASES: Dict[str, str] = {
    # 图像生成
    "comfyui": "comfyui",
    "comfy": "comfyui",
    "local_image": "comfyui",
    # 视频生成
    "jimeng": "jimeng",
    "jm": "jimeng",
    "kling": "kling",
    "kl": "kling",
    "wan": "wan",
    "local_video": "wan",
    # 语音合成
    "cosyvoice": "cosyvoice",
    "cosy": "cosyvoice",
    "edge_tts": "edge_tts",
    "edge": "edge_tts",
    "local_tts": "cosyvoice",
}


def normalize_provider(provider: str) -> str:
    """标准化提供商名称"""
    key = provider.lower().strip()
    return PROVIDER_ALIASES.get(key, key)


def create_image_generator(
    provider: str = "comfyui",
    **kwargs: Any
) -> ImageGenerator:
    """创建图像生成器
    
    Args:
        provider: 提供商名称 (comfyui/fal/ark 等)
        **kwargs: 传递给生成器的额外参数
    
    Returns:
        ImageGenerator 实例
    
    Raises:
        GeneratorError: 不支持的提供商
    """
    normalized = normalize_provider(provider)
    
    if normalized == "comfyui":
        from .image import ComfyUIImageGenerator
        return ComfyUIImageGenerator(**kwargs)
    
    # 未来扩展: fal, ark 等云端服务
    # elif normalized == "fal":
    #     from .image import FalImageGenerator
    #     return FalImageGenerator(**kwargs)
    
    raise GeneratorError(
        code="PROVIDER_NOT_SUPPORTED",
        message=f"不支持的图像生成提供商: {provider}",
        details={"supported": ["comfyui"]}
    )


def create_video_generator(
    provider: str = "jimeng",
    **kwargs: Any
) -> VideoGenerator:
    """创建视频生成器
    
    Args:
        provider: 提供商名称 (jimeng/kling/wan 等)
        **kwargs: 传递给生成器的额外参数
    
    Returns:
        VideoGenerator 实例
    
    Raises:
        GeneratorError: 不支持的提供商
    """
    normalized = normalize_provider(provider)
    
    if normalized == "jimeng":
        from .video import JiMengVideoGenerator
        return JiMengVideoGenerator(**kwargs)
    
    if normalized == "kling":
        from .video import KlingVideoGenerator
        return KlingVideoGenerator(**kwargs)
    
    if normalized == "wan":
        from .video import WanVideoGenerator
        return WanVideoGenerator(**kwargs)
    
    raise GeneratorError(
        code="PROVIDER_NOT_SUPPORTED",
        message=f"不支持的视频生成提供商: {provider}",
        details={"supported": ["jimeng", "kling", "wan"]}
    )


def create_audio_generator(
    provider: str = "cosyvoice",
    **kwargs: Any
) -> AudioGenerator:
    """创建语音生成器
    
    Args:
        provider: 提供商名称 (cosyvoice/edge_tts 等)
        **kwargs: 传递给生成器的额外参数
    
    Returns:
        AudioGenerator 实例
    
    Raises:
        GeneratorError: 不支持的提供商
    """
    normalized = normalize_provider(provider)
    
    if normalized == "cosyvoice":
        from .audio import CosyVoiceAudioGenerator
        return CosyVoiceAudioGenerator(**kwargs)
    
    if normalized == "edge_tts":
        from .audio import EdgeTTSAudioGenerator
        return EdgeTTSAudioGenerator(**kwargs)
    
    raise GeneratorError(
        code="PROVIDER_NOT_SUPPORTED",
        message=f"不支持的语音生成提供商: {provider}",
        details={"supported": ["cosyvoice", "edge_tts"]}
    )

