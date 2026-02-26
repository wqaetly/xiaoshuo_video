"""
分镜场景服务 - 封装场景相关业务逻辑
"""
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.utils.config import get_config, Config
from src.utils.file_utils import load_json, save_json, ensure_dir


class SceneService:
    """分镜场景管理服务"""

    def __init__(self, config: Optional[Config] = None):
        self.config = config or get_config()
        self.projects_dir = Path(self.config.paths.projects_dir)

    def _get_storyboard_path(self, project_name: str) -> Path:
        """获取分镜文件路径"""
        return self.projects_dir / project_name / "storyboard.json"

    def _load_storyboard(self, project_name: str) -> Optional[Dict[str, Any]]:
        """加载分镜数据"""
        path = self._get_storyboard_path(project_name)
        if not path.exists():
            return None
        return load_json(path)

    def _save_storyboard(self, project_name: str, storyboard: Dict[str, Any]) -> None:
        """保存分镜数据"""
        save_json(self._get_storyboard_path(project_name), storyboard)

    def list_scenes(
        self, project_name: str, chapter: Optional[int] = None, status: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取场景列表"""
        storyboard = self._load_storyboard(project_name)
        if storyboard is None:
            return {"scenes": [], "total": 0, "chapters": []}

        scenes = storyboard.get("scenes", [])
        chapters_set = set()

        # 收集所有章节
        for s in scenes:
            ch = s.get("chapter")
            if ch is not None:
                chapters_set.add(ch)

        # 过滤
        if chapter is not None:
            scenes = [s for s in scenes if s.get("chapter") == chapter]
        if status:
            scenes = [s for s in scenes if s.get("generation_status", {}).get("image") == status]

        return {
            "scenes": scenes,
            "total": len(scenes),
            "chapters": sorted(list(chapters_set)),
        }

    def get_scene(self, project_name: str, scene_id: str) -> Optional[Dict[str, Any]]:
        """获取场景详情"""
        storyboard = self._load_storyboard(project_name)
        if storyboard is None:
            return None

        for scene in storyboard.get("scenes", []):
            if scene.get("id") == scene_id:
                # 添加资源路径
                project_path = self.projects_dir / project_name
                scene["image_path"] = str(project_path / "images" / f"{scene_id}.png")
                scene["audio_path"] = str(project_path / "audio" / f"{scene_id}.wav")
                scene["video_path"] = str(project_path / "videos" / f"{scene_id}.mp4")
                return scene

        return None

    def create_scene(self, project_name: str, scene_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新场景"""
        storyboard = self._load_storyboard(project_name)
        if storyboard is None:
            storyboard = {"novel_title": "", "total_scenes": 0, "scenes": []}

        # 生成场景ID
        scenes = storyboard.get("scenes", [])
        max_index = max([s.get("global_index", 0) for s in scenes], default=0)
        new_index = max_index + 1

        chapter = scene_data.get("chapter", 1)
        sequence = len([s for s in scenes if s.get("chapter") == chapter]) + 1

        scene = {
            "id": f"scene_{chapter:02d}_{sequence:03d}",
            "chapter": chapter,
            "sequence": sequence,
            "global_index": new_index,
            "duration": scene_data.get("duration", 5.0),
            "visual": scene_data.get("visual", {}),
            "audio": scene_data.get("audio", {}),
            "subtitle": scene_data.get("subtitle", {}),
            "generation_status": {"image": "pending", "audio": "pending", "video": "pending"},
        }

        scenes.append(scene)
        storyboard["scenes"] = scenes
        storyboard["total_scenes"] = len(scenes)
        self._save_storyboard(project_name, storyboard)

        return scene

    def update_scene(
        self, project_name: str, scene_id: str, updates: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """更新场景"""
        storyboard = self._load_storyboard(project_name)
        if storyboard is None:
            return None

        scenes = storyboard.get("scenes", [])
        for i, scene in enumerate(scenes):
            if scene.get("id") == scene_id:
                # 更新字段
                for key, value in updates.items():
                    if key not in ["id", "global_index"]:  # 保护关键字段
                        if isinstance(value, dict) and isinstance(scene.get(key), dict):
                            scene[key].update(value)
                        else:
                            scene[key] = value
                scenes[i] = scene
                storyboard["scenes"] = scenes
                self._save_storyboard(project_name, storyboard)
                return scene

        return None

    def delete_scene(self, project_name: str, scene_id: str) -> bool:
        """删除场景"""
        storyboard = self._load_storyboard(project_name)
        if storyboard is None:
            return False

        scenes = storyboard.get("scenes", [])
        new_scenes = [s for s in scenes if s.get("id") != scene_id]

        if len(new_scenes) == len(scenes):
            return False  # 没有找到要删除的场景

        storyboard["scenes"] = new_scenes
        storyboard["total_scenes"] = len(new_scenes)
        self._save_storyboard(project_name, storyboard)
        return True

    def reorder_scenes(self, project_name: str, scene_ids: List[str]) -> bool:
        """重新排序场景"""
        storyboard = self._load_storyboard(project_name)
        if storyboard is None:
            return False

        scenes = storyboard.get("scenes", [])
        scene_map = {s.get("id"): s for s in scenes}

        # 按新顺序重建场景列表
        new_scenes = []
        for i, scene_id in enumerate(scene_ids):
            if scene_id in scene_map:
                scene = scene_map[scene_id]
                scene["global_index"] = i + 1
                new_scenes.append(scene)

        # 添加未在列表中的场景
        for scene in scenes:
            if scene.get("id") not in scene_ids:
                scene["global_index"] = len(new_scenes) + 1
                new_scenes.append(scene)

        storyboard["scenes"] = new_scenes
        self._save_storyboard(project_name, storyboard)
        return True

    def analyze_novel(self, project_name: str) -> Dict[str, Any]:
        """分析小说生成分镜（调用 Pipeline Controller）"""
        from src.pipeline import PipelineController

        project_path = self.projects_dir / project_name
        if not project_path.exists():
            raise ValueError(f"项目不存在: {project_name}")

        novel_path = project_path / "input" / "novel.txt"
        if not novel_path.exists():
            raise ValueError("小说文件不存在")

        controller = PipelineController(project_path, self.config)
        controller.run_phase("analyze")

        # 重新加载分镜
        storyboard = self._load_storyboard(project_name)
        return {
            "success": True,
            "total_scenes": storyboard.get("total_scenes", 0) if storyboard else 0,
            "message": "分镜生成完成",
        }

    def get_scene_image_path(self, project_name: str, scene_id: str) -> Optional[Path]:
        """获取场景图像路径"""
        path = self.projects_dir / project_name / "images" / f"{scene_id}.png"
        return path if path.exists() else None


# 单例模式
_scene_service: Optional[SceneService] = None


def get_scene_service() -> SceneService:
    """获取场景服务实例"""
    global _scene_service
    if _scene_service is None:
        _scene_service = SceneService()
    return _scene_service

