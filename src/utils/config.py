"""配置管理模块

使用 Pydantic 进行配置验证，支持从 YAML 文件和环境变量加载配置。
"""
import os
import re
from pathlib import Path
from typing import Optional, Any, Dict, Literal
import yaml
from pydantic import BaseModel, Field, field_validator, model_validator
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class LocalConfig(BaseModel):
    """本地服务配置"""
    ollama_url: str = Field(
        default="http://localhost:11434",
        description="Ollama LLM 服务地址"
    )
    ollama_model: str = Field(
        default="glm4:9b",
        description="Ollama 模型名称"
    )
    comfyui_url: str = Field(
        default="http://localhost:8188",
        description="ComfyUI 服务地址"
    )
    cosyvoice_url: str = Field(
        default="http://localhost:9880",
        description="CosyVoice TTS 服务地址"
    )
    ffmpeg_path: str = Field(
        default="ffmpeg",
        description="FFmpeg 可执行文件路径"
    )
    ffprobe_path: str = Field(
        default="ffprobe",
        description="FFprobe 可执行文件路径"
    )

    @field_validator('ollama_url', 'comfyui_url', 'cosyvoice_url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """验证 URL 格式"""
        if not re.match(r'^https?://', v):
            raise ValueError(f"无效的 URL 格式: {v}，需要以 http:// 或 https:// 开头")
        return v


class APIConfig(BaseModel):
    """API 配置"""
    video_provider: Literal["jimeng", "kling"] = Field(
        default="jimeng",
        description="视频生成提供商"
    )
    video_api_key: str = Field(
        default="",
        description="视频 API 密钥"
    )
    use_idle_time: bool = Field(
        default=True,
        description="是否使用空闲时段（可能更便宜）"
    )


class CharacterConsistencyConfig(BaseModel):
    """角色一致性配置"""
    method: str = Field(
        default="i2l",
        description="角色一致性方案: i2l / ipadapter / none"
    )


class I2LConfig(BaseModel):
    """Z-Image-i2L 配置"""
    enabled: bool = Field(default=True, description="是否启用")
    workflow: str = Field(default="z_image_i2l.json", description="工作流文件")
    lora_strength: float = Field(default=1.0, ge=0.0, le=2.0, description="LoRA 强度")
    apply_to_unet: bool = Field(default=True, description="是否应用到 UNET")


class IPAdapterConfig(BaseModel):
    """IP-Adapter 配置"""
    enabled: bool = Field(default=False, description="是否启用")
    workflow: str = Field(default="z_image_turbo_ipadapter.json", description="工作流文件")
    model: str = Field(default="ip-adapter-plus_sdxl_vit-h.safetensors", description="IP-Adapter 模型")
    clip_vision: str = Field(default="CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors", description="CLIP Vision 模型")
    weight: float = Field(default=0.8, ge=0.0, le=1.0, description="IP-Adapter 权重")
    noise: float = Field(default=0.0, ge=0.0, le=1.0, description="噪声级别")
    weight_type: str = Field(default="standard", description="权重类型")
    start_at: float = Field(default=0.0, ge=0.0, le=1.0, description="起始位置")
    end_at: float = Field(default=1.0, ge=0.0, le=1.0, description="结束位置")


class ImageConfig(BaseModel):
    """图像生成配置"""
    model: str = Field(default="z_image_turbo", description="图像模型: z_image_turbo / sdxl")
    workflow: str = Field(default="z_image_turbo_scene.json", description="ComfyUI 工作流文件")
    steps: int = Field(default=4, ge=1, le=100, description="采样步数")
    cfg: float = Field(default=1.0, ge=0.0, le=30.0, description="CFG Scale")
    sampler: str = Field(default="res_multistep", description="采样器")
    scheduler: str = Field(default="simple", description="调度器")
    character_consistency: CharacterConsistencyConfig = Field(
        default_factory=CharacterConsistencyConfig,
        description="角色一致性配置"
    )
    i2l: I2LConfig = Field(default_factory=I2LConfig, description="Z-Image-i2L 配置")
    ipadapter: IPAdapterConfig = Field(default_factory=IPAdapterConfig, description="IP-Adapter 配置")


class LocalVideoConfig(BaseModel):
    """本地视频生成配置"""
    workflow: str = Field(default="wan2_i2v.json", description="ComfyUI 工作流文件名")
    model: str = Field(default="wan2.1_i2v_480p_bf16.safetensors", description="模型文件名")
    video_length: int = Field(default=81, ge=1, description="默认帧数")
    fps: int = Field(default=16, ge=1, le=60, description="输出帧率")
    width: int = Field(default=832, ge=1, description="视频宽度")
    height: int = Field(default=480, ge=1, description="视频高度")
    steps: int = Field(default=30, ge=1, description="采样步数")
    cfg: float = Field(default=5.0, ge=0, description="CFG Scale")


class VideoConfig(BaseModel):
    """视频配置"""
    provider: str = Field(
        default="api",
        description="视频生成方式: local / api"
    )
    resolution: str = Field(
        default="1280x720",
        pattern=r"^\d+x\d+$",
        description="视频分辨率 (格式: 宽x高)"
    )
    fps: int = Field(
        default=24,
        ge=15,
        le=60,
        description="视频帧率 (15-60)"
    )
    style: str = Field(
        default="anime",
        description="视觉风格"
    )
    local: Optional[LocalVideoConfig] = Field(
        default_factory=LocalVideoConfig,
        description="本地视频生成配置"
    )


class GenerationConfig(BaseModel):
    """生成配置"""
    scene_duration_min: float = Field(
        default=3.0,
        ge=1.0,
        le=10.0,
        description="场景最小时长（秒）"
    )
    scene_duration_max: float = Field(
        default=6.0,
        ge=2.0,
        le=15.0,
        description="场景最大时长（秒）"
    )
    max_concurrent_tasks: int = Field(
        default=3,
        ge=1,
        le=10,
        description="最大并发任务数"
    )
    retry_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="重试次数"
    )
    retry_delay: int = Field(
        default=5,
        ge=1,
        le=60,
        description="重试延迟（秒）"
    )
    enable_parallel: bool = Field(
        default=True,
        description="是否启用并行执行（图像和音频同时生成）"
    )
    base_seed: Optional[int] = Field(
        default=None,
        description="基础随机种子 (null=自动生成, 固定值可复现结果)"
    )
    use_agent_storyboard: bool = Field(
        default=False,
        description="是否使用 Agent 架构生成分镜（实验性功能）"
    )
    agent_max_iterations: int = Field(
        default=100,
        ge=10,
        le=500,
        description="Agent 最大迭代次数"
    )
    use_generator_bridge: bool = Field(
        default=False,
        description="是否使用 GeneratorBridge 统一生成器管理（推荐用于新项目）"
    )

    @model_validator(mode='after')
    def validate_duration_range(self) -> 'GenerationConfig':
        """验证时长范围"""
        if self.scene_duration_min >= self.scene_duration_max:
            raise ValueError(
                f"scene_duration_min ({self.scene_duration_min}) "
                f"必须小于 scene_duration_max ({self.scene_duration_max})"
            )
        return self


class PathsConfig(BaseModel):
    """路径配置"""
    projects_dir: str = Field(
        default="data/projects",
        description="项目目录"
    )
    models_dir: str = Field(
        default="models",
        description="模型目录"
    )
    temp_dir: str = Field(
        default="temp",
        description="临时文件目录"
    )


class LogModulesConfig(BaseModel):
    """日志模块文件名配置"""
    api: str = Field(default="api.log", description="WebUI API 后端日志")
    llm: str = Field(default="llm.log", description="LLM/Ollama 调用日志")
    comfyui: str = Field(default="comfyui.log", description="ComfyUI 图像生成日志")
    tts: str = Field(default="tts.log", description="TTS 语音合成日志")
    video: str = Field(default="video.log", description="视频生成日志")
    pipeline: str = Field(default="pipeline.log", description="流程控制日志")
    all: str = Field(default="app.log", description="全局日志 (所有模块)")


class LogConfig(BaseModel):
    """日志配置"""
    enabled: bool = Field(
        default=True,
        description="是否启用文件日志"
    )
    log_dir: str = Field(
        default="log",
        description="日志目录"
    )
    level: str = Field(
        default="DEBUG",
        description="日志级别: DEBUG / INFO / WARNING / ERROR"
    )
    rotation: str = Field(
        default="50 MB",
        description="日志文件轮转大小"
    )
    retention: str = Field(
        default="30 days",
        description="日志保留时间"
    )
    separate_modules: bool = Field(
        default=True,
        description="是否按模块分别记录日志"
    )
    modules: LogModulesConfig = Field(
        default_factory=LogModulesConfig,
        description="模块日志文件名"
    )

    @field_validator('level')
    @classmethod
    def validate_level(cls, v: str) -> str:
        """验证日志级别"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f"无效的日志级别: {v}，可选值: {valid_levels}")
        return v.upper()


class Config(BaseModel):
    """全局配置

    支持从 YAML 文件和环境变量加载配置，并进行严格验证。
    """
    local: LocalConfig = Field(default_factory=LocalConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    video: VideoConfig = Field(default_factory=VideoConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    logging: LogConfig = Field(default_factory=LogConfig)

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """加载配置文件

        Args:
            config_path: 配置文件路径，默认为 config/settings.yaml

        Returns:
            Config 实例

        Raises:
            ValueError: 配置验证失败时抛出
        """
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # 从环境变量覆盖配置
        cls._apply_env_overrides(data)

        try:
            config = cls(**data)
            return config
        except Exception as e:
            raise ValueError(f"配置验证失败: {e}")

    @staticmethod
    def _apply_env_overrides(data: Dict[str, Any]) -> None:
        """从环境变量覆盖配置"""
        # API 配置
        if "api" not in data:
            data["api"] = {}

        # 优先使用特定提供商的密钥
        jimeng_key = os.getenv("JIMENG_API_KEY", "")
        kling_key = os.getenv("KLING_API_KEY", "")

        # 根据配置的提供商选择对应密钥
        provider = data.get("api", {}).get("video_provider", "jimeng")
        if provider == "jimeng" and jimeng_key:
            data["api"]["video_api_key"] = jimeng_key
        elif provider == "kling" and kling_key:
            data["api"]["video_api_key"] = kling_key
        else:
            # 回退：使用任一可用的密钥
            data["api"]["video_api_key"] = jimeng_key or kling_key

        # 本地服务配置
        if "local" not in data:
            data["local"] = {}

        if os.getenv("OLLAMA_URL"):
            data["local"]["ollama_url"] = os.getenv("OLLAMA_URL")
        if os.getenv("COMFYUI_URL"):
            data["local"]["comfyui_url"] = os.getenv("COMFYUI_URL")
        if os.getenv("COSYVOICE_URL"):
            data["local"]["cosyvoice_url"] = os.getenv("COSYVOICE_URL")

    def get_project_path(self, project_name: str) -> Path:
        """获取项目路径"""
        return Path(self.paths.projects_dir) / project_name

    def validate(self) -> list[str]:
        """验证配置完整性，返回警告列表

        此方法不会抛出异常，仅返回潜在问题的警告列表。
        用于在启动时检查配置是否合理。

        Returns:
            警告消息列表
        """
        warnings = []

        # 检查 API 密钥
        if not self.api.video_api_key:
            warnings.append(
                "视频 API 密钥未配置，视频生成功能将不可用。"
                "请设置环境变量 JIMENG_API_KEY 或 KLING_API_KEY"
            )

        # 检查路径是否可写
        projects_path = Path(self.paths.projects_dir)
        if projects_path.exists() and not os.access(projects_path, os.W_OK):
            warnings.append(f"项目目录 {projects_path} 不可写")

        # 检查分辨率格式
        try:
            w, h = map(int, self.video.resolution.split('x'))
            if w < 640 or h < 480:
                warnings.append(f"视频分辨率 {self.video.resolution} 可能过低")
            if w > 3840 or h > 2160:
                warnings.append(f"视频分辨率 {self.video.resolution} 可能过高，会增加生成时间")
        except ValueError:
            warnings.append(f"视频分辨率格式无效: {self.video.resolution}")

        return warnings

    def print_summary(self) -> None:
        """打印配置摘要"""
        print("=" * 50)
        print("配置摘要")
        print("=" * 50)
        print(f"  LLM: {self.local.ollama_url} ({self.local.ollama_model})")
        print(f"  ComfyUI: {self.local.comfyui_url}")
        print(f"  CosyVoice: {self.local.cosyvoice_url}")
        print(f"  视频提供商: {self.api.video_provider}")
        print(f"  视频 API 密钥: {'已配置' if self.api.video_api_key else '未配置'}")
        print(f"  并行执行: {'启用' if self.generation.enable_parallel else '禁用'}")
        print(f"  最大并发: {self.generation.max_concurrent_tasks}")
        print("=" * 50)


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置"""
    global _config
    if _config is None:
        _config = Config.load()
    return _config


def reload_config(config_path: Optional[Path] = None) -> Config:
    """重新加载配置"""
    global _config
    _config = Config.load(config_path)
    return _config


def validate_config_on_startup() -> None:
    """启动时验证配置，打印警告

    建议在应用启动时调用此函数。
    """
    config = get_config()
    warnings = config.validate()

    if warnings:
        print("\n⚠️ 配置警告:")
        for w in warnings:
            print(f"  - {w}")
        print()
