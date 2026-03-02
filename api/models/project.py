"""
项目相关数据模型
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """创建项目请求"""
    name: str = Field(..., min_length=1, max_length=100, description="项目名称")
    style: str = Field(default="anime", description="视频风格")


class ProjectInfo(BaseModel):
    """项目基本信息"""
    name: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    novel_file: Optional[str] = None
    style: str = "anime"


class ProjectStatus(BaseModel):
    """项目状态信息"""
    name: str
    current_phase: str = "init"
    total_scenes: int = 0
    completed_scenes: Dict[str, List[str]] = Field(default_factory=dict)
    progress: float = 0.0
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class ProjectDetail(BaseModel):
    """项目详情"""
    info: ProjectInfo
    status: ProjectStatus
    stats: Dict[str, int] = Field(default_factory=dict)


class ProjectListItem(BaseModel):
    """项目列表项"""
    name: str
    phase: str = "init"
    progress: float = 0.0
    scenes_count: int = 0
    updated_at: Optional[str] = None


class ProjectListResponse(BaseModel):
    """项目列表响应"""
    projects: List[ProjectListItem]
    total: int


class ProgressStats(BaseModel):
    """进度统计"""
    total_scenes: int = 0
    images_done: int = 0
    audio_done: int = 0
    videos_done: int = 0
    phase: str = "init"
    progress_pct: float = 0.0


class QuickCreateResponse(BaseModel):
    """快速创建响应 - 创建并启动生成"""
    name: str
    created_at: Optional[str] = None
    style: str = "anime"
    novel_file: Optional[str] = None
    generation_started: bool = False
    generation_message: str = ""

