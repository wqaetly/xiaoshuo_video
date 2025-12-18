"""配置管理模块"""
import os
from pathlib import Path
from typing import Optional, Any, Dict
import yaml
from pydantic import BaseModel
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class LocalConfig(BaseModel):
    """本地服务配置"""
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:14b"
    comfyui_url: str = "http://localhost:8188"
    cosyvoice_url: str = "http://localhost:9880"


class APIConfig(BaseModel):
    """API配置"""
    video_provider: str = "jimeng"
    video_api_key: str = ""
    use_idle_time: bool = True


class VideoConfig(BaseModel):
    """视频配置"""
    resolution: str = "1280x720"
    fps: int = 24
    style: str = "anime"


class GenerationConfig(BaseModel):
    """生成配置"""
    scene_duration_min: float = 3.0
    scene_duration_max: float = 6.0
    max_concurrent_tasks: int = 3
    retry_count: int = 3
    retry_delay: int = 5


class PathsConfig(BaseModel):
    """路径配置"""
    projects_dir: str = "data/projects"
    models_dir: str = "models"
    temp_dir: str = "temp"


class Config(BaseModel):
    """全局配置"""
    local: LocalConfig = LocalConfig()
    api: APIConfig = APIConfig()
    video: VideoConfig = VideoConfig()
    generation: GenerationConfig = GenerationConfig()
    paths: PathsConfig = PathsConfig()

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Config":
        """加载配置文件"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        # 从环境变量覆盖API密钥
        if "api" not in data:
            data["api"] = {}
        data["api"]["video_api_key"] = os.getenv("JIMENG_API_KEY", "") or os.getenv("KLING_API_KEY", "")

        return cls(**data)

    def get_project_path(self, project_name: str) -> Path:
        """获取项目路径"""
        return Path(self.paths.projects_dir) / project_name


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
