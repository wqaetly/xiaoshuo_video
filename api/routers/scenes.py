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
    """重新生成场景资源"""
    # TODO: 将重新生成任务添加到后台任务队列
    return {
        "message": "已添加重新生成任务",
        "scene_ids": request.scene_ids,
        "resource_types": request.resource_types,
    }


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

