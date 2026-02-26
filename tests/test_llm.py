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

        client = OllamaClient(base_url="http://localhost:11434", model="glm4:9b")
        assert client.base_url == "http://localhost:11434"
        assert client.model == "glm4:9b"

    @patch("src.llm.client.requests.Session")
    def test_check_health_success(self, mock_session_class):
        """测试健康检查成功"""
        from src.llm.client import OllamaClient

        mock_session = MagicMock()
        mock_session.get.return_value.status_code = 200
        mock_session_class.return_value = mock_session

        client = OllamaClient()
        assert client.check_health() is True
        mock_session.get.assert_called_once()

    @patch("src.llm.client.requests.Session")
    def test_check_health_failure(self, mock_session_class):
        """测试健康检查失败"""
        from src.llm.client import OllamaClient

        mock_session = MagicMock()
        mock_session.get.side_effect = Exception("Connection refused")
        mock_session_class.return_value = mock_session

        client = OllamaClient()
        assert client.check_health() is False


class TestStoryboardGenerator:
    """分镜生成器测试"""

    def test_generator_initialization(self):
        """测试生成器初始化"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        generator = StoryboardGenerator(mock_llm)
        assert generator.llm == mock_llm

    def test_generator_with_custom_params(self):
        """测试自定义参数初始化"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        generator = StoryboardGenerator(
            mock_llm,
            max_context_tokens=4000,
            context_overlap_tokens=200,
            custom_chapter_patterns=[r"第\d+回"]
        )
        assert generator.context_manager.max_tokens == 4000
        assert generator.context_manager.overlap_tokens == 200

    @patch("src.llm.storyboard_generator.get_prompt_with_fallback")
    def test_generate_single_scene_success(self, mock_get_prompt):
        """测试单场景生成成功"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        # 模拟LLM.chat()返回有效的场景JSON（注意是chat方法不是generate）
        mock_llm.chat.return_value = '''```json
{
    "done": false,
    "scene": {
        "visual": {"description": "古典庭院，阳光明媚"},
        "subtitle": {"text": "这是一个美丽的早晨"},
        "audio": {"description": "鸟鸣声"},
        "duration": 5
    },
    "covered_text": "清晨的阳光"
}
```'''
        mock_get_prompt.return_value = "test prompt"

        generator = StoryboardGenerator(mock_llm)
        result = generator._generate_single_scene(
            chapter_text="清晨的阳光洒在庭院中",
            chapter_num=1,
            characters={"characters": []},
            scene_index=1,
            previous_scenes_summary="无",
            text_hint="清晨的阳光"
        )

        assert result is not None
        assert "scene" in result
        assert result["scene"]["visual"]["description"] == "古典庭院，阳光明媚"

    @patch("src.llm.storyboard_generator.get_prompt_with_fallback")
    def test_generate_single_scene_done(self, mock_get_prompt):
        """测试单场景生成完成标记"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        mock_llm.chat.return_value = '{"done": true}'
        mock_get_prompt.return_value = "test prompt"

        generator = StoryboardGenerator(mock_llm)
        result = generator._generate_single_scene(
            chapter_text="短文本",
            chapter_num=1,
            characters={"characters": []},
            scene_index=5,
            previous_scenes_summary="之前场景",
            text_hint=""
        )

        assert result is not None
        assert result.get("done") is True

    def test_build_scenes_summary_empty(self):
        """测试空场景摘要构建"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        generator = StoryboardGenerator(mock_llm)

        summary = generator._build_scenes_summary([])
        assert summary == "无"

    def test_build_scenes_summary_with_scenes(self):
        """测试有场景时的摘要构建"""
        from src.llm.storyboard_generator import StoryboardGenerator

        mock_llm = MagicMock()
        generator = StoryboardGenerator(mock_llm)

        scenes = [
            {
                "sequence": 1,
                "visual": {"description": "场景一描述"},
                "subtitle": {"text": "对话一"}
            },
            {
                "sequence": 2,
                "visual": {"description": "场景二描述"},
                "subtitle": {"text": "对话二"}
            }
        ]

        summary = generator._build_scenes_summary(scenes)
        assert "场景1" in summary
        assert "场景2" in summary
        assert "场景一描述" in summary


class TestCharacterExtractor:
    """角色提取器测试"""

    def test_extractor_initialization(self):
        """测试提取器初始化"""
        from src.llm.character_extractor import CharacterExtractor

        mock_llm = MagicMock()
        extractor = CharacterExtractor(mock_llm)
        assert extractor.llm == mock_llm


class TestJsonParser:
    """JSON 解析器测试"""

    def test_extract_json_from_text(self):
        """测试从文本中提取JSON字符串"""
        from src.llm.json_parser import extract_json_from_text

        text = '''
        这是一些说明文字
        ```json
        {"key": "value", "number": 42}
        ```
        更多文字
        '''
        result = extract_json_from_text(text)
        # extract_json_from_text 返回的是字符串
        assert result is not None
        assert "key" in result
        assert "value" in result

    def test_extract_json_no_code_block(self):
        """测试没有代码块时直接解析"""
        from src.llm.json_parser import extract_json_from_text

        text = '{"simple": "json"}'
        result = extract_json_from_text(text)
        assert result is not None
        assert "simple" in result

    def test_extract_json_invalid_returns_none(self):
        """测试无效JSON返回None"""
        from src.llm.json_parser import extract_json_from_text

        text = "This is not JSON at all"
        result = extract_json_from_text(text)
        assert result is None

    def test_parse_json_safe(self):
        """测试安全JSON解析"""
        from src.llm.json_parser import parse_json_safe

        json_str = '{"key": "value", "number": 42}'
        result = parse_json_safe(json_str)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_safe_with_invalid(self):
        """测试安全JSON解析处理无效输入"""
        from src.llm.json_parser import parse_json_safe

        result = parse_json_safe("not json")
        assert result is None


class TestChapterSplitter:
    """章节分割器测试"""

    def test_splitter_initialization(self):
        """测试分割器初始化"""
        from src.llm.chapter_splitter import ChapterSplitter

        splitter = ChapterSplitter()
        assert splitter.min_chapter_length == 500
        assert splitter.max_chapter_length == 20000

    def test_splitter_custom_params(self):
        """测试自定义参数"""
        from src.llm.chapter_splitter import ChapterSplitter

        splitter = ChapterSplitter(
            min_chapter_length=100,
            max_chapter_length=5000,
            custom_patterns=[r"第\d+回"]
        )
        assert splitter.min_chapter_length == 100
        assert splitter.max_chapter_length == 5000

    def test_split_no_chapters(self):
        """测试无章节标记的文本"""
        from src.llm.chapter_splitter import ChapterSplitter

        splitter = ChapterSplitter(min_chapter_length=50)
        text = "这是一段没有章节标记的短文本。" * 20
        chapters = splitter.split(text)

        assert len(chapters) >= 1
        assert chapters[0].index == 1

    def test_split_with_chinese_chapters(self):
        """测试中文章节标记"""
        from src.llm.chapter_splitter import ChapterSplitter

        splitter = ChapterSplitter(min_chapter_length=10)
        text = """第一章 开始
这是第一章的内容，描述了故事的开端。

第二章 发展
这是第二章的内容，故事开始发展。

第三章 结局
这是第三章的内容，故事迎来结局。"""

        chapters = splitter.split(text)
        assert len(chapters) >= 2

    def test_chapter_word_count(self):
        """测试章节字数统计"""
        from src.llm.chapter_splitter import Chapter, ChapterFormat

        chapter = Chapter(
            index=1,
            title="测试章节",
            content="这是一段中文文本，包含English words。",
            format_type=ChapterFormat.NO_CHAPTER
        )

        # 应该包含中文字符和英文单词
        assert chapter.word_count > 0
        assert chapter.length == len(chapter.content)


class TestContextWindowManager:
    """上下文窗口管理器测试"""

    def test_manager_initialization(self):
        """测试管理器初始化"""
        from src.llm.chapter_splitter import ContextWindowManager

        manager = ContextWindowManager(max_tokens=4000, overlap_tokens=200)
        assert manager.max_tokens == 4000
        assert manager.overlap_tokens == 200

    def test_needs_chunking_short_text(self):
        """测试短文本不需要分块"""
        from src.llm.chapter_splitter import ContextWindowManager

        manager = ContextWindowManager(max_tokens=8000)
        short_text = "这是一段短文本。" * 10

        assert manager.needs_chunking(short_text) is False

    def test_needs_chunking_long_text(self):
        """测试长文本需要分块"""
        from src.llm.chapter_splitter import ContextWindowManager

        manager = ContextWindowManager(max_tokens=100)  # 很小的窗口
        long_text = "这是一段很长的文本。" * 100

        assert manager.needs_chunking(long_text) is True

    def test_estimate_tokens(self):
        """测试token估算"""
        from src.llm.chapter_splitter import ContextWindowManager

        manager = ContextWindowManager(chars_per_token=1.5)
        text = "这是测试文本" * 10  # 60个字符

        estimated = manager.estimate_tokens(text)
        assert estimated == int(60 / 1.5)  # 40 tokens

    def test_chunk_text(self):
        """测试文本分块"""
        from src.llm.chapter_splitter import ContextWindowManager

        manager = ContextWindowManager(max_tokens=50, overlap_tokens=10)
        long_text = "这是一段需要分块的长文本。" * 20

        chunks = manager.chunk_text(long_text, chapter_index=1)

        assert len(chunks) >= 1
        assert chunks[0].chapter_index == 1
        assert chunks[0].index == 1

    def test_create_context_prompt(self):
        """测试上下文提示创建"""
        from src.llm.chapter_splitter import ContextWindowManager, TextChunk

        manager = ContextWindowManager()
        chunk = TextChunk(
            index=2,
            content="当前块的内容",
            chapter_index=1,
            is_continuation=True
        )

        prompt = manager.create_context_prompt(chunk, "上一块的摘要")

        assert "当前块的内容" in prompt
        assert "上一块的摘要" in prompt
