"""
分镜场景 API 路由
"""
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from ..models.scene import (
    Scene,
    SceneCreate,
    SceneUpdate,
    SceneListResponse,
    SceneFilter,
    SceneReorderRequest,
    SceneRegenerateRequest,
)
from ..services.scene_service import get_scene_service

router = APIRouter()


@router.get("/{project_name}", response_model=SceneListResponse)
async def list_scenes(
    project_name: str,
    chapter: Optional[int] = Query(None, description="按章节筛选"),
    status: Optional[str] = Query(None, description="按状态筛选"),
):
    """获取场景列表"""
    service = get_scene_service()
    result = service.list_scenes(project_name, chapter, status)
    return SceneListResponse(
        scenes=[Scene(**s) for s in result["scenes"]],
        total=result["total"],
        chapters=result["chapters"],
    )


@router.get("/{project_name}/{scene_id}", response_model=Scene)
async def get_scene(project_name: str, scene_id: str):
    """获取场景详情"""
    service = get_scene_service()
    scene = service.get_scene(project_name, scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail=f"场景不存在: {scene_id}")
    return Scene(**scene)


@router.post("/{project_name}", response_model=Scene)
async def create_scene(project_name: str, scene: SceneCreate):
    """创建场景"""
    service = get_scene_service()
    try:
        result = service.create_scene(project_name, scene.model_dump())
        return Scene(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建场景失败: {e}")


@router.put("/{project_name}/{scene_id}", response_model=Scene)
async def update_scene(project_name: str, scene_id: str, scene: SceneUpdate):
    """更新场景"""
    service = get_scene_service()
    result = service.update_scene(project_name, scene_id, scene.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=404, detail=f"场景不存在: {scene_id}")
    return Scene(**result)


@router.delete("/{project_name}/{scene_id}")
async def delete_scene(project_name: str, scene_id: str):
    """删除场景"""
    service = get_scene_service()
    if not service.delete_scene(project_name, scene_id):
        raise HTTPException(status_code=404, detail=f"场景不存在: {scene_id}")
    return {"message": f"场景 {scene_id} 已删除"}


@router.post("/{project_name}/reorder")
async def reorder_scenes(project_name: str, request: SceneReorderRequest):
    """重新排序场景"""
    service = get_scene_service()
    if not service.reorder_scenes(project_name, request.scene_ids):
        raise HTTPException(status_code=400, detail="排序失败")
    return {"message": "排序成功", "scene_ids": request.scene_ids}


@router.post("/{project_name}/regenerate")
async def regenerate_scenes(
    project_name: str, request: SceneRegenerateRequest, background_tasks: BackgroundTasks
):
    """重新生成场景资源

    手动指定要重新生成的场景和资源类型。
    会先标记这些场景为失效，然后触发重新生成。
    """
    from ..services.generation_service import get_generation_service

    scene_service = get_scene_service()
    generation_service = get_generation_service()

    # 手动标记指定场景为失效
    for scene_id in request.scene_ids:
        scene_service._invalidate_scene_resources(
            project_name,
            scene_id,
            set(request.resource_types)
        )

    # 触发增量更新
    result = generation_service.regenerate_invalidated(project_name)

    return {
        "success": result.get("success", True),
        "message": result.get("message", "已添加重新生成任务"),
        "scene_ids": request.scene_ids,
        "resource_types": request.resource_types,
    }


@router.post("/{project_name}/sync-changes")
async def sync_changes(project_name: str):
    """同步变更 - 重新生成所有失效的场景资源

    当分镜文本被修改后，相关资源会自动标记为失效。
    调用此接口会重新生成所有失效的资源。
    """
    from ..services.generation_service import get_generation_service

    generation_service = get_generation_service()

    # 先检查是否有失效的场景
    status = generation_service.get_invalidation_status(project_name)
    if not status.get("has_invalidated", False):
        return {
            "success": True,
            "message": "没有需要同步的变更",
            "invalidated_counts": status.get("invalidated_counts", {}),
        }

    # 触发增量更新
    result = generation_service.regenerate_invalidated(project_name)

    return {
        "success": result.get("success", True),
        "message": result.get("message", "已启动同步任务"),
        "invalidated_counts": status.get("invalidated_counts", {}),
    }


@router.get("/{project_name}/invalidation-status")
async def get_invalidation_status(project_name: str):
    """获取项目的失效状态

    返回所有被标记为失效需要重新生成的场景信息。
    """
    from ..services.generation_service import get_generation_service

    generation_service = get_generation_service()
    status = generation_service.get_invalidation_status(project_name)

    return status


@router.post("/{project_name}/analyze")
async def analyze_novel(project_name: str, background_tasks: BackgroundTasks):
    """分析小说生成分镜"""
    service = get_scene_service()
    try:
        result = service.analyze_novel(project_name)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {e}")

