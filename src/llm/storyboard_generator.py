"""分镜脚本生成器"""
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from .client import OllamaClient
from .json_parser import parse_json_safe, parse_json_array, repair_json, extract_json_from_text
from .prompt_manager import get_prompt_with_fallback
from .chapter_splitter import ChapterSplitter, ContextWindowManager, Chapter
from ..utils.logger import get_logger

logger = get_logger(__name__)


class StoryboardGenerator:
    """分镜脚本生成器"""

    def __init__(
        self,
        llm_client: OllamaClient,
        max_context_tokens: int = 8000,
        context_overlap_tokens: int = 500,
        custom_chapter_patterns: Optional[List[str]] = None
    ):
        self.llm = llm_client
        # 章节分割器
        self.chapter_splitter = ChapterSplitter(
            custom_patterns=custom_chapter_patterns
        )
        # 上下文窗口管理器
        self.context_manager = ContextWindowManager(
            max_tokens=max_context_tokens,
            overlap_tokens=context_overlap_tokens
        )

    def generate(
        self,
        novel_text: str,
        characters: Dict[str, Any],
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成完整的分镜脚本"""
        # 使用智能章节分割器
        chapters = self.chapter_splitter.split(novel_text)
        logger.info(f"小说分割为 {len(chapters)} 个章节")

        all_scenes = []
        scene_counter = 0

        for chapter in chapters:
            chapter_num = chapter.index
            logger.info(f"正在生成第 {chapter_num} 章分镜: {chapter.title} ({chapter.word_count} 字)")

            # 检查是否需要分块处理长章节
            if self.context_manager.needs_chunking(chapter.content):
                scenes = self._generate_chunked_chapter_scenes(
                    chapter=chapter,
                    characters=characters
                )
            else:
                scenes = self._generate_chapter_scenes(
                    chapter_text=chapter.content,
                    chapter_num=chapter_num,
                    characters=characters
                )

            # 添加全局ID
            for scene in scenes:
                scene_counter += 1
                scene["id"] = f"scene_{chapter_num:02d}_{scene['sequence']:03d}"
                scene["global_index"] = scene_counter

            all_scenes.extend(scenes)
            logger.info(f"第 {chapter_num} 章生成 {len(scenes)} 个场景")

        # 构建完整分镜数据
        storyboard = {
            "novel_title": title or self._extract_title(novel_text),
            "total_scenes": len(all_scenes),
            "total_chapters": len(chapters),
            "characters": characters.get("characters", []),
            "scenes": all_scenes
        }

        return storyboard

    def _generate_chunked_chapter_scenes(
        self,
        chapter: Chapter,
        characters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """分块处理长章节生成分镜"""
        chunks = self.context_manager.chunk_text(chapter.content, chapter.index)
        logger.info(f"章节 {chapter.index} 分为 {len(chunks)} 块处理")
        
        all_scenes = []
        previous_summary = None
        
        for chunk in chunks:
            # 构建带上下文的提示
            context_text = self.context_manager.create_context_prompt(
                chunk, previous_summary
            )
            
            # 生成该块的分镜
            scenes = self._generate_chapter_scenes(
                chapter_text=context_text,
                chapter_num=chapter.index,
                characters=characters
            )
            
            all_scenes.extend(scenes)
            
            # 为下一块生成摘要
            if len(scenes) > 0 and chunk.index < len(chunks):
                previous_summary = self._generate_chunk_summary(scenes)
        
        # 重新排序场景序号
        for i, scene in enumerate(all_scenes):
            scene["sequence"] = i + 1
        
        return all_scenes
    
    def _generate_chunk_summary(self, scenes: List[Dict[str, Any]]) -> str:
        """生成分块的摘要，用于下一块的上下文"""
        summaries = []
        for scene in scenes[-3:]:  # 只取最后3个场景
            visual = scene.get("visual", {})
            desc = visual.get("description", "")
            if desc:
                summaries.append(desc[:100])
        return "；".join(summaries) if summaries else ""

    def _generate_chapter_scenes(
        self,
        chapter_text: str,
        chapter_num: int,
        characters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """为单个章节生成分镜"""
        max_chars = 8000
        if len(chapter_text) > max_chars:
            chapter_text = chapter_text[:max_chars] + "..."

        prompt = get_prompt_with_fallback(
            "generate_storyboard",
            chapter_num=chapter_num,
            chapter_text=chapter_text,
            characters_json=json.dumps(
                characters.get("characters", []),
                ensure_ascii=False,
                indent=2
            )
        )

        response = self.llm.chat(
            prompt=prompt,
            temperature=0.5,
            max_tokens=8192
        )

        scenes = self._parse_scenes_response(response)

        # 添加章节信息和状态
        for i, scene in enumerate(scenes):
            scene["chapter"] = chapter_num
            scene["sequence"] = i + 1
            scene["generation_status"] = {
                "image": "pending",
                "video": "pending",
                "audio": "pending"
            }

        return scenes

    def _parse_scenes_response(self, response: str) -> List[Dict[str, Any]]:
        """解析分镜响应 (使用增强的JSON解析器)"""
        scenes = parse_json_safe(response, default=[])
        
        if not scenes:
            logger.warning("JSON解析返回空列表，尝试备用解析方法")
            scenes = self._fallback_parse(response)
        
        if not isinstance(scenes, list):
            logger.error(f"分镜解析结果不是列表: {type(scenes)}")
            return []
        
        return self._validate_scenes(scenes)

    def _validate_scenes(self, scenes: List[Dict]) -> List[Dict]:
        """验证并修复场景数据"""
        validated = []

        for scene in scenes:
            # 确保必要字段
            if "duration" not in scene:
                scene["duration"] = 5.0
            else:
                # 限制时长范围
                scene["duration"] = max(3.0, min(6.0, float(scene["duration"])))

            if "visual" not in scene:
                scene["visual"] = {
                    "description": "场景描述缺失",
                    "style_tags": [],
                    "characters_in_scene": [],
                    "camera": {
                        "type": "static",
                        "start_frame": "medium_shot",
                        "end_frame": "medium_shot"
                    }
                }

            if "audio" not in scene:
                scene["audio"] = {
                    "narration": None,
                    "dialogues": [],
                    "bgm": "ambient",
                    "sfx": []
                }

            if "subtitle" not in scene:
                # 从对话或旁白生成字幕
                scene["subtitle"] = self._generate_subtitle(scene)

            validated.append(scene)

        return validated

    def _generate_subtitle(self, scene: Dict) -> Dict:
        """根据场景音频生成字幕"""
        audio = scene.get("audio", {})

        # 优先使用对话
        dialogues = audio.get("dialogues", [])
        if dialogues:
            first_dialogue = dialogues[0]
            return {
                "text": first_dialogue.get("text", ""),
                "style": "dialogue",
                "character": first_dialogue.get("character_id")
            }

        # 其次使用旁白
        narration = audio.get("narration")
        if narration and narration.get("text"):
            return {
                "text": narration["text"],
                "style": "narration",
                "character": None
            }

        return {
            "text": "",
            "style": "none",
            "character": None
        }

    def _split_chapters(self, text: str) -> List[str]:
        """分割章节"""
        # 匹配常见章节格式
        patterns = [
            r'第[一二三四五六七八九十百千万零\d]+章[^\n]*',
            r'Chapter\s+\d+[^\n]*',
            r'第[一二三四五六七八九十百千万零\d]+节[^\n]*',
        ]

        combined_pattern = '|'.join(f'({p})' for p in patterns)
        parts = re.split(combined_pattern, text)

        # 清理并组合
        chapters = []
        current_chapter = ""

        for part in parts:
            if part is None:
                continue
            part = part.strip()
            if not part:
                continue

            # 检查是否是章节标题
            is_title = any(re.match(p, part) for p in patterns)
            if is_title:
                if current_chapter:
                    chapters.append(current_chapter)
                current_chapter = part + "\n"
            else:
                current_chapter += part + "\n"

        if current_chapter:
            chapters.append(current_chapter)

        # 如果没有找到章节，按段落分割
        if len(chapters) <= 1:
            paragraphs = text.split('\n\n')
            # 每5-10个段落作为一个"章节"
            chunk_size = 7
            chapters = []
            for i in range(0, len(paragraphs), chunk_size):
                chunk = '\n\n'.join(paragraphs[i:i + chunk_size])
                if chunk.strip():
                    chapters.append(chunk)

        return chapters

    def _extract_title(self, text: str) -> str:
        """提取标题"""
        lines = text.strip().split('\n')
        for line in lines[:5]:
            line = line.strip()
            if line and len(line) < 50:
                return line
        return "未命名小说"

    def _fallback_parse(self, response: str) -> List[Dict[str, Any]]:
        """备用解析方法 - 尝试更激进的修复"""
        json_str = extract_json_from_text(response)
        if not json_str:
            return []
        
        repaired = repair_json(json_str)
        
        try:
            result = json.loads(repaired)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            pass
        
        scenes = []
        scene_pattern = r'\{[^{}]*"duration"[^{}]*\}'
        matches = re.findall(scene_pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                scene = json.loads(match)
                scenes.append(scene)
            except:
                continue
        
        return scenes

    def _try_fix_json(self, json_str: str) -> List[Dict]:
        """尝试修复常见JSON错误 (已废弃，使用json_parser模块)"""
        return self._fallback_parse(json_str)

    def regenerate_scene(
        self,
        scene: Dict[str, Any],
        characters: Dict[str, Any],
        feedback: str
    ) -> Dict[str, Any]:
        """根据反馈重新生成单个场景"""
        prompt = f"""请根据以下反馈修改场景分镜:

原场景:
{json.dumps(scene, ensure_ascii=False, indent=2)}

角色信息:
{json.dumps(characters.get("characters", []), ensure_ascii=False, indent=2)}

修改要求:
{feedback}

请输出修改后的完整场景JSON (保持相同格式):
```json
{{...}}
```"""

        response = self.llm.chat(prompt=prompt, temperature=0.3)

        # 解析单个场景
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            try:
                new_scene = json.loads(json_match.group(1))
                # 保留原有ID和状态
                new_scene["id"] = scene.get("id")
                new_scene["chapter"] = scene.get("chapter")
                new_scene["sequence"] = scene.get("sequence")
                new_scene["generation_status"] = scene.get("generation_status", {
                    "image": "pending",
                    "video": "pending",
                    "audio": "pending"
                })
                return new_scene
            except json.JSONDecodeError:
                pass

        return scene  # 返回原场景
