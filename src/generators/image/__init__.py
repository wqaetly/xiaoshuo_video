"""
图像生成器模块

支持的提供商:
- ComfyUI (本地)
- Fal (云端，未来扩展)
"""

from .comfyui import ComfyUIImageGenerator

__all__ = [
    "ComfyUIImageGenerator",
]

