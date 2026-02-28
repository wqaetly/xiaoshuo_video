"""
任务队列 API 路由
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..models.task import (
    Task,
    TaskListResponse,
    QueueStatus,
    BatchOperationRequest,
    BatchOperationResponse,
    LogsResponse,
    LogEntry,
)
from ..services.task_service import get_task_service
from ..services.task_queue.events import get_event_emitter

router = APIRouter()


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None, description="按状态筛选"),
    limit: int = Query(100, ge=1, le=500),
):
    """获取任务列表"""
    service = get_task_service()
    result = service.list_tasks(status, limit)
    return TaskListResponse(
        tasks=[Task(**t) for t in result["tasks"]],
        total=result["total"],
        running=result["running"],
        pending=result["pending"],
        completed=result["completed"],
        failed=result["failed"],
    )


@router.get("/status", response_model=QueueStatus)
async def get_queue_status():
    """获取队列状态"""
    service = get_task_service()
    status = service.get_queue_status()
    return QueueStatus(**status)


@router.get("/logs", response_model=LogsResponse)
async def get_logs(
    level: Optional[str] = Query(None, description="日志级别"),
    limit: int = Query(100, ge=1, le=1000),
):
    """获取日志"""
    service = get_task_service()
    result = service.get_logs(level, limit)
    return LogsResponse(
        logs=[LogEntry(**l) for l in result["logs"]],
        total=result["total"],
    )


@router.delete("/logs")
async def clear_logs():
    """清除日志"""
    service = get_task_service()
    service.clear_logs()
    return {"message": "ok"}


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str):
    """获取任务详情"""
    service = get_task_service()
    task = service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {task_id}")
    return Task(**service._task_to_dict(task))


@router.delete("/{task_id}")
async def cancel_task(task_id: str):
    """取消任务"""
    service = get_task_service()
    if not service.cancel_task(task_id):
        raise HTTPException(status_code=400, detail=f"无法取消任务: {task_id}")
    return {"message": f"任务 {task_id} 已取消"}


@router.post("/clear-completed")
async def clear_completed_tasks():
    """清除已完成的任务"""
    service = get_task_service()
    cleared = service.clear_completed()
    return {"message": "ok", "cleared": cleared}


@router.post("/cancel-all")
async def cancel_all_tasks():
    """取消所有任务"""
    service = get_task_service()
    cancelled = service.cancel_all()
    return {"message": "ok", "cancelled": cancelled}


@router.post("/batch", response_model=BatchOperationResponse)
async def batch_operation(request: BatchOperationRequest):
    """批量操作场景"""
    # 批量操作需要结合 scene_service 和 task_service
    service = get_task_service()

    task_ids = []
    for scene_id in request.scene_ids:
        if request.regenerate_image:
            task = service.create_task(
                name=f"重新生成图像: {scene_id}",
                task_type="image",
                scene_id=scene_id,
            )
            task_ids.append(task.id)
        if request.regenerate_audio:
            task = service.create_task(
                name=f"重新生成音频: {scene_id}",
                task_type="audio",
                scene_id=scene_id,
            )
            task_ids.append(task.id)
        if request.regenerate_video:
            task = service.create_task(
                name=f"重新生成视频: {scene_id}",
                task_type="video",
                scene_id=scene_id,
            )
            task_ids.append(task.id)

    return BatchOperationResponse(
        success=True,
        message=f"已创建 {len(task_ids)} 个任务",
        affected_count=len(request.scene_ids),
        task_ids=task_ids,
    )


@router.get("/events/stream")
async def task_events_stream():
    """任务事件 SSE 流

    使用 Server-Sent Events 实时推送任务状态更新。

    事件类型:
    - task_created: 任务创建
    - task_started: 任务开始执行
    - task_progress: 任务进度更新
    - task_completed: 任务完成
    - task_failed: 任务失败
    """
    async def event_generator():
        emitter = get_event_emitter()

        # 发送连接成功事件
        yield "event: connected\ndata: {\"message\": \"SSE 连接成功\"}\n\n"

        # 订阅事件流
        async for event in emitter.subscribe():
            yield event.to_sse()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
        }
    )
