"""
项目管理 API 路由
"""
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse

from ..models.project import (
    ProjectCreate,
    ProjectInfo,
    ProjectDetail,
    ProjectListItem,
    ProjectListResponse,
    ProjectStatus,
    ProgressStats,
)
from ..services.project_service import get_project_service

router = APIRouter()


@router.get("", response_model=ProjectListResponse)
async def list_projects():
    """获取项目列表"""
    service = get_project_service()
    projects = service.list_projects()
    items = [
        ProjectListItem(
            name=p["name"],
            phase=p.get("phase", "init"),
            progress=p.get("progress", 0.0),
            scenes_count=p.get("scenes_count", 0),
            updated_at=p.get("updated_at"),
        )
        for p in projects
    ]
    return ProjectListResponse(projects=items, total=len(items))


@router.post("", response_model=ProjectInfo)
async def create_project(
    name: str = Form(...),
    style: str = Form(default="anime"),
    novel_file: UploadFile = File(...),
):
    """创建新项目"""
    service = get_project_service()
    try:
        # 读取上传的文件内容
        content = await novel_file.read()
        result = service.create_project(name, style, content)
        return ProjectInfo(
            name=result["name"],
            created_at=result.get("created_at"),
            style=result.get("style", "anime"),
            novel_file=result.get("novel_file"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建项目失败: {e}")


@router.get("/{project_name}", response_model=ProjectDetail)
async def get_project(project_name: str):
    """获取项目详情"""
    service = get_project_service()
    info = service.get_project(project_name)
    if info is None:
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")

    status = service.get_project_status(project_name) or {}
    stats = service.get_project_stats(project_name) or {}

    return ProjectDetail(
        info=ProjectInfo(**info),
        status=ProjectStatus(**status) if status else ProjectStatus(name=project_name),
        stats=stats,
    )


@router.delete("/{project_name}")
async def delete_project(project_name: str):
    """删除项目"""
    service = get_project_service()
    if not service.delete_project(project_name):
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")
    return {"message": f"项目 {project_name} 已删除"}


@router.get("/{project_name}/status", response_model=ProjectStatus)
async def get_project_status(project_name: str):
    """获取项目状态"""
    service = get_project_service()
    status = service.get_project_status(project_name)
    if status is None:
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")
    return ProjectStatus(**status)


@router.get("/{project_name}/stats", response_model=ProgressStats)
async def get_project_stats(project_name: str):
    """获取项目进度统计"""
    service = get_project_service()
    stats = service.get_project_stats(project_name)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")
    return ProgressStats(**stats)

