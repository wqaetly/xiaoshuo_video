"""LLM模块"""
from .client import OllamaClient
from .storyboard_generator import StoryboardGenerator
from .character_extractor import CharacterExtractor
from .json_parser import (
    parse_json_safe,
    parse_json_array,
    parse_json_with_schema,
    repair_json,
    extract_json_from_text,
    StreamingJSONParser,
)
from .prompt_manager import (
    PromptManager,
    PromptTemplate,
    get_prompt_manager,
    get_prompt,
    get_prompt_with_fallback,
)
from .chapter_splitter import (
    ChapterSplitter,
    ContextWindowManager,
    Chapter,
    TextChunk,
    ChapterFormat,
    split_chapters,
    chunk_for_llm,
)

__all__ = [
    "OllamaClient",
    "StoryboardGenerator",
    "CharacterExtractor",
    "parse_json_safe",
    "parse_json_array",
    "parse_json_with_schema",
    "repair_json",
    "extract_json_from_text",
    "StreamingJSONParser",
    "PromptManager",
    "PromptTemplate",
    "get_prompt_manager",
    "get_prompt",
    "get_prompt_with_fallback",
    "ChapterSplitter",
    "ContextWindowManager",
    "Chapter",
    "TextChunk",
    "ChapterFormat",
    "split_chapters",
    "chunk_for_llm",
]
