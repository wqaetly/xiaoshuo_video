"""视频生成模块"""
from .api_client import VideoAPIClient, VideoData, create_video_client
from .jimeng import JimengClient
from .kling import KlingClient
from .wan_local import WanLocalVideoGenerator

__all__ = [
    "VideoAPIClient",
    "VideoData",
    "create_video_client",
    "JimengClient",
    "KlingClient",
    "WanLocalVideoGenerator",
]
