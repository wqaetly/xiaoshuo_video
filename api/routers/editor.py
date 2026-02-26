"""
视频编辑 API 路由
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query

from ..models.editor import (
    Timeline,
    TrimRequest,
    ConcatRequest,
    SpeedAdjustRequest,
    VolumeAdjustRequest,
    ExportRequest,
    ExportProgress,
    MediaInfo,
    MaterialListResponse,
    TransitionType,
    VideoClip,
    AudioClip,
    SubtitleClip,
)
from ..services.editor_service import get_editor_service

router = APIRouter()


@router.get("/transitions", response_model=List[TransitionType])
async def list_transitions():
    """获取可用转场效果列表"""
    transitions = [
        TransitionType(id="fade", name="淡入淡出"),
        TransitionType(id="wipeleft", name="向左擦除"),
        TransitionType(id="wiperight", name="向右擦除"),
        TransitionType(id="wipeup", name="向上擦除"),
        TransitionType(id="wipedown", name="向下擦除"),
        TransitionType(id="slideleft", name="向左滑动"),
        TransitionType(id="slideright", name="向右滑动"),
        TransitionType(id="circleclose", name="圆形关闭"),
        TransitionType(id="circleopen", name="圆形打开"),
        TransitionType(id="dissolve", name="溶解"),
    ]
    return transitions


@router.get("/media/info", response_model=MediaInfo)
async def get_media_info(path: str = Query(..., description="媒体文件路径")):
    """获取媒体文件信息"""
    service = get_editor_service()
    info = service.get_media_info(path)
    if info is None:
        raise HTTPException(status_code=404, detail=f"无法获取媒体信息: {path}")
    return MediaInfo(**info)


@router.get("/{project_name}/materials", response_model=MaterialListResponse)
async def list_materials(project_name: str):
    """获取项目素材列表"""
    service = get_editor_service()
    result = service.list_materials(project_name)
    return MaterialListResponse(
        videos=[MediaInfo(**v) for v in result["videos"]],
        audios=[MediaInfo(**a) for a in result["audios"]],
        images=result["images"],
    )


@router.get("/{project_name}/timeline", response_model=Timeline)
async def get_timeline(project_name: str):
    """获取时间轴数据"""
    service = get_editor_service()
    data = service.get_timeline(project_name)
    return Timeline(
        video_clips=[VideoClip(**c) for c in data.get("video_clips", [])],
        audio_clips=[AudioClip(**c) for c in data.get("audio_clips", [])],
        subtitle_clips=[SubtitleClip(**c) for c in data.get("subtitle_clips", [])],
        total_duration=data.get("total_duration", 0.0),
    )


@router.put("/{project_name}/timeline", response_model=Timeline)
async def update_timeline(project_name: str, timeline: Timeline):
    """更新时间轴数据"""
    service = get_editor_service()
    data = service.save_timeline(project_name, timeline.model_dump())
    return Timeline(**data)


@router.post("/{project_name}/trim", response_model=MediaInfo)
async def trim_video(project_name: str, request: TrimRequest):
    """裁剪视频"""
    service = get_editor_service()
    result = service.trim_video(
        project_name,
        request.source,
        request.start_time,
        request.end_time,
        request.output_name,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="裁剪视频失败")
    return MediaInfo(**result)


@router.post("/{project_name}/concat", response_model=MediaInfo)
async def concat_videos(project_name: str, request: ConcatRequest):
    """拼接视频"""
    service = get_editor_service()
    result = service.concat_videos(
        project_name,
        [c.model_dump() for c in request.clips],
        request.output_name,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="拼接视频失败")
    return MediaInfo(**result)


@router.post("/{project_name}/speed", response_model=MediaInfo)
async def adjust_speed(project_name: str, request: SpeedAdjustRequest):
    """调整视频速度"""
    service = get_editor_service()
    result = service.adjust_speed(
        project_name,
        request.source,
        request.speed,
        request.output_name,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="调整速度失败")
    return MediaInfo(**result)


@router.post("/{project_name}/volume", response_model=MediaInfo)
async def adjust_volume(project_name: str, request: VolumeAdjustRequest):
    """调整音量"""
    service = get_editor_service()
    result = service.adjust_volume(
        project_name,
        request.source,
        request.volume,
        request.output_name,
    )
    if result is None:
        raise HTTPException(status_code=500, detail="调整音量失败")
    return MediaInfo(**result)


@router.post("/{project_name}/export")
async def export_video(
    project_name: str, request: ExportRequest, background_tasks: BackgroundTasks
):
    """导出视频"""
    # TODO: 实现视频导出（需要后台任务）
    return {
        "task_id": f"export_{project_name}",
        "message": "导出任务已添加到队列",
        "status": "pending",
    }


@router.get("/{project_name}/export/{task_id}", response_model=ExportProgress)
async def get_export_progress(project_name: str, task_id: str):
    """获取导出进度"""
    # TODO: 从任务服务获取进度
    return ExportProgress(
        task_id=task_id,
        progress=0.0,
        status="pending",
        message="等待处理",
    )

