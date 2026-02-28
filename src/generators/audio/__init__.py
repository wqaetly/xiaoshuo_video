"""
语音生成器模块

支持的提供商:
- CosyVoice (本地)
- Edge TTS (云端免费)
"""

from .cosyvoice import CosyVoiceAudioGenerator
from .edge_tts import EdgeTTSAudioGenerator

__all__ = [
    "CosyVoiceAudioGenerator",
    "EdgeTTSAudioGenerator",
]

