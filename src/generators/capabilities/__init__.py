"""
Model Capabilities 注册表系统

借鉴 waoowaoo 的设计，统一管理不同模型的能力参数。
"""

from .types import (
    ModelType,
    ImageCapabilities,
    VideoCapabilities,
    AudioCapabilities,
    ModelCapabilities,
    CapabilityValidationResult,
)
from .registry import (
    CapabilityRegistry,
    get_capability_registry,
)
from .validator import (
    validate_image_params,
    validate_video_params,
    validate_audio_params,
)

__all__ = [
    # Types
    "ModelType",
    "ImageCapabilities",
    "VideoCapabilities",
    "AudioCapabilities",
    "ModelCapabilities",
    "CapabilityValidationResult",
    # Registry
    "CapabilityRegistry",
    "get_capability_registry",
    # Validators
    "validate_image_params",
    "validate_video_params",
    "validate_audio_params",
]

