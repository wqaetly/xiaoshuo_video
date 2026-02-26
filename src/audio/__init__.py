"""音频处理模块

提供音频特征提取、节拍检测等功能，用于：
- 歌词/音乐与视频的节拍同步
- Yvann-Nodes 音频反应效果的数据准备
- LatentSync 口型同步的音频预处理
"""
from .audio_analyzer import AudioAnalyzer, BeatInfo

__all__ = [
    "AudioAnalyzer",
    "BeatInfo",
]

