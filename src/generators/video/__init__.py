"""
视频生成器模块

支持的提供商:
- Wan (本地 ComfyUI)
- JiMeng (即梦 API)
- Kling (可灵 API)
"""

from .wan import WanVideoGenerator
from .jimeng import JiMengVideoGenerator
from .kling import KlingVideoGenerator

__all__ = [
    "WanVideoGenerator",
    "JiMengVideoGenerator",
    "KlingVideoGenerator",
]

