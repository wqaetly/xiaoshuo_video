"""
系统设置 API 路由
"""
from fastapi import APIRouter

from ..models.settings import (
    AppSettings,
    SettingsUpdateRequest,
    SettingsResponse,
    LocalServicesConfig,
    APIServicesConfig,
    VideoOutputConfig,
)
from ..services.settings_service import get_settings_service

router = APIRouter()


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """获取当前设置"""
    service = get_settings_service()
    data = service.get_all_settings()
    return SettingsResponse(
        settings=AppSettings(
            local=LocalServicesConfig(**data["local"]),
            api=APIServicesConfig(**data["api"]),
            video=VideoOutputConfig(**data["video"]),
        ),
        message="ok",
    )


@router.put("", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest):
    """更新设置"""
    service = get_settings_service()
    data = service.update_settings(
        local=request.local.model_dump() if request.local else None,
        api=request.api.model_dump() if request.api else None,
        video=request.video.model_dump() if request.video else None,
    )
    return SettingsResponse(
        settings=AppSettings(
            local=LocalServicesConfig(**data["local"]),
            api=APIServicesConfig(**data["api"]),
            video=VideoOutputConfig(**data["video"]),
        ),
        message="设置已更新",
    )


@router.get("/local", response_model=LocalServicesConfig)
async def get_local_services_config():
    """获取本地服务配置"""
    service = get_settings_service()
    data = service.get_local_config()
    return LocalServicesConfig(**data)


@router.put("/local", response_model=LocalServicesConfig)
async def update_local_services_config(config: LocalServicesConfig):
    """更新本地服务配置"""
    service = get_settings_service()
    data = service.update_local_config(config.model_dump())
    return LocalServicesConfig(**data)


@router.get("/api", response_model=APIServicesConfig)
async def get_api_services_config():
    """获取API服务配置"""
    service = get_settings_service()
    data = service.get_api_config()
    return APIServicesConfig(**data)


@router.put("/api", response_model=APIServicesConfig)
async def update_api_services_config(config: APIServicesConfig):
    """更新API服务配置"""
    service = get_settings_service()
    data = service.update_api_config(config.model_dump())
    return APIServicesConfig(**data)


@router.get("/video", response_model=VideoOutputConfig)
async def get_video_output_config():
    """获取视频输出配置"""
    service = get_settings_service()
    data = service.get_video_config()
    return VideoOutputConfig(**data)


@router.put("/video", response_model=VideoOutputConfig)
async def update_video_output_config(config: VideoOutputConfig):
    """更新视频输出配置"""
    service = get_settings_service()
    data = service.update_video_config(config.model_dump())
    return VideoOutputConfig(**data)


@router.post("/reload")
async def reload_settings():
    """重新加载配置文件"""
    service = get_settings_service()
    service.reload()
    return {"message": "配置已重新加载"}

