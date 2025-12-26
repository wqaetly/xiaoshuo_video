"""
测试 Pipeline 状态管理
"""
import json
from pathlib import Path

import pytest


class TestPipelineState:
    """Pipeline 状态测试"""

    def test_state_initialization(self):
        """测试状态初始化"""
        from src.pipeline.state import PipelineState, Phase

        state = PipelineState()
        assert state.current_phase == Phase.INIT
        assert state.total_scenes == 0
        assert state.current_scene_index == 0

    def test_mark_scene_completed(self):
        """测试标记场景完成"""
        from src.pipeline.state import PipelineState

        state = PipelineState()
        state.mark_scene_completed("scene_01", "image")

        assert state.is_scene_completed("scene_01", "image")
        assert not state.is_scene_completed("scene_01", "video")
        assert not state.is_scene_completed("scene_02", "image")

    def test_add_error(self):
        """测试添加错误记录"""
        from src.pipeline.state import PipelineState

        state = PipelineState()
        state.add_error("generate_images", "scene_01", "Test error message")

        assert len(state.errors) == 1
        assert state.errors[0]["phase"] == "generate_images"
        assert state.errors[0]["scene_id"] == "scene_01"
        assert state.errors[0]["message"] == "Test error message"

    def test_state_save_and_load(self, tmp_path: Path):
        """测试状态保存和加载"""
        from src.pipeline.state import PipelineState, Phase

        state = PipelineState()
        state.current_phase = Phase.GENERATE_IMAGES
        state.total_scenes = 10
        state.mark_scene_completed("scene_01", "image")
        state.add_error("test", "scene_02", "error")

        state_file = tmp_path / "state.json"
        state.save(state_file)

        loaded_state = PipelineState.load(state_file)
        assert loaded_state.current_phase == Phase.GENERATE_IMAGES
        assert loaded_state.total_scenes == 10
        assert loaded_state.is_scene_completed("scene_01", "image")
        assert len(loaded_state.errors) == 1

    def test_get_progress(self):
        """测试获取进度"""
        from src.pipeline.state import PipelineState

        state = PipelineState()
        state.total_scenes = 5
        state.mark_scene_completed("scene_01", "image")
        state.mark_scene_completed("scene_02", "image")
        state.add_error("test", "scene_03", "error")

        progress = state.get_progress()
        assert progress["total_scenes"] == 5
        assert progress["error_count"] == 1


class TestPhaseEnum:
    """Phase 枚举测试"""

    def test_phase_values(self):
        """测试阶段枚举值"""
        from src.pipeline.state import Phase

        assert Phase.INIT.value == "init"
        assert Phase.ANALYZE.value == "analyze"
        assert Phase.GENERATE_IMAGES.value == "generate_images"
        assert Phase.DONE.value == "done"

    def test_phase_ordering(self):
        """测试阶段顺序"""
        from src.pipeline.state import Phase

        phases = list(Phase)
        assert phases.index(Phase.INIT) < phases.index(Phase.ANALYZE)
        assert phases.index(Phase.ANALYZE) < phases.index(Phase.GENERATE_IMAGES)
        assert phases.index(Phase.COMPOSE) < phases.index(Phase.DONE)
