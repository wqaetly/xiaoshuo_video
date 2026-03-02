"""
设置数据模型
"""
from typing import Optional
from pydantic import BaseModel


class LocalServicesConfig(BaseModel):
    """本地服务配置"""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    comfyui_url: str = "http://localhost:8188"
    cosyvoice_url: str = "http://localhost:9880"


class APIServicesConfig(BaseModel):
    """API 服务配置"""
    video_provider: str = "jimeng"  # jimeng, kling
    video_api_key: str = ""
    use_idle_time: bool = True


class VideoOutputConfig(BaseModel):
    """视频输出配置"""
    resolution: str = "1280x720"
    fps: int = 24


class AppSettings(BaseModel):
    """应用设置"""
    local: LocalServicesConfig = LocalServicesConfig()
    api: APIServicesConfig = APIServicesConfig()
    video: VideoOutputConfig = VideoOutputConfig()


class SettingsUpdateRequest(BaseModel):
    """设置更新请求"""
    local: Optional[LocalServicesConfig] = None
    api: Optional[APIServicesConfig] = None
    video: Optional[VideoOutputConfig] = None


class SettingsResponse(BaseModel):
    """设置响应"""
    settings: AppSettings
    message: str = "ok"

