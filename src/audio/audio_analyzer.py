"""音频分析器 - 提取音频特征用于视频同步"""
import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BeatInfo:
    """节拍信息"""
    timestamp: float          # 节拍时间点 (秒)
    strength: float           # 节拍强度 (0.0-1.0)
    beat_number: int          # 节拍编号
    measure: int              # 小节编号
    beat_in_measure: int      # 小节内的节拍位置


@dataclass 
class AudioFeatures:
    """音频特征数据"""
    duration: float                    # 总时长 (秒)
    sample_rate: int                   # 采样率
    bpm: float                         # 每分钟节拍数
    beats: List[BeatInfo] = field(default_factory=list)  # 节拍列表
    energy_curve: List[float] = field(default_factory=list)  # 能量曲线
    onset_frames: List[float] = field(default_factory=list)  # 起音时间点


class AudioAnalyzer:
    """音频分析器
    
    使用 FFmpeg 提取基本音频信息，
    可选使用 librosa (如果已安装) 进行高级分析。
    """
    
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        """初始化音频分析器
        
        Args:
            ffmpeg_path: FFmpeg 可执行文件路径
        """
        self.ffmpeg_path = ffmpeg_path
        self._librosa_available = self._check_librosa()
    
    def _check_librosa(self) -> bool:
        """检查 librosa 是否可用"""
        try:
            import librosa
            return True
        except ImportError:
            logger.info("librosa 未安装，使用基础音频分析")
            return False
    
    def analyze(self, audio_path: Path) -> AudioFeatures:
        """分析音频文件
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            AudioFeatures 音频特征数据
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        # 获取基础信息 (FFmpeg)
        duration, sample_rate = self._get_basic_info(audio_path)
        
        features = AudioFeatures(
            duration=duration,
            sample_rate=sample_rate,
            bpm=120.0  # 默认 BPM
        )
        
        # 如果 librosa 可用，进行高级分析
        if self._librosa_available:
            self._analyze_with_librosa(audio_path, features)
        
        return features
    
    def _get_basic_info(self, audio_path: Path) -> tuple[float, int]:
        """使用 FFmpeg 获取基础音频信息"""
        try:
            cmd = [
                self.ffmpeg_path, "-i", str(audio_path),
                "-hide_banner", "-f", "null", "-"
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )
            
            # 从 stderr 解析信息 (FFmpeg 输出到 stderr)
            output = result.stderr
            
            # 解析时长
            duration = 0.0
            if "Duration:" in output:
                import re
                match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", output)
                if match:
                    h, m, s, ms = match.groups()
                    duration = int(h)*3600 + int(m)*60 + int(s) + int(ms)/100
            
            # 解析采样率
            sample_rate = 44100  # 默认值
            if "Hz" in output:
                import re
                match = re.search(r"(\d+) Hz", output)
                if match:
                    sample_rate = int(match.group(1))
            
            return duration, sample_rate
            
        except Exception as e:
            logger.warning(f"FFmpeg 分析失败: {e}")
            return 0.0, 44100
    
    def _analyze_with_librosa(self, audio_path: Path, features: AudioFeatures) -> None:
        """使用 librosa 进行高级分析"""
        try:
            import librosa
            import numpy as np
            
            # 加载音频
            y, sr = librosa.load(str(audio_path), sr=None)
            
            # 检测 BPM 和节拍
            tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            features.bpm = float(tempo) if np.isscalar(tempo) else float(tempo[0])
            
            # 转换节拍帧到时间
            beat_times = librosa.frames_to_time(beat_frames, sr=sr)
            
            # 构建节拍信息
            beats_per_measure = 4  # 假设 4/4 拍
            for i, t in enumerate(beat_times):
                beat = BeatInfo(
                    timestamp=float(t),
                    strength=1.0 if (i % beats_per_measure == 0) else 0.7,
                    beat_number=i,
                    measure=i // beats_per_measure,
                    beat_in_measure=i % beats_per_measure
                )
                features.beats.append(beat)
            
            # 计算能量曲线 (RMS)
            rms = librosa.feature.rms(y=y)[0]
            features.energy_curve = (rms / rms.max()).tolist() if rms.max() > 0 else []
            
            # 检测起音
            onset_frames_arr = librosa.onset.onset_detect(y=y, sr=sr)
            features.onset_frames = librosa.frames_to_time(onset_frames_arr, sr=sr).tolist()
            
            logger.info(f"音频分析完成: BPM={features.bpm:.1f}, 节拍数={len(features.beats)}")
            
        except Exception as e:
            logger.warning(f"librosa 分析失败: {e}")

