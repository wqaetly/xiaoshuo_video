"""
参数验证器

在生成前验证参数是否在模型支持范围内。
"""
from typing import Dict, Any, Optional, List

from .types import (
    ModelCapabilities,
    ImageCapabilities,
    VideoCapabilities,
    AudioCapabilities,
    CapabilityValidationResult,
)
from .registry import get_capability_registry
from ...utils.logger import get_logger

logger = get_logger(__name__)


def validate_image_params(
    model_key: str,
    params: Dict[str, Any],
    auto_adjust: bool = True,
) -> CapabilityValidationResult:
    """验证图像生成参数
    
    Args:
        model_key: 模型键 (provider/model_id)
        params: 生成参数
        auto_adjust: 是否自动调整不支持的参数
        
    Returns:
        验证结果
    """
    registry = get_capability_registry()
    caps = registry.get(model_key)
    
    if caps is None or caps.image is None:
        return CapabilityValidationResult(
            is_valid=False,
            errors=[f"未找到图像模型: {model_key}"],
        )
    
    img_caps = caps.image
    errors: List[str] = []
    warnings: List[str] = []
    adjusted: Dict[str, Any] = {}
    
    # 验证分辨率
    if "resolution" in params:
        if params["resolution"] not in img_caps.resolution_options:
            if auto_adjust:
                adjusted["resolution"] = img_caps.resolution_options[0]
                warnings.append(f"分辨率 {params['resolution']} 不支持，已调整为 {adjusted['resolution']}")
            else:
                errors.append(f"不支持的分辨率: {params['resolution']}")
    
    # 验证宽高比
    if "aspect_ratio" in params:
        if params["aspect_ratio"] not in img_caps.aspect_ratio_options:
            if auto_adjust:
                adjusted["aspect_ratio"] = img_caps.aspect_ratio_options[0]
                warnings.append(f"宽高比 {params['aspect_ratio']} 不支持，已调整为 {adjusted['aspect_ratio']}")
            else:
                errors.append(f"不支持的宽高比: {params['aspect_ratio']}")
    
    # 验证步数
    if "steps" in params:
        min_steps, max_steps = img_caps.steps_range
        if not (min_steps <= params["steps"] <= max_steps):
            if auto_adjust:
                adjusted["steps"] = max(min_steps, min(max_steps, params["steps"]))
                warnings.append(f"步数 {params['steps']} 超出范围，已调整为 {adjusted['steps']}")
            else:
                errors.append(f"步数超出范围 [{min_steps}, {max_steps}]")
    
    # 验证 CFG Scale
    if "cfg_scale" in params:
        min_cfg, max_cfg = img_caps.cfg_scale_range
        if not (min_cfg <= params["cfg_scale"] <= max_cfg):
            if auto_adjust:
                adjusted["cfg_scale"] = max(min_cfg, min(max_cfg, params["cfg_scale"]))
                warnings.append(f"CFG Scale {params['cfg_scale']} 超出范围，已调整为 {adjusted['cfg_scale']}")
            else:
                errors.append(f"CFG Scale 超出范围 [{min_cfg}, {max_cfg}]")
    
    # 验证负面提示词支持
    if "negative_prompt" in params and not img_caps.supports_negative_prompt:
        warnings.append("该模型不支持负面提示词，将被忽略")
        adjusted["negative_prompt"] = None
    
    return CapabilityValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        adjusted_params=adjusted,
    )


def validate_video_params(
    model_key: str,
    params: Dict[str, Any],
    auto_adjust: bool = True,
) -> CapabilityValidationResult:
    """验证视频生成参数"""
    registry = get_capability_registry()
    caps = registry.get(model_key)
    
    if caps is None or caps.video is None:
        return CapabilityValidationResult(
            is_valid=False,
            errors=[f"未找到视频模型: {model_key}"],
        )
    
    vid_caps = caps.video
    errors: List[str] = []
    warnings: List[str] = []
    adjusted: Dict[str, Any] = {}
    
    # 验证时长
    if "duration" in params:
        if params["duration"] not in vid_caps.duration_options:
            if auto_adjust:
                # 选择最接近的时长
                closest = min(vid_caps.duration_options, key=lambda x: abs(x - params["duration"]))
                adjusted["duration"] = closest
                warnings.append(f"时长 {params['duration']}s 不支持，已调整为 {closest}s")
            else:
                errors.append(f"不支持的时长: {params['duration']}s")
    
    # 验证 FPS
    if "fps" in params:
        if params["fps"] not in vid_caps.fps_options:
            if auto_adjust:
                adjusted["fps"] = vid_caps.fps_options[0]
                warnings.append(f"FPS {params['fps']} 不支持，已调整为 {adjusted['fps']}")
            else:
                errors.append(f"不支持的 FPS: {params['fps']}")
    
    # 验证首尾帧功能
    if params.get("first_frame") or params.get("last_frame"):
        if not vid_caps.supports_first_last_frame:
            errors.append("该模型不支持首尾帧控制")
    
    return CapabilityValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        adjusted_params=adjusted,
    )


def validate_audio_params(
    model_key: str,
    params: Dict[str, Any],
    auto_adjust: bool = True,
) -> CapabilityValidationResult:
    """验证音频生成参数"""
    registry = get_capability_registry()
    caps = registry.get(model_key)
    
    if caps is None or caps.audio is None:
        return CapabilityValidationResult(
            is_valid=False,
            errors=[f"未找到音频模型: {model_key}"],
        )
    
    aud_caps = caps.audio
    errors: List[str] = []
    warnings: List[str] = []
    adjusted: Dict[str, Any] = {}
    
    # 验证声音选项
    if "voice" in params and aud_caps.voice_options:
        if params["voice"] not in aud_caps.voice_options:
            if auto_adjust:
                adjusted["voice"] = aud_caps.voice_options[0]
                warnings.append(f"声音 {params['voice']} 不支持，已调整为 {adjusted['voice']}")
            else:
                errors.append(f"不支持的声音: {params['voice']}")
    
    return CapabilityValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        adjusted_params=adjusted,
    )

