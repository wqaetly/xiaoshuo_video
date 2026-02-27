"""
设置服务 - 读写系统配置
"""
from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from src.utils.logger import get_logger

logger = get_logger("api.settings_service")


class SettingsService:
    """设置服务"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        self.config_path = Path(config_path)
        self._settings: Optional[Dict[str, Any]] = None

    def _load_settings(self) -> Dict[str, Any]:
        """加载配置文件"""
        if self._settings is not None:
            return self._settings

        try:
            if self.config_path.exists():
                with open(self.config_path, "r", encoding="utf-8") as f:
                    self._settings = yaml.safe_load(f) or {}
            else:
                self._settings = {}
            return self._settings
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            return {}

    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """保存配置到文件"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(settings, f, allow_unicode=True, default_flow_style=False)
            self._settings = settings
            return True
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """获取所有设置"""
        settings = self._load_settings()
        return {
            "local": settings.get("local", {
                "ollama_url": "http://localhost:11434",
                "ollama_model": "glm4:9b",
                "comfyui_url": "http://localhost:8188",
                "cosyvoice_url": "http://localhost:9880",
            }),
            "api": settings.get("api", {
                "video_provider": "jimeng",
                "video_api_key": "",
                "use_idle_time": True,
            }),
            "video": settings.get("video", {
                "resolution": "1280x720",
                "fps": 24,
            }),
        }

    def get_local_config(self) -> Dict[str, Any]:
        """获取本地服务配置"""
        settings = self._load_settings()
        return settings.get("local", {
            "ollama_url": "http://localhost:11434",
            "ollama_model": "glm4:9b",
            "comfyui_url": "http://localhost:8188",
            "cosyvoice_url": "http://localhost:9880",
        })

    def update_local_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """更新本地服务配置"""
        settings = self._load_settings()
        settings["local"] = {**self.get_local_config(), **config}
        self._save_settings(settings)
        return settings["local"]

    def get_api_config(self) -> Dict[str, Any]:
        """获取API服务配置"""
        settings = self._load_settings()
        return settings.get("api", {
            "video_provider": "jimeng",
            "video_api_key": "",
            "use_idle_time": True,
        })

    def update_api_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """更新API服务配置"""
        settings = self._load_settings()
        settings["api"] = {**self.get_api_config(), **config}
        self._save_settings(settings)
        return settings["api"]

    def get_video_config(self) -> Dict[str, Any]:
        """获取视频输出配置"""
        settings = self._load_settings()
        return settings.get("video", {
            "resolution": "1280x720",
            "fps": 24,
        })

    def update_video_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """更新视频输出配置"""
        settings = self._load_settings()
        settings["video"] = {**self.get_video_config(), **config}
        self._save_settings(settings)
        return settings["video"]

    def update_settings(
        self,
        local: Optional[Dict[str, Any]] = None,
        api: Optional[Dict[str, Any]] = None,
        video: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """批量更新设置"""
        if local:
            self.update_local_config(local)
        if api:
            self.update_api_config(api)
        if video:
            self.update_video_config(video)
        return self.get_all_settings()

    def reload(self) -> None:
        """重新加载配置"""
        self._settings = None
        self._load_settings()


# 单例模式
_settings_service: Optional[SettingsService] = None


def get_settings_service() -> SettingsService:
    """获取设置服务实例"""
    global _settings_service
    if _settings_service is None:
        _settings_service = SettingsService()
    return _settings_service

