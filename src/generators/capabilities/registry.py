"""
Model Capabilities 注册表

管理所有模型的能力配置，支持从 YAML 文件加载。
"""
from pathlib import Path
from typing import Dict, Optional, List
import yaml

from .types import (
    ModelCapabilities,
    ImageCapabilities,
    VideoCapabilities,
    AudioCapabilities,
    ModelType,
)
from ...utils.logger import get_logger

logger = get_logger(__name__)

# 默认配置文件路径
DEFAULT_CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "capabilities.yaml"


class CapabilityRegistry:
    """模型能力注册表
    
    功能:
    - 从 YAML 文件加载能力配置
    - 动态注册/查询模型能力
    - 验证参数是否在支持范围内
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_PATH
        self._registry: Dict[str, ModelCapabilities] = {}
        self._load_from_config()
    
    def _load_from_config(self) -> None:
        """从配置文件加载能力定义"""
        if not self.config_path.exists():
            logger.warning(f"能力配置文件不存在: {self.config_path}")
            self._register_defaults()
            return
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            for provider_name, models in config.get("providers", {}).items():
                for model_id, model_config in models.items():
                    caps = self._parse_model_config(provider_name, model_id, model_config)
                    self._registry[caps.model_key] = caps
            
            logger.info(f"已加载 {len(self._registry)} 个模型能力配置")
        except Exception as e:
            logger.error(f"加载能力配置失败: {e}")
            self._register_defaults()
    
    def _parse_model_config(
        self,
        provider: str,
        model_id: str,
        config: dict
    ) -> ModelCapabilities:
        """解析单个模型配置"""
        image_caps = None
        video_caps = None
        audio_caps = None
        
        if "image" in config:
            img_cfg = config["image"]
            image_caps = ImageCapabilities(
                resolution_options=img_cfg.get("resolution_options", ["1024x1024"]),
                aspect_ratio_options=img_cfg.get("aspect_ratio_options", ["1:1"]),
                style_options=img_cfg.get("style_options", []),
                supports_negative_prompt=img_cfg.get("supports_negative_prompt", True),
                steps_range=tuple(img_cfg.get("steps_range", [1, 50])),
                cfg_scale_range=tuple(img_cfg.get("cfg_scale_range", [1.0, 20.0])),
                supports_seed=img_cfg.get("supports_seed", True),
                supports_img2img=img_cfg.get("supports_img2img", False),
                max_batch_size=img_cfg.get("max_batch_size", 4),
            )
        
        if "video" in config:
            vid_cfg = config["video"]
            video_caps = VideoCapabilities(
                generation_mode_options=vid_cfg.get("generation_mode_options", ["text2video"]),
                duration_options=vid_cfg.get("duration_options", [5.0]),
                fps_options=vid_cfg.get("fps_options", [24]),
                resolution_options=vid_cfg.get("resolution_options", ["1280x720"]),
                supports_first_last_frame=vid_cfg.get("supports_first_last_frame", False),
                supports_generate_audio=vid_cfg.get("supports_generate_audio", False),
                supports_camera_control=vid_cfg.get("supports_camera_control", False),
                max_wait_time=vid_cfg.get("max_wait_time", 600),
                aspect_ratio_options=vid_cfg.get("aspect_ratio_options", ["16:9"]),
            )
        
        if "audio" in config:
            aud_cfg = config["audio"]
            audio_caps = AudioCapabilities(
                voice_options=aud_cfg.get("voice_options", []),
                rate_options=aud_cfg.get("rate_options", ["-50%", "0%", "+50%"]),
                language_options=aud_cfg.get("language_options", ["zh-CN"]),
                supports_emotion=aud_cfg.get("supports_emotion", False),
                supports_ssml=aud_cfg.get("supports_ssml", False),
                format_options=aud_cfg.get("format_options", ["mp3", "wav"]),
                sample_rate_options=aud_cfg.get("sample_rate_options", [24000]),
            )
        
        return ModelCapabilities(
            provider=provider,
            model_id=model_id,
            display_name=config.get("display_name", f"{provider}/{model_id}"),
            image=image_caps,
            video=video_caps,
            audio=audio_caps,
            metadata=config.get("metadata", {}),
        )
    
    def _register_defaults(self) -> None:
        """注册默认模型配置"""
        # ComfyUI (本地图像生成)
        self.register(ModelCapabilities(
            provider="comfyui",
            model_id="z-image-turbo",
            display_name="Z-Image-Turbo (阿里通义)",
            image=ImageCapabilities(
                resolution_options=["512x512", "768x768", "1024x1024"],
                aspect_ratio_options=["1:1", "16:9", "9:16", "4:3", "3:4"],
                steps_range=(4, 8),
                supports_img2img=True,
            ),
        ))
        # 更多默认配置在 capabilities.yaml 中定义
    
    def register(self, caps: ModelCapabilities) -> None:
        """注册模型能力"""
        self._registry[caps.model_key] = caps
        logger.debug(f"已注册模型能力: {caps.model_key}")
    
    def get(self, model_key: str) -> Optional[ModelCapabilities]:
        """获取模型能力"""
        return self._registry.get(model_key)
    
    def get_by_provider(self, provider: str) -> List[ModelCapabilities]:
        """获取指定提供商的所有模型"""
        return [c for c in self._registry.values() if c.provider == provider]
    
    def list_by_type(self, model_type: ModelType) -> List[ModelCapabilities]:
        """列出支持指定类型的所有模型"""
        return [c for c in self._registry.values() if c.supports(model_type)]
    
    def list_all(self) -> List[ModelCapabilities]:
        """列出所有已注册的模型"""
        return list(self._registry.values())


# 单例
_registry: Optional[CapabilityRegistry] = None


def get_capability_registry() -> CapabilityRegistry:
    """获取能力注册表单例"""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
    return _registry

