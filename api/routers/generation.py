"""
生成控制 API 路由
"""
from typing import List

from fastapi import APIRouter, HTTPException, BackgroundTasks

from ..models.generation import (
    OllamaServiceStatus,
    ComfyUIServiceStatus,
    CosyVoiceServiceStatus,
    ServicesStatusResponse,
    GenerationStartRequest,
    GenerationStopRequest,
    GenerationProgress,
    GenerationResult,
    PhaseOption,
    PhaseListResponse,
)
from ..services.generation_service import get_generation_service

router = APIRouter()


@router.get("/services", response_model=ServicesStatusResponse)
async def check_services():
    """检查所有服务状态"""
    service = get_generation_service()
    status = await service.check_services()
    return ServicesStatusResponse(
        ollama=OllamaServiceStatus(
            available=status["ollama"]["status"] == "online",
            model=status["ollama"].get("model", ""),
        ),
        comfyui=ComfyUIServiceStatus(
            available=status["comfyui"]["status"] == "online",
            queue_size=status["comfyui"].get("queue_size", 0),
        ),
        cosyvoice=CosyVoiceServiceStatus(
            available=status["cosyvoice"]["status"] == "online",
        ),
    )


@router.get("/phases", response_model=PhaseListResponse)
async def list_phases():
    """获取可用生成阶段列表"""
    phases = [
        PhaseOption(id="full", name="完整流程", description="执行所有阶段"),
        PhaseOption(id="analyze", name="分析小说", description="分析小说生成分镜"),
        PhaseOption(id="character_design", name="角色设计", description="生成角色立绘"),
        PhaseOption(id="generate_images", name="图像生成", description="生成场景图像"),
        PhaseOption(id="generate_audio", name="音频生成", description="生成配音"),
        PhaseOption(id="generate_video", name="视频生成", description="生成场景视频"),
        PhaseOption(id="compose", name="合成视频", description="合成最终视频"),
    ]
    return PhaseListResponse(phases=phases)


@router.post("/start", response_model=GenerationResult)
async def start_generation(request: GenerationStartRequest):
    """启动生成任务"""
    service = get_generation_service()
    try:
        result = service.start_generation(
            project_name=request.project_name,
            phase=request.phase,
            resume=request.resume,
            start_from=request.start_from,
        )
        return GenerationResult(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"启动失败: {e}")


@router.post("/stop", response_model=GenerationResult)
async def stop_generation(request: GenerationStopRequest):
    """停止生成任务"""
    service = get_generation_service()
    result = service.stop_generation(request.project_name)
    return GenerationResult(**result)


@router.get("/progress/{project_name}", response_model=GenerationProgress)
async def get_progress(project_name: str):
    """获取生成进度（全局流程）"""
    service = get_generation_service()
    progress = service.get_progress(project_name)
    return GenerationProgress(**progress)


@router.get("/micro-tasks/{project_name}")
async def get_micro_tasks(project_name: str, active_only: bool = False):
    """获取微任务列表

    微任务是独立于全局流程的小任务，如单独重新生成某个场景的图片。
    每个微任务有独立的进度跟踪。

    Args:
        project_name: 项目名称
        active_only: 是否只返回活跃任务（pending/running）
    """
    service = get_generation_service()
    if active_only:
        tasks = service.get_active_micro_tasks(project_name)
    else:
        tasks = service.get_micro_tasks(project_name)
    return {"tasks": tasks, "count": len(tasks)}

