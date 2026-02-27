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
    QuickCreateResponse,
)
from ..services.project_service import get_project_service
from ..services.generation_service import get_generation_service

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


@router.post("/quick-create", response_model=QuickCreateResponse)
async def quick_create_project(
    name: str = Form(...),
    style: str = Form(default="anime"),
    novel_file: UploadFile = File(...),
):
    """快速创建项目并立即启动生成

    一键式操作：创建项目 -> 自动启动完整生成流程
    适用于歌词、短文等快速生成场景
    """
    project_service = get_project_service()
    generation_service = get_generation_service()

    try:
        # 1. 创建项目
        content = await novel_file.read()
        project_result = project_service.create_project(name, style, content)

        # 2. 立即启动生成
        gen_result = generation_service.start_generation(
            project_name=name,
            phase="full",
            resume=False,  # 新项目不需要续传
        )

        return QuickCreateResponse(
            name=project_result["name"],
            created_at=project_result.get("created_at"),
            style=project_result.get("style", "anime"),
            novel_file=project_result.get("novel_file"),
            generation_started=gen_result.get("success", False),
            generation_message=gen_result.get("message", ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"快速创建失败: {e}")


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


@router.put("/{project_name}/novel")
async def update_novel(
    project_name: str,
    novel_file: UploadFile = File(...),
):
    """更换项目的小说源文件

    上传新的小说文件，会自动重置分镜数据和项目状态
    """
    service = get_project_service()
    try:
        content = await novel_file.read()
        result = service.update_novel(project_name, content)
        return {
            "success": True,
            "message": "小说文件已更新，分镜数据已重置",
            **result,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新小说文件失败: {e}")


@router.get("/{project_name}/novel")
async def get_novel_content(project_name: str):
    """获取项目的小说内容"""
    service = get_project_service()
    content = service.get_novel_content(project_name)
    if content is None:
        raise HTTPException(status_code=404, detail=f"小说文件不存在: {project_name}")
    return {"content": content}

