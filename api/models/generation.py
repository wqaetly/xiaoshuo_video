"""
生成控制数据模型
"""
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class OllamaServiceStatus(BaseModel):
    """Ollama 服务状态"""
    available: bool
    model: str = ""


class ComfyUIServiceStatus(BaseModel):
    """ComfyUI 服务状态"""
    available: bool
    queue_size: int = 0


class CosyVoiceServiceStatus(BaseModel):
    """CosyVoice 服务状态"""
    available: bool


class ServicesStatusResponse(BaseModel):
    """所有服务状态响应"""
    ollama: OllamaServiceStatus
    comfyui: ComfyUIServiceStatus
    cosyvoice: CosyVoiceServiceStatus


class GenerationStartRequest(BaseModel):
    """启动生成请求"""
    project_name: str
    phase: str = "full"  # full, analyze, character_design, generate_images, etc.
    resume: bool = True
    skip_failed: bool = True
    failure_threshold: int = 50


class GenerationStopRequest(BaseModel):
    """停止生成请求"""
    project_name: str


class CompletedTasks(BaseModel):
    """各类型任务完成数"""
    character: int = 0
    image: int = 0
    audio: int = 0
    video: int = 0


class FailedScene(BaseModel):
    """失败场景信息"""
    scene_id: str
    phase: str
    message: str
    time: str


class GenerationProgress(BaseModel):
    """生成进度信息"""
    phase: str
    phase_index: int = 0  # 当前阶段索引 (0-7)
    total_phases: int = 7  # 总阶段数
    task: str
    progress: float  # 0.0 - 1.0
    message: str
    is_running: bool = False
    # 场景级进度
    current_scene_index: int = 0
    total_scenes: int = 0
    # 各类型任务完成情况
    completed_tasks: CompletedTasks = Field(default_factory=CompletedTasks)
    # 失败场景列表
    failed_scenes: List[FailedScene] = Field(default_factory=list)
    # 总错误数
    error_count: int = 0


class GenerationResult(BaseModel):
    """生成结果"""
    success: bool
    phase: str
    message: str
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class PhaseOption(BaseModel):
    """阶段选项"""
    id: str
    name: str
    description: str


class PhaseListResponse(BaseModel):
    """阶段列表响应"""
    phases: List[PhaseOption]

