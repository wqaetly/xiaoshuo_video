"""
生成器模块 - 多 AI Provider 抽象层

借鉴 waoowaoo 项目的工厂+策略模式，实现统一的生成器接口，
支持本地模型（ComfyUI/Ollama/CosyVoice）和云端API（即梦/可灵/Fal等）的无缝切换。

Usage:
    from src.generators import create_image_generator, create_video_generator, create_audio_generator
    
    # 创建图像生成器
    generator = create_image_generator("comfyui")
    result = await generator.generate(prompt="...", options={...})
    
    # 创建视频生成器
    video_gen = create_video_generator("jimeng")
    result = await video_gen.generate(image_url="...", prompt="...")
"""

from .base import (
    GenerateResult,
    GenerateOptions,
    ImageGenerateParams,
    VideoGenerateParams,
    AudioGenerateParams,
    ImageGenerator,
    VideoGenerator,
    AudioGenerator,
    GeneratorError,
)
from .factory import (
    create_image_generator,
    create_video_generator,
    create_audio_generator,
)

__all__ = [
    # 类型
    "GenerateResult",
    "GenerateOptions",
    "ImageGenerateParams",
    "VideoGenerateParams",
    "AudioGenerateParams",
    # 抽象类
    "ImageGenerator",
    "VideoGenerator",
    "AudioGenerator",
    # 异常
    "GeneratorError",
    # 工厂函数
    "create_image_generator",
    "create_video_generator",
    "create_audio_generator",
]

