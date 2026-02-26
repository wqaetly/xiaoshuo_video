"""
Pytest 配置和共享 fixtures
"""
import os
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

# 添加项目根目录到 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def project_root() -> Path:
    """返回项目根目录"""
    return PROJECT_ROOT


@pytest.fixture
def temp_project_dir(tmp_path: Path) -> Path:
    """创建临时项目目录结构"""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()

    # 创建标准目录结构
    for dir_name in ["input", "characters", "images", "videos", "audio", "output"]:
        (project_dir / dir_name).mkdir()

    return project_dir


@pytest.fixture
def sample_novel_text() -> str:
    """示例小说文本"""
    return """
    第一章 初遇

    李明走在繁华的街道上，阳光洒在他的肩头。他是一个普通的大学生，
    今天是他来到这座城市的第一天。

    "你好，请问图书馆怎么走？"一个清脆的声音从身后传来。

    李明转身，看到一个穿着白色连衣裙的女孩，她有着一双明亮的眼睛。

    "往前走，第二个路口左转就到了。"李明回答道。

    "谢谢你！"女孩微笑着说，然后转身离开。

    李明看着她的背影，心中泛起一丝涟漪。
    """


@pytest.fixture
def sample_storyboard() -> dict:
    """示例分镜数据"""
    return {
        "total_scenes": 2,
        "scenes": [
            {
                "id": "scene_01_001",
                "duration": 5.0,
                "visual": {
                    "description": "繁华的城市街道，阳光明媚",
                    "camera": {"type": "slow_zoom_in", "start_frame": "wide_shot", "end_frame": "medium_shot"},
                },
                "audio": {
                    "narration": {"text": "李明走在繁华的街道上", "emotion": "narrative"},
                    "dialogues": [],
                },
                "generation_status": {"image": "pending", "video": "pending", "audio": "pending"},
            },
            {
                "id": "scene_01_002",
                "duration": 4.0,
                "visual": {
                    "description": "女孩穿着白色连衣裙，明亮的眼睛",
                    "camera": {"type": "static", "start_frame": "close_up", "end_frame": "close_up"},
                },
                "audio": {
                    "narration": None,
                    "dialogues": [
                        {"character_id": "girl_01", "text": "你好，请问图书馆怎么走？", "emotion": "friendly"}
                    ],
                },
                "generation_status": {"image": "pending", "video": "pending", "audio": "pending"},
            },
        ],
    }


@pytest.fixture
def sample_characters() -> dict:
    """示例角色数据"""
    return {
        "characters": [
            {
                "id": "li_ming",
                "name": "李明",
                "appearance": {
                    "gender": "male",
                    "age": "young adult",
                    "description": "普通大学生，穿着休闲",
                },
                "voice": {"voice_id": "male_gentle", "pitch": 1.0, "speed": 1.0},
            },
            {
                "id": "girl_01",
                "name": "女孩",
                "appearance": {
                    "gender": "female",
                    "age": "young adult",
                    "description": "穿着白色连衣裙，明亮的眼睛",
                },
                "voice": {"voice_id": "female_gentle", "pitch": 1.0, "speed": 1.0},
            },
        ]
    }


@pytest.fixture
def mock_config() -> MagicMock:
    """模拟配置对象"""
    config = MagicMock()
    config.local.ollama_url = "http://localhost:11434"
    config.local.ollama_model = "glm4:9b"
    config.local.comfyui_url = "http://localhost:8188"
    config.local.cosyvoice_url = "http://localhost:9880"
    config.api.video_provider = "jimeng"
    config.api.video_api_key = "test_key"
    config.api.use_idle_time = True
    config.video.resolution = "1280x720"
    config.video.fps = 24
    config.video.style = "anime"
    config.generation.max_concurrent_tasks = 3
    config.generation.retry_count = 3
    config.paths.projects_dir = "data/projects"
    return config
