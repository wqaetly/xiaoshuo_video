"""
分镜场景数据模型

匹配 storyboard.json 的数据结构:
{
    "id": "scene_01_001",
    "chapter": 1,
    "sequence": 1,
    "global_index": 1,
    "duration": 5.0,
    "visual": {...},
    "audio": {...},
    "subtitle": {...},
    "generation_status": {...}
}
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CameraInfo(BaseModel):
    """镜头信息"""
    type: str = "static"
    start_frame: str = "medium_shot"
    end_frame: str = "medium_shot"


class VisualInfo(BaseModel):
    """视觉描述"""
    description: str = ""
    sd_prompt: Optional[str] = None
    style_tags: List[str] = Field(default_factory=list)
    characters_in_scene: List[str] = Field(default_factory=list)
    camera: CameraInfo = Field(default_factory=CameraInfo)


class NarrationInfo(BaseModel):
    """旁白信息"""
    text: str = ""
    emotion: str = "calm"


class DialogueInfo(BaseModel):
    """对话信息"""
    character_id: str
    text: str
    emotion: str = "neutral"


class AudioInfo(BaseModel):
    """音频信息"""
    narration: Optional[NarrationInfo] = None
    dialogues: List[DialogueInfo] = Field(default_factory=list)
    bgm: str = "ambient"
    sfx: List[str] = Field(default_factory=list)


class SubtitleInfo(BaseModel):
    """字幕信息"""
    text: str = ""
    style: str = "narration"
    character: Optional[str] = None


class GenerationStatus(BaseModel):
    """生成状态"""
    image: str = "pending"
    audio: str = "pending"
    video: str = "pending"


class Scene(BaseModel):
    """场景完整信息 - 匹配 storyboard.json 结构"""
    id: str
    chapter: int = 1
    sequence: int = 1
    global_index: int = 1
    duration: float = 5.0
    visual: VisualInfo = Field(default_factory=VisualInfo)
    audio: AudioInfo = Field(default_factory=AudioInfo)
    subtitle: SubtitleInfo = Field(default_factory=SubtitleInfo)
    generation_status: GenerationStatus = Field(default_factory=GenerationStatus)
    # 资源路径（由服务层添加）
    image_path: Optional[str] = None
    audio_path: Optional[str] = None
    video_path: Optional[str] = None

    class Config:
        extra = "allow"  # 允许额外字段


class SceneCreate(BaseModel):
    """创建场景请求"""
    chapter: int = 1
    duration: float = 5.0
    visual: Optional[VisualInfo] = None
    audio: Optional[AudioInfo] = None
    subtitle: Optional[SubtitleInfo] = None


class SceneUpdate(BaseModel):
    """更新场景请求"""
    duration: Optional[float] = None
    visual: Optional[Dict[str, Any]] = None
    audio: Optional[Dict[str, Any]] = None
    subtitle: Optional[Dict[str, Any]] = None


class SceneListResponse(BaseModel):
    """场景列表响应"""
    scenes: List[Scene]
    total: int
    chapters: List[int] = Field(default_factory=list)


class SceneFilter(BaseModel):
    """场景筛选条件"""
    chapter: Optional[int] = None
    status: Optional[str] = None
    has_image: Optional[bool] = None
    has_audio: Optional[bool] = None
    has_video: Optional[bool] = None


class SceneReorderRequest(BaseModel):
    """场景重新排序请求"""
    scene_ids: List[str] = Field(..., description="按新顺序排列的场景ID列表")


class SceneRegenerateRequest(BaseModel):
    """场景重新生成请求"""
    scene_ids: List[str]
    resource_types: List[str] = Field(
        default_factory=lambda: ["image"],
        description="要重新生成的资源类型: image, audio, video"
    )

