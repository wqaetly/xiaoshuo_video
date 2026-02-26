"""
项目管理服务 - 封装项目相关业务逻辑
"""
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

import yaml

from src.utils.config import get_config, Config
from src.utils.file_utils import load_json, save_json, ensure_dir
from src.pipeline import PipelineState, Phase


class ProjectService:
    """项目管理服务"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = Path(self.config.paths.projects_dir)

    def get_projects_dir(self) -> Path:
        """获取项目目录"""
        return self.projects_dir

    def list_projects(self) -> List[Dict[str, Any]]:
        """获取项目列表"""
        if not self.projects_dir.exists():
            return []

        projects = []
        for p in self.projects_dir.iterdir():
            if not p.is_dir():
                continue

            project_info = {
                "name": p.name,
                "phase": "init",
                "progress": 0.0,
                "scenes_count": 0,
                "updated_at": None,
            }

            # 读取状态
            state_file = p / "pipeline_state.json"
            if state_file.exists():
                try:
                    state = PipelineState.load(state_file)
                    project_info["phase"] = state.current_phase.value
                    project_info["progress"] = state.get_progress()
                    project_info["updated_at"] = state.updated_at
                except Exception:
                    pass

            # 读取场景数量
            storyboard_file = p / "storyboard.json"
            if storyboard_file.exists():
                try:
                    storyboard = load_json(storyboard_file)
                    project_info["scenes_count"] = len(storyboard.get("scenes", []))
                except Exception:
                    pass

            projects.append(project_info)

        return sorted(projects, key=lambda x: x.get("updated_at") or "", reverse=True)

    def get_project(self, name: str) -> Optional[Dict[str, Any]]:
        """获取项目详情"""
        project_path = self.projects_dir / name
        if not project_path.exists():
            return None

        info = {
            "name": name,
            "created_at": None,
            "updated_at": None,
            "novel_file": None,
            "style": "anime",
        }

        # 读取项目配置
        config_file = project_path / "project.yaml"
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f) or {}
                info["style"] = config.get("video", {}).get("style", "anime")
            except Exception:
                pass

        # 检查小说文件
        novel_file = project_path / "input" / "novel.txt"
        if novel_file.exists():
            info["novel_file"] = str(novel_file)

        return info

    def get_project_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取项目状态"""
        project_path = self.projects_dir / name
        if not project_path.exists():
            return None

        status = {
            "name": name,
            "current_phase": "init",
            "total_scenes": 0,
            "completed_scenes": {},
            "progress": 0.0,
            "errors": [],
        }

        state_file = project_path / "pipeline_state.json"
        if state_file.exists():
            try:
                state = PipelineState.load(state_file)
                status["current_phase"] = state.current_phase.value
                status["total_scenes"] = state.total_scenes
                status["completed_scenes"] = state.completed_scenes
                status["progress"] = state.get_progress()
                status["errors"] = state.errors
            except Exception:
                pass

        return status

    def get_project_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """获取项目进度统计"""
        project_path = self.projects_dir / name
        if not project_path.exists():
            return None

        storyboard_path = project_path / "storyboard.json"
        if not storyboard_path.exists():
            return {
                "total_scenes": 0,
                "images_done": 0,
                "audio_done": 0,
                "videos_done": 0,
                "phase": "init",
                "progress_pct": 0.0,
            }

        storyboard = load_json(storyboard_path)
        scenes = storyboard.get("scenes", [])

        images_done = 0
        audio_done = 0
        videos_done = 0

        for scene in scenes:
            status = scene.get("generation_status", {})
            if status.get("image") == "completed":
                images_done += 1
            if status.get("audio") == "completed":
                audio_done += 1
            if status.get("video") == "completed":
                videos_done += 1

        total = len(scenes)
        progress = 0.0
        if total > 0:
            progress = (images_done + audio_done + videos_done) / (total * 3) * 100

        return {
            "total_scenes": total,
            "images_done": images_done,
            "audio_done": audio_done,
            "videos_done": videos_done,
            "phase": "init",
            "progress_pct": round(progress, 1),
        }

    def create_project(
        self, name: str, style: str = "anime", novel_content: Optional[bytes] = None
    ) -> Dict[str, Any]:
        """创建新项目"""
        project_path = self.projects_dir / name
        if project_path.exists():
            raise ValueError(f"项目 {name} 已存在")

        # 创建目录结构
        for dir_name in ["input", "characters", "images", "videos", "audio", "output"]:
            ensure_dir(project_path / dir_name)

        # 保存小说文件
        if novel_content:
            novel_path = project_path / "input" / "novel.txt"
            novel_path.write_bytes(novel_content)

        # 创建项目配置
        project_config = {
            "project": {"name": name},
            "video": {"style": style},
            "local": {
                "ollama_url": self.config.local.ollama_url,
                "ollama_model": self.config.local.ollama_model,
                "comfyui_url": self.config.local.comfyui_url,
                "cosyvoice_url": self.config.local.cosyvoice_url,
            },
        }
        with open(project_path / "project.yaml", "w", encoding="utf-8") as f:
            yaml.dump(project_config, f, allow_unicode=True)

        return {
            "name": name,
            "created_at": datetime.now().isoformat(),
            "style": style,
            "novel_file": str(project_path / "input" / "novel.txt") if novel_content else None,
        }

    def delete_project(self, name: str) -> bool:
        """删除项目"""
        project_path = self.projects_dir / name
        if not project_path.exists():
            return False

        shutil.rmtree(project_path)
        return True


# 单例模式
_project_service: Optional[ProjectService] = None


def get_project_service() -> ProjectService:
    """获取项目服务实例"""
    global _project_service
    if _project_service is None:
        _project_service = ProjectService()
    return _project_service

