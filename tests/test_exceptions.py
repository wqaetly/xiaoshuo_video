"""
测试自定义异常类
"""
import pytest

from src.exceptions import (
    XiaoshuoVideoError,
    ServiceUnavailableError,
    ServiceTimeoutError,
    APIError,
    APIRateLimitError,
    GenerationError,
    ImageGenerationError,
    VideoGenerationError,
    ProjectNotFoundError,
    InvalidInputError,
    JSONParseError,
    MissingConfigError,
)


class TestBaseException:
    """基础异常测试"""

    def test_basic_exception(self):
        """测试基础异常"""
        exc = XiaoshuoVideoError("测试错误")
        assert str(exc) == "测试错误"
        assert exc.message == "测试错误"
        assert exc.details is None

    def test_exception_with_details(self):
        """测试带详情的异常"""
        exc = XiaoshuoVideoError("测试错误", details="详细信息")
        assert str(exc) == "测试错误: 详细信息"
        assert exc.details == "详细信息"


class TestServiceExceptions:
    """服务异常测试"""

    def test_service_unavailable(self):
        """测试服务不可用异常"""
        exc = ServiceUnavailableError("Ollama", "http://localhost:11434")
        assert "Ollama" in str(exc)
        assert "http://localhost:11434" in str(exc)
        assert exc.service_name == "Ollama"
        assert exc.url == "http://localhost:11434"

    def test_service_timeout(self):
        """测试服务超时异常"""
        exc = ServiceTimeoutError("ComfyUI", 30.0)
        assert "ComfyUI" in str(exc)
        assert "30" in str(exc)
        assert exc.timeout == 30.0

    def test_api_error(self):
        """测试API错误"""
        exc = APIError("jimeng", status_code=500, details="服务器错误")
        assert "jimeng" in str(exc)
        assert exc.status_code == 500

    def test_api_rate_limit(self):
        """测试API速率限制"""
        exc = APIRateLimitError("kling", retry_after=60)
        assert exc.status_code == 429
        assert exc.retry_after == 60


class TestGenerationExceptions:
    """生成异常测试"""

    def test_image_generation_error(self):
        """测试图像生成错误"""
        exc = ImageGenerationError("scene_01_001", details="显存不足")
        assert "scene_01_001" in str(exc)
        assert exc.scene_id == "scene_01_001"

    def test_video_generation_error(self):
        """测试视频生成错误"""
        exc = VideoGenerationError("scene_01_002", "jimeng", details="API调用失败")
        assert "scene_01_002" in str(exc)
        assert "jimeng" in str(exc)


class TestDataExceptions:
    """数据异常测试"""

    def test_invalid_input(self):
        """测试无效输入"""
        exc = InvalidInputError("duration", "正数", got="-5")
        assert "duration" in str(exc)
        assert exc.field == "duration"

    def test_json_parse_error(self):
        """测试JSON解析错误"""
        exc = JSONParseError("LLM输出", details="无法找到JSON块")
        assert "JSON" in str(exc)
        assert exc.source == "LLM输出"


class TestProjectExceptions:
    """项目异常测试"""

    def test_project_not_found(self):
        """测试项目不存在"""
        exc = ProjectNotFoundError("my_project")
        assert "my_project" in str(exc)
        assert exc.project_name == "my_project"


class TestConfigExceptions:
    """配置异常测试"""

    def test_missing_config(self):
        """测试缺少配置"""
        exc = MissingConfigError("api.video_api_key", config_file=".env")
        assert "api.video_api_key" in str(exc)
        assert ".env" in str(exc)
