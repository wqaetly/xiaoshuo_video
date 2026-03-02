"""
角色数据模型

匹配 characters.json 的数据结构:
{
    "id": "char_001",
    "name": "李逍遥",
    "aliases": ["逍遥"],
    "appearance": {...},
    "sd_prompt": "...",
    "voice": {...}
}
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AppearanceInfo(BaseModel):
    """外貌信息"""
    gender: str = "unknown"
    hair: str = ""
    eyes: str = ""
    clothing: str = ""
    features: str = ""


class VoiceConfig(BaseModel):
    """语音配置"""
    provider: str = "edge"
    voice_id: str = "male_heroic"
    speed: float = 1.0
    pitch: int = 0


class Character(BaseModel):
    """角色完整信息 - 匹配 characters.json 结构"""
    id: str
    name: str = "未命名"
    aliases: List[str] = Field(default_factory=list)
    appearance: AppearanceInfo = Field(default_factory=AppearanceInfo)
    sd_prompt: str = ""
    sd_negative: str = ""
    voice: VoiceConfig = Field(default_factory=VoiceConfig)
    images: List[str] = Field(default_factory=list)

    class Config:
        extra = "allow"


class CharacterCreate(BaseModel):
    """创建角色请求"""
    name: str
    aliases: List[str] = Field(default_factory=list)
    appearance: Optional[Dict[str, Any]] = None
    sd_prompt: str = ""
    sd_negative: str = ""
    voice: Optional[Dict[str, Any]] = None


class CharacterUpdate(BaseModel):
    """更新角色请求"""
    name: Optional[str] = None
    aliases: Optional[List[str]] = None
    appearance: Optional[Dict[str, Any]] = None
    sd_prompt: Optional[str] = None
    sd_negative: Optional[str] = None
    voice: Optional[Dict[str, Any]] = None


class NarratorConfig(BaseModel):
    """旁白配置"""
    voice: VoiceConfig = Field(default_factory=VoiceConfig)


class CharacterListResponse(BaseModel):
    """角色列表响应"""
    characters: List[Character]
    total: int
    narrator: Optional[NarratorConfig] = None


class VoicePreviewRequest(BaseModel):
    """语音预览请求"""
    text: str = "你好，这是语音测试。"
    voice_id: str = "male_heroic"


class VoicePreviewResponse(BaseModel):
    """语音预览响应"""
    audio_data: Optional[str] = None  # Base64 编码的音频数据
    message: str = ""


class VoiceOption(BaseModel):
    """可用语音选项"""
    id: str
    name: str
    gender: str
    provider: str = "edge"
    sample_url: Optional[str] = None


class VoiceListResponse(BaseModel):
    """语音列表响应"""
    voices: List[VoiceOption]

