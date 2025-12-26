"""提示词模板管理器"""
import re
from pathlib import Path
from typing import Dict, Any, Optional
from ..utils.logger import get_logger
from ..utils.file_utils import read_text

logger = get_logger(__name__)

# 默认配置目录
DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent / "config" / "prompts"


class PromptTemplate:
    """提示词模板"""
    
    def __init__(self, template: str, name: str = "unnamed"):
        self.template = template
        self.name = name
        self._variables = self._extract_variables()
    
    def _extract_variables(self) -> set:
        """提取模板中的变量"""
        pattern = r'\{(\w+)\}'
        return set(re.findall(pattern, self.template))
    
    @property
    def variables(self) -> set:
        """获取所有变量名"""
        return self._variables.copy()
    
    def format(self, **kwargs) -> str:
        """格式化模板"""
        missing = self._variables - set(kwargs.keys())
        if missing:
            logger.warning(f"模板 {self.name} 缺少变量: {missing}")
        
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    def safe_format(self, **kwargs) -> str:
        """安全格式化模板，未提供的变量保留原样"""
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    @classmethod
    def from_file(cls, path: Path, name: Optional[str] = None) -> "PromptTemplate":
        """从文件加载模板"""
        template_text = read_text(path)
        template_name = name or path.stem
        return cls(template=template_text, name=template_name)


class PromptManager:
    """提示词模板管理器"""
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载所有模板"""
        if not self.prompts_dir.exists():
            logger.warning(f"提示词目录不存在: {self.prompts_dir}")
            return
        
        for file_path in self.prompts_dir.glob("*.txt"):
            try:
                template = PromptTemplate.from_file(file_path)
                self._templates[template.name] = template
                logger.debug(f"加载提示词模板: {template.name}")
            except Exception as e:
                logger.error(f"加载模板失败 {file_path}: {e}")
    
    def get(self, name: str) -> Optional[PromptTemplate]:
        """获取模板"""
        return self._templates.get(name)
    
    def format(self, name: str, **kwargs) -> Optional[str]:
        """格式化指定模板"""
        template = self.get(name)
        if template is None:
            logger.error(f"模板不存在: {name}")
            return None
        return template.format(**kwargs)
    
    def register(self, name: str, template: str) -> PromptTemplate:
        """注册新模板"""
        prompt_template = PromptTemplate(template=template, name=name)
        self._templates[name] = prompt_template
        return prompt_template
    
    def list_templates(self) -> list:
        """列出所有模板名"""
        return list(self._templates.keys())
    
    def reload(self) -> None:
        """重新加载所有模板"""
        self._templates.clear()
        self._load_templates()


_prompt_manager: Optional[PromptManager] = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = PromptManager()
    return _prompt_manager


def get_prompt(name: str, **kwargs) -> Optional[str]:
    """便捷方法：获取并格式化提示词"""
    return get_prompt_manager().format(name, **kwargs)


# 内置提示词模板 (作为后备)
BUILTIN_PROMPTS = {
    "generate_storyboard": """你是专业的动画分镜师。请将以下小说章节转换为分镜脚本。

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
- 确保生成的场景能够连贯地讲述故事""",

    "extract_characters": """你是一个专业的小说分析师。请分析以下小说片段，提取所有主要角色信息。

小说内容:
{novel_text}

请以JSON数组格式输出，每个角色包含:
- id: 唯一标识 (格式: char_001, char_002, ...)
- name: 角色姓名
- aliases: 别名/称呼列表 (如 "他", "主角", "少年" 等)
- appearance: 外貌描述对象
  - gender: 性别 (male/female)
  - age: 大致年龄
  - hair: 发型发色描述
  - eyes: 眼睛特征
  - clothing: 典型服装描述
  - features: 其他显著特征
- personality: 性格特点描述
- sd_prompt: 用于Stable Diffusion的英文外貌提示词
- sd_negative: Stable Diffusion负面提示词

注意:
1. 只提取有明确描述的主要角色
2. 如果某些信息不明确，可以根据上下文合理推断
3. sd_prompt应该是高质量的英文提示词，包含外貌、服装等细节
4. 确保JSON格式正确，可以被解析

输出格式:
```json
[
  {{
    "id": "char_001",
    "name": "角色名",
    "aliases": ["别名1", "别名2"],
    "appearance": {{
      "gender": "male",
      "age": "25",
      "hair": "黑色短发",
      "eyes": "剑眉星目",
      "clothing": "白色长袍",
      "features": "身材修长"
    }},
    "personality": "正直勇敢",
    "sd_prompt": "1boy, black short hair, sharp eyebrows, wearing white hanfu robe, handsome",
    "sd_negative": "ugly, deformed, bad anatomy, bad hands"
  }}
]
```""",

    "regenerate_scene": """请根据以下反馈修改场景分镜:

原场景:
{scene_json}

角色信息:
{characters_json}

修改要求:
{feedback}

请输出修改后的完整场景JSON (保持相同格式):
```json
{{...}}
```"""
}


def get_builtin_prompt(name: str, **kwargs) -> Optional[str]:
    """获取内置提示词"""
    template = BUILTIN_PROMPTS.get(name)
    if template is None:
        return None
    
    result = template
    for key, value in kwargs.items():
        result = result.replace(f"{{{key}}}", str(value))
    
    return result


def get_prompt_with_fallback(name: str, **kwargs) -> str:
    """获取提示词，如果文件不存在则使用内置模板"""
    result = get_prompt(name, **kwargs)
    if result:
        return result
    
    builtin = get_builtin_prompt(name, **kwargs)
    if builtin:
        logger.info(f"使用内置提示词模板: {name}")
        return builtin
    
    raise ValueError(f"提示词模板不存在: {name}")
