"""
Model Capabilities 类型定义

定义不同生成器类型的能力参数结构。
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum


class ModelType(str, Enum):
    """模型类型"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    LLM = "llm"


@dataclass
class ImageCapabilities:
    """图像生成能力参数
    
    定义图像生成模型支持的参数范围。
    """
    # 支持的分辨率选项
    resolution_options: List[str] = field(default_factory=lambda: ["1024x1024"])
    # 支持的宽高比
    aspect_ratio_options: List[str] = field(default_factory=lambda: ["1:1", "16:9", "9:16"])
    # 支持的风格
    style_options: List[str] = field(default_factory=list)
    # 是否支持负面提示词
    supports_negative_prompt: bool = True
    # 支持的步数范围
    steps_range: tuple[int, int] = (1, 50)
    # 支持的 CFG Scale 范围
    cfg_scale_range: tuple[float, float] = (1.0, 20.0)
    # 是否支持种子控制
    supports_seed: bool = True
    # 是否支持图生图
    supports_img2img: bool = False
    # 最大批量生成数
    max_batch_size: int = 4


@dataclass
class VideoCapabilities:
    """视频生成能力参数
    
    定义视频生成模型支持的参数范围。
    """
    # 生成模式选项
    generation_mode_options: List[str] = field(default_factory=lambda: ["text2video"])
    # 支持的时长选项（秒）
    duration_options: List[float] = field(default_factory=lambda: [5.0])
    # 支持的 FPS 选项
    fps_options: List[int] = field(default_factory=lambda: [24])
    # 支持的分辨率选项
    resolution_options: List[str] = field(default_factory=lambda: ["1280x720"])
    # 是否支持首尾帧控制
    supports_first_last_frame: bool = False
    # 是否支持生成音频
    supports_generate_audio: bool = False
    # 是否支持运镜控制
    supports_camera_control: bool = False
    # 最大等待时间（秒）
    max_wait_time: int = 600
    # 支持的宽高比
    aspect_ratio_options: List[str] = field(default_factory=lambda: ["16:9"])


@dataclass
class AudioCapabilities:
    """音频生成能力参数
    
    定义 TTS 模型支持的参数范围。
    """
    # 支持的声音/音色选项
    voice_options: List[str] = field(default_factory=list)
    # 支持的语速选项
    rate_options: List[str] = field(default_factory=lambda: ["-50%", "0%", "+50%"])
    # 支持的语言
    language_options: List[str] = field(default_factory=lambda: ["zh-CN", "en-US"])
    # 是否支持情感控制
    supports_emotion: bool = False
    # 是否支持 SSML
    supports_ssml: bool = False
    # 支持的音频格式
    format_options: List[str] = field(default_factory=lambda: ["mp3", "wav"])
    # 支持的采样率
    sample_rate_options: List[int] = field(default_factory=lambda: [24000, 48000])


@dataclass
class ModelCapabilities:
    """模型能力集合
    
    一个模型可能同时具备多种能力（如 ComfyUI 可以做图像也可以做视频）。
    """
    # 提供商名称
    provider: str
    # 模型ID
    model_id: str
    # 模型显示名称
    display_name: str
    # 图像能力
    image: Optional[ImageCapabilities] = None
    # 视频能力
    video: Optional[VideoCapabilities] = None
    # 音频能力
    audio: Optional[AudioCapabilities] = None
    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def model_key(self) -> str:
        """生成唯一模型键"""
        return f"{self.provider}/{self.model_id}"
    
    def supports(self, model_type: ModelType) -> bool:
        """检查是否支持指定类型"""
        if model_type == ModelType.IMAGE:
            return self.image is not None
        elif model_type == ModelType.VIDEO:
            return self.video is not None
        elif model_type == ModelType.AUDIO:
            return self.audio is not None
        return False


@dataclass
class CapabilityValidationResult:
    """能力验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    adjusted_params: Dict[str, Any] = field(default_factory=dict)

