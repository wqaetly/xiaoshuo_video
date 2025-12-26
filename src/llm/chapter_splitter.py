"""章节分割器 - 支持多种格式和上下文窗口管理"""
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ChapterFormat(Enum):
    """章节格式类型"""
    CHINESE_NUMBER = "chinese_number"  # 第一章、第二十章
    ARABIC_NUMBER = "arabic_number"    # 第1章、第23章
    ENGLISH = "english"                # Chapter 1, Chapter 23
    SECTION = "section"                # 第一节、第二节
    VOLUME = "volume"                  # 卷一、上篇
    CUSTOM_MARKER = "custom_marker"    # 自定义分隔符
    NO_CHAPTER = "no_chapter"          # 无章节标记


@dataclass
class Chapter:
    """章节数据结构"""
    index: int
    title: str
    content: str
    start_pos: int = 0
    end_pos: int = 0
    format_type: ChapterFormat = ChapterFormat.NO_CHAPTER
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def length(self) -> int:
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        """估算字数(中文按字符，英文按单词)"""
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', self.content))
        english_words = len(re.findall(r'[a-zA-Z]+', self.content))
        return chinese_chars + english_words


@dataclass
class TextChunk:
    """文本分块数据结构"""
    index: int
    content: str
    chapter_index: int
    is_continuation: bool = False
    overlap_start: int = 0  # 重叠部分开始位置
    metadata: Dict[str, Any] = field(default_factory=dict)


class ChapterSplitter:
    """智能章节分割器"""
    
    # 章节标题模式 (优先级从高到低)
    CHAPTER_PATTERNS = [
        # 中文数字章节 (第一章、第十二章、第一百零八章)
        (r'第[一二三四五六七八九十百千万零]+章\s*[^\n]*', ChapterFormat.CHINESE_NUMBER),
        # 阿拉伯数字章节 (第1章、第123章)
        (r'第\d+章\s*[^\n]*', ChapterFormat.ARABIC_NUMBER),
        # 英文章节 (Chapter 1, CHAPTER 12)
        (r'[Cc][Hh][Aa][Pp][Tt][Ee][Rr]\s+\d+\s*[^\n]*', ChapterFormat.ENGLISH),
        # 中文数字节 (第一节、第十节)
        (r'第[一二三四五六七八九十百千万零]+节\s*[^\n]*', ChapterFormat.SECTION),
        # 卷/篇/部 (卷一、上篇、第一部)
        (r'[卷篇部][一二三四五六七八九十百千万零\d]+\s*[^\n]*', ChapterFormat.VOLUME),
        (r'第[一二三四五六七八九十百千万零\d]+[卷篇部]\s*[^\n]*', ChapterFormat.VOLUME),
        (r'[上中下]篇\s*[^\n]*', ChapterFormat.VOLUME),
        # 数字开头的章节 (1. xxx, 1、xxx, 【1】xxx)
        (r'^\d+[\.、]\s*[^\n]+', ChapterFormat.ARABIC_NUMBER),
        (r'^【\d+】\s*[^\n]+', ChapterFormat.ARABIC_NUMBER),
        # 特殊标记 (序章、楔子、尾声、番外)
        (r'^[序终]章\s*[^\n]*', ChapterFormat.CUSTOM_MARKER),
        (r'^楔子\s*[^\n]*', ChapterFormat.CUSTOM_MARKER),
        (r'^尾声\s*[^\n]*', ChapterFormat.CUSTOM_MARKER),
        (r'^番外\s*[^\n]*', ChapterFormat.CUSTOM_MARKER),
        (r'^[Pp]rologue\s*[^\n]*', ChapterFormat.CUSTOM_MARKER),
        (r'^[Ee]pilogue\s*[^\n]*', ChapterFormat.CUSTOM_MARKER),
    ]
    
    # 段落分隔模式
    PARAGRAPH_SEPARATORS = [
        r'\n\n+',           # 多个换行
        r'\n\s*\n',         # 换行+空白+换行
        r'(?<=[。！？])\s*\n',  # 句号后换行
    ]
    
    def __init__(
        self,
        min_chapter_length: int = 500,
        max_chapter_length: int = 20000,
        fallback_chunk_size: int = 3000,
        custom_patterns: Optional[List[str]] = None
    ):
        """
        初始化章节分割器
        
        Args:
            min_chapter_length: 最小章节长度(字符)
            max_chapter_length: 最大章节长度(字符)
            fallback_chunk_size: 无章节时的默认分块大小
            custom_patterns: 自定义章节模式
        """
        self.min_chapter_length = min_chapter_length
        self.max_chapter_length = max_chapter_length
        self.fallback_chunk_size = fallback_chunk_size
        
        # 添加自定义模式
        self.patterns = list(self.CHAPTER_PATTERNS)
        if custom_patterns:
            for p in custom_patterns:
                self.patterns.insert(0, (p, ChapterFormat.CUSTOM_MARKER))
    
    def split(self, text: str) -> List[Chapter]:
        """
        分割文本为章节
        
        Args:
            text: 原始文本
            
        Returns:
            章节列表
        """
        text = self._preprocess(text)
        
        # 检测章节格式
        detected_format, matches = self._detect_format(text)
        logger.info(f"检测到章节格式: {detected_format.value}, 匹配数: {len(matches)}")
        
        if detected_format == ChapterFormat.NO_CHAPTER or len(matches) < 2:
            # 无明确章节，按段落分块
            logger.info("未检测到明确章节标记，将按段落分块")
            return self._split_by_paragraphs(text)
        
        # 按检测到的格式分割
        chapters = self._split_by_matches(text, matches, detected_format)
        
        # 合并过短章节
        chapters = self._merge_short_chapters(chapters)
        
        # 分割过长章节
        chapters = self._split_long_chapters(chapters)
        
        # 重新编号
        for i, chapter in enumerate(chapters):
            chapter.index = i + 1
        
        logger.info(f"最终分割为 {len(chapters)} 个章节")
        return chapters
    
    def _preprocess(self, text: str) -> str:
        """预处理文本"""
        # 统一换行符
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        # 清理多余空白行
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 清理行首空格(保留段落缩进)
        text = re.sub(r'\n[ \t]+', '\n', text)
        return text.strip()
    
    def _detect_format(self, text: str) -> Tuple[ChapterFormat, List[Tuple[int, int, str]]]:
        """检测文本的章节格式"""
        best_format = ChapterFormat.NO_CHAPTER
        best_matches = []
        
        for pattern, format_type in self.patterns:
            matches = []
            for m in re.finditer(pattern, text, re.MULTILINE):
                matches.append((m.start(), m.end(), m.group()))
            
            # 选择匹配数最多的格式
            if len(matches) > len(best_matches):
                best_matches = matches
                best_format = format_type
        
        # 验证匹配的合理性
        if best_matches:
            # 检查分布是否合理(章节间距不应太小或太大)
            if len(best_matches) >= 2:
                avg_distance = (best_matches[-1][0] - best_matches[0][0]) / (len(best_matches) - 1)
                if avg_distance < self.min_chapter_length / 2:
                    # 匹配太密集，可能是误匹配
                    logger.warning(f"章节标记太密集(平均间距{avg_distance:.0f}字符)，可能为误匹配")
                    # 尝试更严格的过滤
                    best_matches = self._filter_dense_matches(best_matches)
        
        return best_format, best_matches
    
    def _filter_dense_matches(
        self, 
        matches: List[Tuple[int, int, str]]
    ) -> List[Tuple[int, int, str]]:
        """过滤掉过于密集的匹配"""
        if len(matches) < 2:
            return matches
        
        filtered = [matches[0]]
        for match in matches[1:]:
            last_pos = filtered[-1][0]
            if match[0] - last_pos >= self.min_chapter_length:
                filtered.append(match)
        
        return filtered
    
    def _split_by_matches(
        self,
        text: str,
        matches: List[Tuple[int, int, str]],
        format_type: ChapterFormat
    ) -> List[Chapter]:
        """根据匹配结果分割章节"""
        chapters = []
        
        # 处理第一个章节之前的内容(如序言)
        if matches[0][0] > self.min_chapter_length:
            prologue_content = text[:matches[0][0]].strip()
            if prologue_content:
                chapters.append(Chapter(
                    index=0,
                    title="序言",
                    content=prologue_content,
                    start_pos=0,
                    end_pos=matches[0][0],
                    format_type=ChapterFormat.CUSTOM_MARKER
                ))
        
        # 处理各章节
        for i, (start, end, title) in enumerate(matches):
            # 确定章节结束位置
            if i < len(matches) - 1:
                chapter_end = matches[i + 1][0]
            else:
                chapter_end = len(text)
            
            content = text[start:chapter_end].strip()
            title_clean = title.strip()
            
            chapters.append(Chapter(
                index=i + 1,
                title=title_clean,
                content=content,
                start_pos=start,
                end_pos=chapter_end,
                format_type=format_type
            ))
        
        return chapters
    
    def _split_by_paragraphs(self, text: str) -> List[Chapter]:
        """按段落分块(无明确章节时)"""
        # 按多种分隔符分割
        paragraphs = re.split(r'\n\n+', text)
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return [Chapter(
                index=1,
                title="全文",
                content=text,
                format_type=ChapterFormat.NO_CHAPTER
            )]
        
        chapters = []
        current_content = []
        current_length = 0
        
        for para in paragraphs:
            para_len = len(para)
            
            # 检查是否应该开始新章节
            if current_length + para_len > self.fallback_chunk_size and current_content:
                # 保存当前章节
                chapters.append(Chapter(
                    index=len(chapters) + 1,
                    title=f"段落 {len(chapters) + 1}",
                    content='\n\n'.join(current_content),
                    format_type=ChapterFormat.NO_CHAPTER
                ))
                current_content = []
                current_length = 0
            
            current_content.append(para)
            current_length += para_len
        
        # 保存最后一个章节
        if current_content:
            chapters.append(Chapter(
                index=len(chapters) + 1,
                title=f"段落 {len(chapters) + 1}",
                content='\n\n'.join(current_content),
                format_type=ChapterFormat.NO_CHAPTER
            ))
        
        return chapters
    
    def _merge_short_chapters(self, chapters: List[Chapter]) -> List[Chapter]:
        """合并过短的章节"""
        if len(chapters) < 2:
            return chapters
        
        merged = []
        i = 0
        
        while i < len(chapters):
            current = chapters[i]
            
            # 检查是否需要合并
            if current.length < self.min_chapter_length and i < len(chapters) - 1:
                # 与下一章合并
                next_chapter = chapters[i + 1]
                merged_content = current.content + "\n\n" + next_chapter.content
                merged_chapter = Chapter(
                    index=current.index,
                    title=current.title,
                    content=merged_content,
                    start_pos=current.start_pos,
                    end_pos=next_chapter.end_pos,
                    format_type=current.format_type
                )
                merged.append(merged_chapter)
                i += 2
                logger.debug(f"合并章节: {current.title} + {next_chapter.title}")
            else:
                merged.append(current)
                i += 1
        
        return merged
    
    def _split_long_chapters(self, chapters: List[Chapter]) -> List[Chapter]:
        """分割过长的章节"""
        result = []
        
        for chapter in chapters:
            if chapter.length <= self.max_chapter_length:
                result.append(chapter)
            else:
                # 需要分割
                sub_chapters = self._split_chapter_by_scenes(chapter)
                result.extend(sub_chapters)
                logger.debug(f"分割长章节: {chapter.title} -> {len(sub_chapters)} 部分")
        
        return result
    
    def _split_chapter_by_scenes(self, chapter: Chapter) -> List[Chapter]:
        """按场景分割长章节"""
        content = chapter.content
        
        # 尝试按场景分隔符分割
        scene_patterns = [
            r'\n\*\s*\*\s*\*\n',      # * * *
            r'\n---+\n',               # ---
            r'\n===+\n',               # ===
            r'\n…+\n',                 # ……
            r'\n。{3,}\n',             # 。。。
        ]
        
        for pattern in scene_patterns:
            parts = re.split(pattern, content)
            if len(parts) > 1:
                return self._create_sub_chapters(chapter, parts)
        
        # 没有场景分隔符，按句子分割
        return self._split_by_sentences(chapter)
    
    def _create_sub_chapters(
        self, 
        parent: Chapter, 
        parts: List[str]
    ) -> List[Chapter]:
        """创建子章节"""
        sub_chapters = []
        
        for i, part in enumerate(parts):
            part = part.strip()
            if not part:
                continue
            
            sub_chapters.append(Chapter(
                index=parent.index,
                title=f"{parent.title} ({i + 1})",
                content=part,
                format_type=parent.format_type,
                metadata={"parent_chapter": parent.title, "part": i + 1}
            ))
        
        return sub_chapters
    
    def _split_by_sentences(self, chapter: Chapter) -> List[Chapter]:
        """按句子边界分割"""
        content = chapter.content
        target_size = self.max_chapter_length
        
        # 按句子分割
        sentences = re.split(r'([。！？…]+)', content)
        
        sub_chapters = []
        current_content = ""
        part_num = 1
        
        for i in range(0, len(sentences), 2):
            sentence = sentences[i]
            if i + 1 < len(sentences):
                sentence += sentences[i + 1]  # 加上标点
            
            if len(current_content) + len(sentence) > target_size and current_content:
                sub_chapters.append(Chapter(
                    index=chapter.index,
                    title=f"{chapter.title} ({part_num})",
                    content=current_content.strip(),
                    format_type=chapter.format_type,
                    metadata={"parent_chapter": chapter.title, "part": part_num}
                ))
                part_num += 1
                current_content = ""
            
            current_content += sentence
        
        if current_content.strip():
            sub_chapters.append(Chapter(
                index=chapter.index,
                title=f"{chapter.title} ({part_num})" if part_num > 1 else chapter.title,
                content=current_content.strip(),
                format_type=chapter.format_type,
                metadata={"parent_chapter": chapter.title, "part": part_num} if part_num > 1 else {}
            ))
        
        return sub_chapters


class ContextWindowManager:
    """上下文窗口管理器 - 处理长文本分块"""
    
    def __init__(
        self,
        max_tokens: int = 8000,
        overlap_tokens: int = 500,
        chars_per_token: float = 1.5  # 中文约1.5字符/token
    ):
        """
        初始化上下文窗口管理器
        
        Args:
            max_tokens: 最大token数
            overlap_tokens: 重叠token数(确保上下文连贯)
            chars_per_token: 字符/token比例
        """
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.chars_per_token = chars_per_token
        
        # 计算字符限制
        self.max_chars = int(max_tokens * chars_per_token)
        self.overlap_chars = int(overlap_tokens * chars_per_token)
    
    def estimate_tokens(self, text: str) -> int:
        """估算文本的token数"""
        return int(len(text) / self.chars_per_token)
    
    def needs_chunking(self, text: str) -> bool:
        """检查文本是否需要分块"""
        return len(text) > self.max_chars
    
    def chunk_text(
        self,
        text: str,
        chapter_index: int = 1
    ) -> List[TextChunk]:
        """
        将文本分块(带重叠)
        
        Args:
            text: 原始文本
            chapter_index: 所属章节索引
            
        Returns:
            文本块列表
        """
        if not self.needs_chunking(text):
            return [TextChunk(
                index=1,
                content=text,
                chapter_index=chapter_index,
                is_continuation=False
            )]
        
        chunks = []
        start = 0
        chunk_index = 1
        
        while start < len(text):
            # 计算结束位置
            end = start + self.max_chars
            
            if end >= len(text):
                # 最后一块
                chunk_content = text[start:]
            else:
                # 在句子边界截断
                end = self._find_sentence_boundary(text, start, end)
                chunk_content = text[start:end]
            
            # 计算重叠
            overlap_start = 0
            if chunk_index > 1 and start > 0:
                overlap_start = self.overlap_chars
            
            chunks.append(TextChunk(
                index=chunk_index,
                content=chunk_content,
                chapter_index=chapter_index,
                is_continuation=chunk_index > 1,
                overlap_start=overlap_start
            ))
            
            # 下一块的起始位置(减去重叠)
            start = end - self.overlap_chars
            if start < 0:
                start = 0
            
            chunk_index += 1
            
            # 防止无限循环
            if end >= len(text):
                break
        
        logger.info(f"章节 {chapter_index} 分为 {len(chunks)} 个块")
        return chunks
    
    def _find_sentence_boundary(
        self,
        text: str,
        start: int,
        end: int
    ) -> int:
        """找到最近的句子边界"""
        # 在end附近寻找句子结束符
        search_range = min(500, (end - start) // 4)
        search_start = max(start, end - search_range)
        
        # 句子结束符
        sentence_ends = ['。', '！', '？', '…', '.', '!', '?', '\n\n']
        
        best_pos = end
        for sep in sentence_ends:
            pos = text.rfind(sep, search_start, end)
            if pos > search_start and pos < best_pos:
                best_pos = pos + len(sep)
        
        return best_pos
    
    def create_context_prompt(
        self,
        chunk: TextChunk,
        previous_summary: Optional[str] = None
    ) -> str:
        """
        为分块创建带上下文的提示词
        
        Args:
            chunk: 文本块
            previous_summary: 前文摘要
            
        Returns:
            包含上下文的提示词
        """
        context_parts = []
        
        if chunk.is_continuation:
            context_parts.append("【续前文】")
            if previous_summary:
                context_parts.append(f"前文摘要: {previous_summary}")
        
        context_parts.append(f"【第{chunk.chapter_index}章 - 第{chunk.index}部分】")
        context_parts.append(chunk.content)
        
        return '\n\n'.join(context_parts)
    
    def merge_chunk_results(
        self,
        results: List[Any],
        overlap_chars: int = 0
    ) -> List[Any]:
        """
        合并分块处理的结果
        
        Args:
            results: 各块的处理结果列表
            overlap_chars: 需要去除的重叠字符数
            
        Returns:
            合并后的结果
        """
        if not results:
            return []
        
        if len(results) == 1:
            return results[0] if isinstance(results[0], list) else [results[0]]
        
        merged = []
        for i, result in enumerate(results):
            if isinstance(result, list):
                # 去除重叠部分(如果有)
                if i > 0 and overlap_chars > 0:
                    # 假设结果有某种位置信息，需要过滤重叠
                    merged.extend(result)
                else:
                    merged.extend(result)
            else:
                merged.append(result)
        
        return merged


def split_chapters(
    text: str,
    min_length: int = 500,
    max_length: int = 20000,
    custom_patterns: Optional[List[str]] = None
) -> List[Chapter]:
    """
    便捷函数：分割章节
    
    Args:
        text: 小说文本
        min_length: 最小章节长度
        max_length: 最大章节长度
        custom_patterns: 自定义章节模式
        
    Returns:
        章节列表
    """
    splitter = ChapterSplitter(
        min_chapter_length=min_length,
        max_chapter_length=max_length,
        custom_patterns=custom_patterns
    )
    return splitter.split(text)


def chunk_for_llm(
    text: str,
    max_tokens: int = 8000,
    overlap_tokens: int = 500
) -> List[TextChunk]:
    """
    便捷函数：为LLM分块
    
    Args:
        text: 文本
        max_tokens: 最大token数
        overlap_tokens: 重叠token数
        
    Returns:
        文本块列表
    """
    manager = ContextWindowManager(
        max_tokens=max_tokens,
        overlap_tokens=overlap_tokens
    )
    return manager.chunk_text(text)
