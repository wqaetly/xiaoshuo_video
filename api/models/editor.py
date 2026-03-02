"""
视频编辑数据模型
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class VideoClip(BaseModel):
    """视频片段"""
    id: str
    source: str  # 源文件路径
    start_time: float = 0.0  # 开始时间（秒）
    end_time: Optional[float] = None  # 结束时间（秒）
    duration: float = 0.0
    thumbnail: Optional[str] = None
    track: int = 0  # 轨道索引


class AudioClip(BaseModel):
    """音频片段"""
    id: str
    source: str
    start_time: float = 0.0
    end_time: Optional[float] = None
    duration: float = 0.0
    volume: float = 1.0
    track: int = 0


class SubtitleClip(BaseModel):
    """字幕片段"""
    id: str
    text: str
    start_time: float
    end_time: float
    style: Optional[Dict[str, Any]] = None


class Timeline(BaseModel):
    """时间轴数据"""
    video_clips: List[VideoClip] = Field(default_factory=list)
    audio_clips: List[AudioClip] = Field(default_factory=list)
    subtitle_clips: List[SubtitleClip] = Field(default_factory=list)
    total_duration: float = 0.0


class TransitionType(BaseModel):
    """转场类型"""
    id: str
    name: str
    preview_url: Optional[str] = None


class TransitionConfig(BaseModel):
    """转场配置"""
    type: str  # fade, wipeleft, wiperight, etc.
    duration: float = 1.0


class TrimRequest(BaseModel):
    """裁剪请求"""
    source: str
    start_time: float
    end_time: float
    output_name: Optional[str] = None


class ConcatRequest(BaseModel):
    """拼接请求"""
    clips: List[VideoClip]
    transitions: List[Optional[TransitionConfig]] = Field(default_factory=list)
    output_name: Optional[str] = None


class SpeedAdjustRequest(BaseModel):
    """变速请求"""
    source: str
    speed: float = 1.0  # 0.5 = 慢放, 2.0 = 快进
    output_name: Optional[str] = None


class VolumeAdjustRequest(BaseModel):
    """音量调整请求"""
    source: str
    volume: float = 1.0
    output_name: Optional[str] = None


class ExportRequest(BaseModel):
    """导出请求"""
    timeline: Timeline
    resolution: str = "1280x720"
    fps: int = 24
    format: str = "mp4"
    output_name: Optional[str] = None


class ExportProgress(BaseModel):
    """导出进度"""
    task_id: str
    progress: float = 0.0
    status: str = "pending"  # pending, processing, completed, failed
    output_path: Optional[str] = None
    message: str = ""


class MediaInfo(BaseModel):
    """媒体文件信息"""
    path: str
    duration: float
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None
    codec: Optional[str] = None
    thumbnail: Optional[str] = None


class MaterialListResponse(BaseModel):
    """素材列表响应"""
    videos: List[MediaInfo] = Field(default_factory=list)
    audios: List[MediaInfo] = Field(default_factory=list)
    images: List[str] = Field(default_factory=list)

