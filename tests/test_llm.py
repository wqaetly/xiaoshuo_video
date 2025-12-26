"""
测试 LLM 模块
"""
from unittest.mock import MagicMock, patch

import pytest


class TestOllamaClient:
    """Ollama 客户端测试"""

    def test_client_initialization(self):
        """测试客户端初始化"""
        from src.llm.client import OllamaClient

        client = OllamaClient(base_url="http://localhost:11434", model="qwen2.5:14b")
        assert client.base_url == "http://localhost:11434"
        assert client.model == "qwen2.5:14b"

    @patch("src.llm.client.requests.get")
    def test_check_health_success(self, mock_get):
        """测试健康检查成功"""
        from src.llm.client import OllamaClient

        mock_get.return_value.status_code = 200
        client = OllamaClient()

        assert client.check_health() is True
        mock_get.assert_called_once()

    @patch("src.llm.client.requests.get")
    def test_check_health_failure(self, mock_get):
        """测试健康检查失败"""
        from src.llm.client import OllamaClient

        mock_get.side_effect = Exception("Connection refused")
        client = OllamaClient()

        assert client.check_health() is False


class TestStoryboardGenerator:
    """分镜生成器测试"""

    def test_generator_initialization(self):
        """测试生成器初始化"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        generator = StoryboardGenerator(mock_llm)
        assert generator.llm_client == mock_llm


class TestCharacterExtractor:
    """角色提取器测试"""

    def test_extractor_initialization(self):
        """测试提取器初始化"""
        from src.llm.character_extractor import CharacterExtractor

        mock_llm = MagicMock()
        extractor = CharacterExtractor(mock_llm)
        assert extractor.llm_client == mock_llm


class TestJsonParser:
    """JSON 解析器测试"""

    def test_extract_json_from_text(self):
        """测试从文本中提取JSON"""
        from src.llm.json_parser import extract_json_from_text

        text = '''
        这是一些说明文字
        ```json
        {"key": "value", "number": 42}
        ```
        更多文字
        '''
        result = extract_json_from_text(text)
        assert result == {"key": "value", "number": 42}

    def test_extract_json_no_code_block(self):
        """测试没有代码块时直接解析"""
        from src.llm.json_parser import extract_json_from_text

        text = '{"simple": "json"}'
        result = extract_json_from_text(text)
        assert result == {"simple": "json"}

    def test_extract_json_invalid_returns_none(self):
        """测试无效JSON返回None"""
        from src.llm.json_parser import extract_json_from_text

        text = "This is not JSON at all"
        result = extract_json_from_text(text)
        assert result is None

    def test_clean_json_string(self):
        """测试清理JSON字符串"""
        from src.llm.json_parser import clean_json_string

        dirty = '{"key": "value with \n newline"}'
        cleaned = clean_json_string(dirty)
        assert "\n" not in cleaned or "\\n" in cleaned
