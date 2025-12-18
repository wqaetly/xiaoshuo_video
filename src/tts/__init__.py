"""TTS语音合成模块"""
from .cosyvoice_client import CosyVoiceClient
from .voice_manager import VoiceManager

__all__ = [
    "CosyVoiceClient",
    "VoiceManager",
]
