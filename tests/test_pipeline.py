"""
测试 Pipeline 状态管理
"""
import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

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


class TestStateConcurrency:
    """状态文件并发访问测试"""

    def test_state_save_with_lock(self, tmp_path: Path):
        """测试带锁的状态保存"""
        from src.pipeline.state import PipelineState, Phase

        state = PipelineState()
        state.current_phase = Phase.GENERATE_IMAGES
        state.total_scenes = 5
        state.mark_scene_completed("scene_01", "image")

        state_file = tmp_path / "state.json"
        state.save(state_file)

        # 验证锁文件是否被正确释放（文件可读）
        loaded = PipelineState.load(state_file)
        assert loaded.current_phase == Phase.GENERATE_IMAGES
        assert loaded.is_scene_completed("scene_01", "image")

    def test_concurrent_state_access(self, tmp_path: Path):
        """测试并发状态访问不会损坏文件"""
        from src.pipeline.state import PipelineState, Phase

        state_file = tmp_path / "state.json"
        errors = []

        # 初始化状态
        initial_state = PipelineState()
        initial_state.total_scenes = 100
        initial_state.save(state_file)

        def writer(thread_id: int):
            """写入线程"""
            try:
                for i in range(10):
                    state = PipelineState.load(state_file)
                    state.mark_scene_completed(f"scene_{thread_id}_{i}", "image")
                    state.save(state_file)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        # 启动多个写入线程
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有错误发生
        assert len(errors) == 0, f"并发错误: {errors}"

        # 验证状态文件完整性
        final_state = PipelineState.load(state_file)
        assert final_state.total_scenes == 100


class TestStopException:
    """停止异常测试"""

    def test_stop_requested_exception(self):
        """测试 StopRequestedException"""
        from src.exceptions import StopRequestedException

        exc = StopRequestedException("用户请求停止")
        assert str(exc) == "用户请求停止"
        assert isinstance(exc, Exception)

    def test_stop_requested_exception_default_message(self):
        """测试默认停止消息"""
        from src.exceptions import StopRequestedException

        exc = StopRequestedException()
        # 默认消息是 "任务被用户中断"
        assert "中断" in str(exc) or "用户" in str(exc)


class TestVideoAPIQuota:
    """视频 API 配额检查测试"""

    def test_quota_check_sufficient(self):
        """测试配额充足"""
        from src.video.api_client import VideoAPIClient

        # 创建一个模拟客户端
        class MockClient(VideoAPIClient):
            def generate(self, image_path, motion_prompt, duration=5.0):
                pass

            def check_status(self, task_id):
                return {}

            def get_quota(self):
                return {"available": 100, "used": 50, "total": 150, "unit": "credits"}

        client = MockClient(api_key="test_key")
        is_sufficient, msg = client.check_quota_sufficient(10)

        assert is_sufficient is True
        assert "充足" in msg

    def test_quota_check_insufficient(self):
        """测试配额不足"""
        from src.video.api_client import VideoAPIClient

        class MockClient(VideoAPIClient):
            def generate(self, image_path, motion_prompt, duration=5.0):
                pass

            def check_status(self, task_id):
                return {}

            def get_quota(self):
                return {"available": 5, "used": 95, "total": 100, "unit": "credits"}

        client = MockClient(api_key="test_key")
        is_sufficient, msg = client.check_quota_sufficient(10)

        assert is_sufficient is False
        assert "不足" in msg

    def test_quota_check_no_data(self):
        """测试无法获取配额信息时的处理"""
        from src.video.api_client import VideoAPIClient

        class MockClient(VideoAPIClient):
            def generate(self, image_path, motion_prompt, duration=5.0):
                pass

            def check_status(self, task_id):
                return {}

            def get_quota(self):
                return {}  # 无法获取配额

        client = MockClient(api_key="test_key")
        is_sufficient, msg = client.check_quota_sufficient(10)

        # 无法获取时应假设足够并继续
        assert is_sufficient is True
        assert "无法获取" in msg


class TestGPUMonitor:
    """GPU 监控测试"""

    @patch("src.utils.gpu_monitor.pynvml")
    def test_gpu_monitor_initialization(self, mock_pynvml):
        """测试 GPU 监控初始化"""
        from src.utils.gpu_monitor import GPUMonitor

        mock_pynvml.nvmlInit.return_value = None
        mock_pynvml.nvmlDeviceGetCount.return_value = 1

        monitor = GPUMonitor()
        assert monitor is not None

    def test_calculate_optimal_workers(self):
        """测试计算最优工作线程数"""
        from src.utils.gpu_monitor import GPUMonitor

        # 测试无 GPU 时的回退行为
        monitor = GPUMonitor()
        workers = monitor.calculate_optimal_workers(
            max_workers=8,
            memory_per_task_mb=2048  # 2GB per task
        )

        # 应该返回一个有效的工作线程数
        assert 1 <= workers <= 8

    def test_gpu_monitor_no_nvidia(self):
        """测试没有 NVIDIA GPU 时的处理"""
        from src.utils.gpu_monitor import GPUMonitor

        with patch("src.utils.gpu_monitor.pynvml") as mock_pynvml:
            mock_pynvml.nvmlInit.side_effect = Exception("NVML not available")

            monitor = GPUMonitor()
            # 应该返回默认值而不是崩溃
            workers = monitor.calculate_optimal_workers(max_workers=4)
            assert workers >= 1
