"""
文件上传与管理 API 路由
"""
import uuid
import shutil
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.utils.logger import get_logger

logger = get_logger("api.files")

router = APIRouter()

# 数据目录
DATA_DIR = Path(__file__).parent.parent.parent / "data"
PROJECTS_DIR = DATA_DIR / "projects"


class UploadResponse(BaseModel):
    """上传响应"""
    filename: str
    path: str
    size: int
    content_type: Optional[str] = None


class FileInfo(BaseModel):
    """文件信息"""
    name: str
    path: str
    size: int
    is_dir: bool


def ensure_dir(path: Path) -> None:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)


@router.post("/{project_name}/upload", response_model=UploadResponse)
async def upload_file(
    project_name: str,
    file: UploadFile = File(...),
    subdir: Optional[str] = Form(default="uploads"),
):
    """上传文件到项目"""
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")

    upload_dir = project_dir / subdir
    ensure_dir(upload_dir)

    # 生成唯一文件名
    ext = Path(file.filename).suffix if file.filename else ""
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = upload_dir / unique_name

    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        return UploadResponse(
            filename=unique_name,
            path=str(file_path.relative_to(DATA_DIR)),
            size=len(content),
            content_type=file.content_type,
        )
    except Exception as e:
        logger.error(f"上传文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.post("/{project_name}/upload-novel", response_model=UploadResponse)
async def upload_novel(
    project_name: str,
    file: UploadFile = File(...),
):
    """上传小说文件"""
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")

    # 小说保存为固定名称
    file_path = project_dir / "novel.txt"

    try:
        content = await file.read()
        # 尝试解码验证是否为文本文件
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="文件不是有效的UTF-8文本")

        with open(file_path, "wb") as f:
            f.write(content)

        return UploadResponse(
            filename="novel.txt",
            path=str(file_path.relative_to(DATA_DIR)),
            size=len(content),
            content_type="text/plain",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"上传小说失败: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.get("/{project_name}/list", response_model=List[FileInfo])
async def list_files(project_name: str, subdir: Optional[str] = None):
    """列出项目文件"""
    project_dir = PROJECTS_DIR / project_name
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail=f"项目不存在: {project_name}")

    target_dir = project_dir / subdir if subdir else project_dir
    if not target_dir.exists():
        return []

    files = []
    for item in target_dir.iterdir():
        files.append(FileInfo(
            name=item.name,
            path=str(item.relative_to(DATA_DIR)),
            size=item.stat().st_size if item.is_file() else 0,
            is_dir=item.is_dir(),
        ))

    return files


@router.delete("/{project_name}/file")
async def delete_file(project_name: str, path: str):
    """删除项目文件"""
    file_path = DATA_DIR / path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 安全检查：确保文件在项目目录内
    project_dir = PROJECTS_DIR / project_name
    if not str(file_path.resolve()).startswith(str(project_dir.resolve())):
        raise HTTPException(status_code=403, detail="无权限删除此文件")

    try:
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        return {"message": "文件已删除", "path": path}
    except Exception as e:
        logger.error(f"删除文件失败: {e}")
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")

