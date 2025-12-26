"""
测试工具函数模块
"""
import json
import tempfile
from pathlib import Path

import pytest


class TestFileUtils:
    """文件工具函数测试"""

    def test_ensure_dir_creates_directory(self, tmp_path: Path):
        """测试目录创建"""
        from src.utils.file_utils import ensure_dir

        new_dir = tmp_path / "new_folder" / "nested"
        ensure_dir(new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ensure_dir_existing_directory(self, tmp_path: Path):
        """测试已存在目录不报错"""
        from src.utils.file_utils import ensure_dir

        existing_dir = tmp_path / "existing"
        existing_dir.mkdir()

        # 不应抛出异常
        ensure_dir(existing_dir)
        assert existing_dir.exists()

    def test_load_json_valid_file(self, tmp_path: Path):
        """测试加载有效JSON文件"""
        from src.utils.file_utils import load_json

        data = {"key": "value", "number": 42}
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")

        result = load_json(json_file)
        assert result == data

    def test_load_json_nonexistent_file(self, tmp_path: Path):
        """测试加载不存在的文件抛出异常"""
        from src.utils.file_utils import load_json

        with pytest.raises(FileNotFoundError):
            load_json(tmp_path / "nonexistent.json")

    def test_save_json_creates_file(self, tmp_path: Path):
        """测试保存JSON文件"""
        from src.utils.file_utils import save_json

        data = {"test": "data", "list": [1, 2, 3]}
        json_file = tmp_path / "output.json"

        save_json(json_file, data)

        assert json_file.exists()
        loaded = json.loads(json_file.read_text(encoding="utf-8"))
        assert loaded == data

    def test_load_yaml_valid_file(self, tmp_path: Path):
        """测试加载YAML文件"""
        from src.utils.file_utils import load_yaml

        yaml_content = """
app:
  name: test
  version: 1.0
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        result = load_yaml(yaml_file)
        assert result["app"]["name"] == "test"
        assert result["app"]["version"] == 1.0


class TestConfig:
    """配置模块测试"""

    def test_get_config_returns_config_object(self):
        """测试获取配置对象"""
        from src.utils.config import get_config

        config = get_config()
        assert config is not None
        assert hasattr(config, "local")
        assert hasattr(config, "api")
        assert hasattr(config, "video")

    def test_config_has_default_values(self):
        """测试配置有默认值"""
        from src.utils.config import get_config

        config = get_config()
        assert config.local.ollama_url is not None
        assert config.video.fps > 0


class TestLogger:
    """日志模块测试"""

    def test_get_logger_returns_logger(self):
        """测试获取日志器"""
        from src.utils.logger import get_logger

        logger = get_logger("test_module")
        assert logger is not None

    def test_logger_can_log_messages(self, capsys):
        """测试日志器可以记录消息"""
        from src.utils.logger import get_logger

        logger = get_logger("test_log")
        logger.info("Test message")
        # loguru 默认输出到 stderr
        # 这里主要测试不抛出异常
