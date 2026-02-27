"""分镜生成 Agent

基于 Tool-Calling 模式的智能分镜生成器，替代原有的线性 StoryboardGenerator。
实现 Reasoning -> Tool Call -> Observation -> Act 循环。
"""
import json
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from .base import BaseAgent, AgentTool, AgentToolkit, AgentContext
from ..client import OllamaClient
from ..chapter_splitter import ChapterSplitter, Chapter
from ..json_parser import parse_json_safe, extract_json_from_text
from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class StoryboardAgentState:
    """分镜 Agent 专用状态"""
    novel_text: str = ""
    characters: Dict[str, Any] = field(default_factory=dict)
    chapters: List[Chapter] = field(default_factory=list)
    scenes: List[Dict[str, Any]] = field(default_factory=list)
    current_chapter: int = 0
    scene_counter: int = 0


class StoryboardAgent(BaseAgent[Dict[str, Any]]):
    """分镜生成 Agent
    
    工具列表:
    - split_chapters: 将小说分割为章节
    - lookup_character: 查询角色信息
    - analyze_scene_count: 分析章节应生成的场景数量
    - generate_scene: 生成单个场景分镜
    - validate_scene: 验证场景数据完整性
    - finalize_storyboard: 完成分镜生成
    """
    
    def __init__(
        self,
        llm_client: OllamaClient,
        max_context_tokens: int = 8000
    ):
        self.chapter_splitter = ChapterSplitter()
        self.max_context_tokens = max_context_tokens
        self._state = StoryboardAgentState()
        super().__init__(llm_client, max_iterations=100)
    
    def generate(
        self,
        novel_text: str,
        characters: Dict[str, Any],
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        """生成完整的分镜脚本 (兼容原 StoryboardGenerator 接口)"""
        self._state = StoryboardAgentState(
            novel_text=novel_text,
            characters=characters
        )
        
        # 构建用户输入
        user_input = self._build_task_prompt(novel_text, characters, title)
        
        # 执行 Agent 循环
        result = self.run(user_input)
        
        return result
    
    def _build_task_prompt(
        self, 
        novel_text: str, 
        characters: Dict[str, Any],
        title: Optional[str] = None
    ) -> str:
        """构建任务提示词"""
        char_names = [c["name"] for c in characters.get("characters", [])]
        
        return f"""请将以下小说转换为分镜脚本。

小说标题: {title or "未命名小说"}
小说长度: {len(novel_text)} 字
角色列表: {', '.join(char_names) if char_names else '待提取'}

任务要求:
1. 首先使用 split_chapters 工具将小说分割为章节
2. 对每个章节使用 analyze_scene_count 分析应生成的场景数量
3. 逐个使用 generate_scene 工具生成每个场景的分镜
4. 使用 validate_scene 验证生成的场景数据
5. 最后使用 finalize_storyboard 完成整合

小说内容 (前 3000 字):
{novel_text[:3000]}

请开始执行任务，使用工具完成分镜生成。"""
    
    def _setup_tools(self) -> None:
        """注册分镜生成相关工具"""
        
        # 工具 1: 章节分割
        self.toolkit.register(AgentTool(
            name="split_chapters",
            description="将小说文本分割为章节列表",
            parameters={
                "type": "object",
                "properties": {},
                "required": []
            },
            func=self._tool_split_chapters
        ))
        
        # 工具 2: 角色查询
        self.toolkit.register(AgentTool(
            name="lookup_character",
            description="根据角色名称或ID查询角色详细信息",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "角色名称、ID或别名"
                    }
                },
                "required": ["query"]
            },
            func=self._tool_lookup_character
        ))
        
        # 工具 3: 场景数量分析
        self.toolkit.register(AgentTool(
            name="analyze_scene_count",
            description="分析指定章节应该生成多少个场景",
            parameters={
                "type": "object",
                "properties": {
                    "chapter_index": {
                        "type": "integer",
                        "description": "章节索引 (从0开始)"
                    }
                },
                "required": ["chapter_index"]
            },
            func=self._tool_analyze_scene_count
        ))
        
        # 工具 4: 生成单个场景
        self.toolkit.register(AgentTool(
            name="generate_scene",
            description="为指定章节生成一个场景分镜",
            parameters={
                "type": "object",
                "properties": {
                    "chapter_index": {"type": "integer", "description": "章节索引"},
                    "scene_index": {"type": "integer", "description": "场景在章节内的序号"},
                    "text_hint": {"type": "string", "description": "该场景对应的原文片段"},
                    "previous_summary": {"type": "string", "description": "前几个场景的摘要"}
                },
                "required": ["chapter_index", "scene_index"]
            },
            func=self._tool_generate_scene
        ))

        # 工具 5: 验证场景
        self.toolkit.register(AgentTool(
            name="validate_scene",
            description="验证场景数据的完整性和正确性",
            parameters={
                "type": "object",
                "properties": {
                    "scene_id": {"type": "string", "description": "场景ID"}
                },
                "required": ["scene_id"]
            },
            func=self._tool_validate_scene
        ))

        # 工具 6: 完成分镜
        self.toolkit.register(AgentTool(
            name="finalize_storyboard",
            description="完成分镜生成，整合所有场景数据",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "小说标题"}
                },
                "required": []
            },
            func=self._tool_finalize_storyboard
        ))

    # ========== 工具实现 ==========

    def _tool_split_chapters(self) -> Dict[str, Any]:
        """工具: 分割章节"""
        chapters = self.chapter_splitter.split(self._state.novel_text)
        self._state.chapters = chapters

        return {
            "success": True,
            "total_chapters": len(chapters),
            "chapters": [
                {
                    "index": c.index,
                    "title": c.title,
                    "word_count": c.word_count
                }
                for c in chapters
            ]
        }

    def _tool_lookup_character(self, query: str) -> Dict[str, Any]:
        """工具: 查询角色信息"""
        characters = self._state.characters.get("characters", [])
        query_lower = query.lower()

        for char in characters:
            # 匹配 ID
            if char.get("id", "").lower() == query_lower:
                return {"found": True, "character": char}
            # 匹配名称
            if char.get("name", "").lower() == query_lower:
                return {"found": True, "character": char}
            # 匹配别名
            aliases = [a.lower() for a in char.get("aliases", [])]
            if query_lower in aliases:
                return {"found": True, "character": char}

        return {"found": False, "message": f"未找到角色: {query}"}

    def _tool_analyze_scene_count(self, chapter_index: int) -> Dict[str, Any]:
        """工具: 分析场景数量"""
        if chapter_index >= len(self._state.chapters):
            return {"error": f"章节索引越界: {chapter_index}"}

        chapter = self._state.chapters[chapter_index]
        word_count = chapter.word_count

        # 基于文本长度估算场景数
        # 约每 200-300 字一个场景
        estimated = max(3, min(20, word_count // 250))

        return {
            "chapter_index": chapter_index,
            "chapter_title": chapter.title,
            "word_count": word_count,
            "recommended_scenes": estimated,
            "min_scenes": max(2, estimated - 2),
            "max_scenes": estimated + 3
        }

    def _tool_generate_scene(
        self,
        chapter_index: int,
        scene_index: int,
        text_hint: str = "",
        previous_summary: str = ""
    ) -> Dict[str, Any]:
        """工具: 生成单个场景分镜"""
        if chapter_index >= len(self._state.chapters):
            return {"error": f"章节索引越界: {chapter_index}"}

        chapter = self._state.chapters[chapter_index]
        characters_json = json.dumps(
            self._state.characters.get("characters", []),
            ensure_ascii=False, indent=2
        )

        # 构建提示词
        prompt = f"""你是专业的动画分镜师。请为以下章节生成第 {scene_index} 个分镜场景。

章节内容 (第{chapter_index + 1}章 - {chapter.title}):
{chapter.content[:2000]}

角色信息:
{characters_json}

前几个场景摘要:
{previous_summary or "（这是第一个场景）"}

文本提示: {text_hint[:200] if text_hint else "章节开始"}

要求:
1. 时长控制在3-6秒
2. 画面描述要详细，包含人物、场景、光影、氛围
3. 镜头类型: static, slow_zoom_in, slow_zoom_out, pan_left, pan_right
4. 画面类型: wide_shot, medium_shot, close_up

直接输出JSON:
```json
{{
  "duration": 5.0,
  "visual": {{
    "description": "详细画面描述",
    "style_tags": ["标签1"],
    "characters_in_scene": ["char_001"],
    "camera": {{"type": "static", "start_frame": "medium_shot", "end_frame": "medium_shot"}}
  }},
  "audio": {{
    "narration": {{"text": "旁白", "emotion": "calm"}},
    "dialogues": [],
    "bgm": "ambient",
    "sfx": []
  }},
  "subtitle": {{"text": "字幕", "style": "narration", "character": null}},
  "covered_text": "该场景覆盖的原文片段"
}}
```"""

        try:
            response = self.llm.chat(prompt=prompt, temperature=0.5, max_tokens=2048)
            result = extract_json_from_text(response)

            if result:
                scene_data = parse_json_safe(result, default=None)
                if scene_data:
                    # 分配场景ID
                    self._state.scene_counter += 1
                    scene_id = f"scene_{chapter_index + 1:02d}_{scene_index:03d}"

                    scene = {
                        "id": scene_id,
                        "chapter": chapter_index + 1,
                        "sequence": scene_index,
                        "global_index": self._state.scene_counter,
                        "generation_status": {
                            "image": "pending",
                            "video": "pending",
                            "audio": "pending"
                        },
                        **scene_data
                    }

                    self._state.scenes.append(scene)

                    return {
                        "success": True,
                        "scene_id": scene_id,
                        "scene": scene,
                        "total_scenes_generated": len(self._state.scenes)
                    }

            return {"error": "场景生成失败，无法解析LLM响应"}

        except Exception as e:
            logger.error(f"生成场景失败: {e}")
            return {"error": str(e)}

    def _tool_validate_scene(self, scene_id: str) -> Dict[str, Any]:
        """工具: 验证场景数据完整性"""
        scene = None
        for s in self._state.scenes:
            if s.get("id") == scene_id:
                scene = s
                break

        if not scene:
            return {"valid": False, "error": f"场景不存在: {scene_id}"}

        issues = []

        # 检查必要字段
        if "duration" not in scene:
            issues.append("缺少duration字段")
        elif not (3.0 <= scene["duration"] <= 6.0):
            issues.append(f"duration超出范围: {scene['duration']}")

        visual = scene.get("visual", {})
        if not visual.get("description"):
            issues.append("缺少画面描述")
        if not visual.get("camera"):
            issues.append("缺少镜头信息")

        if not scene.get("subtitle", {}).get("text"):
            issues.append("缺少字幕")

        return {
            "scene_id": scene_id,
            "valid": len(issues) == 0,
            "issues": issues,
            "scene_summary": {
                "duration": scene.get("duration"),
                "has_visual": bool(visual.get("description")),
                "has_audio": bool(scene.get("audio")),
                "has_subtitle": bool(scene.get("subtitle", {}).get("text"))
            }
        }

    def _tool_finalize_storyboard(self, title: str = "") -> Dict[str, Any]:
        """工具: 完成分镜生成，整合所有场景"""
        if not self._state.scenes:
            return {"error": "没有生成任何场景"}

        storyboard = {
            "novel_title": title or "未命名小说",
            "total_scenes": len(self._state.scenes),
            "total_chapters": len(self._state.chapters),
            "characters": self._state.characters.get("characters", []),
            "scenes": self._state.scenes
        }

        return {
            "success": True,
            "message": "TASK_COMPLETE",  # 触发 Agent 完成
            "storyboard": storyboard
        }

    # ========== BaseAgent 抽象方法实现 ==========

    def _get_system_prompt(self) -> str:
        """获取系统提示词"""
        tools_schema = self.toolkit.get_tools_schema()

        return f"""你是一个专业的动画分镜生成Agent。你的任务是将小说文本转换为详细的分镜脚本。

你可以使用以下工具来完成任务：
{tools_schema}

工具调用格式：
<tool_call>{{"name": "工具名称", "arguments": {{"参数1": "值1"}}}}</tool_call>

工作流程：
1. 使用 split_chapters 分割小说章节
2. 对每个章节使用 analyze_scene_count 确定场景数量
3. 逐个使用 generate_scene 生成分镜
4. 可选使用 validate_scene 验证场景
5. 最后使用 finalize_storyboard 完成整合

当所有场景生成完毕后，调用 finalize_storyboard 工具完成任务。

重要规则：
- 每次只调用一个工具
- 等待工具结果后再决定下一步
- 按顺序处理每个章节的每个场景
- 完成后必须调用 finalize_storyboard"""

    def _parse_final_result(self, context: AgentContext[Dict[str, Any]]) -> Dict[str, Any]:
        """解析最终结果"""
        # 从消息历史中查找 finalize_storyboard 的结果
        for msg in reversed(context.messages):
            if msg.tool_name == "finalize_storyboard" and msg.tool_result:
                result = msg.tool_result
                if isinstance(result, dict) and "storyboard" in result:
                    return result["storyboard"]

        # 如果没找到，直接返回当前状态的场景
        if self._state.scenes:
            return {
                "novel_title": "未命名小说",
                "total_scenes": len(self._state.scenes),
                "total_chapters": len(self._state.chapters),
                "characters": self._state.characters.get("characters", []),
                "scenes": self._state.scenes
            }

        return {"error": "未能生成分镜", "scenes": []}
