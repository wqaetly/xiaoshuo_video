"""分镜脚本生成器"""
import json
import re
from typing import List, Dict, Any, Optional
from .client import OllamaClient
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 分镜生成提示词
STORYBOARD_PROMPT = """你是专业的动画分镜师。请将以下小说章节转换为分镜脚本。

小说章节 (第{chapter_num}章):
{chapter_text}

已知角色信息:
{characters_json}

要求:
1. 每个场景时长控制在3-6秒
2. 场景描述要具体、详细，适合AI图像生成
3. 镜头类型选择: static(静止), slow_zoom_in(缓慢推进), slow_zoom_out(缓慢拉远), pan_left(左移), pan_right(右移), tilt_up(上移), tilt_down(下移)
4. 画面类型: wide_shot(远景), medium_shot(中景), close_up(特写), extreme_close_up(大特写)
5. 对话和旁白要自然流畅
6. 情感标记要准确: epic(史诗), calm(平静), tense(紧张), sad(悲伤), happy(欢快), angry(愤怒), determined(坚定)

输出JSON数组格式:
```json
[
  {{
    "duration": 5.0,
    "visual": {{
      "description": "场景的详细视觉描述，包括环境、人物动作、光影等",
      "style_tags": ["风格标签1", "风格标签2"],
      "characters_in_scene": ["char_001"],
      "camera": {{
        "type": "slow_zoom_in",
        "start_frame": "wide_shot",
        "end_frame": "medium_shot"
      }}
    }},
    "audio": {{
      "narration": {{
        "text": "旁白文本（如果有）",
        "emotion": "epic"
      }},
      "dialogues": [
        {{
          "character_id": "char_001",
          "text": "对话内容",
          "emotion": "determined"
        }}
      ],
      "bgm": "epic_intro",
      "sfx": ["wind_mountain"]
    }},
    "subtitle": {{
      "text": "显示的字幕文本",
      "style": "narration",
      "character": null
    }}
  }}
]
```

注意:
- 如果场景没有旁白，narration设为null
- 如果没有对话，dialogues设为空数组[]
- subtitle.style为"narration"或"dialogue"
- 对话时subtitle.character为说话角色名
- 确保生成的场景能够连贯地讲述故事"""


class StoryboardGenerator:
    """分镜脚本生成器"""

    def __init__(self, llm_client: OllamaClient):
        self.llm = llm_client

    def generate(
        self,
        novel_text: str,
        characters: Dict[str, Any],
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成完整的分镜脚本"""
        # 分割章节
        chapters = self._split_chapters(novel_text)
        logger.info(f"小说分割为 {len(chapters)} 个章节")

        all_scenes = []
        scene_counter = 0

        for chapter_idx, chapter_text in enumerate(chapters):
            chapter_num = chapter_idx + 1
            logger.info(f"正在生成第 {chapter_num} 章分镜...")

            scenes = self._generate_chapter_scenes(
                chapter_text=chapter_text,
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

    def _generate_chapter_scenes(
        self,
        chapter_text: str,
        chapter_num: int,
        characters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """为单个章节生成分镜"""
        # 限制章节长度
        max_chars = 8000
        if len(chapter_text) > max_chars:
            chapter_text = chapter_text[:max_chars] + "..."

        prompt = STORYBOARD_PROMPT.format(
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
        """解析分镜响应"""
        # 尝试找到JSON代码块
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', response)
        if json_match:
            json_str = json_match.group(1)
        else:
            # 尝试直接找到数组
            start = response.find('[')
            end = response.rfind(']') + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
            else:
                logger.error(f"无法从响应中提取分镜JSON")
                return []

        try:
            scenes = json.loads(json_str)
            return self._validate_scenes(scenes)
        except json.JSONDecodeError as e:
            logger.error(f"分镜JSON解析失败: {e}")
            # 尝试修复常见JSON错误
            return self._try_fix_json(json_str)

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

    def _try_fix_json(self, json_str: str) -> List[Dict]:
        """尝试修复常见JSON错误"""
        try:
            # 移除可能的注释
            json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
            # 修复尾随逗号
            json_str = re.sub(r',\s*]', ']', json_str)
            json_str = re.sub(r',\s*}', '}', json_str)

            return json.loads(json_str)
        except:
            logger.error("JSON修复失败")
            return []

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
