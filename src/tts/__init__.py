"""TTS语音合成模块"""
from .cosyvoice_client import CosyVoiceClient, AudioData
from .edge_tts_client import EdgeTTSClient, create_tts_client, EDGE_VOICES
from .voice_manager import VoiceManager

__all__ = [
    "CosyVoiceClient",
    "EdgeTTSClient",
    "AudioData",
    "VoiceManager",
    "create_tts_client",
    "EDGE_VOICES",
]
