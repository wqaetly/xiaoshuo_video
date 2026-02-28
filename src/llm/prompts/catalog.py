"""
Prompt 目录管理

定义所有可用的 Prompt 模板及其元数据。
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class PromptCategory(str, Enum):
    """Prompt 分类"""
    STORYBOARD = "storyboard"      # 分镜相关
    CHARACTER = "character"        # 角色相关
    SCENE = "scene"               # 场景相关
    IMAGE = "image"               # 图像生成
    VIDEO = "video"               # 视频生成
    VOICE = "voice"               # 语音相关
    GENERAL = "general"           # 通用


@dataclass
class PromptEntry:
    """Prompt 条目
    
    记录单个 prompt 的元数据。
    """
    id: str                              # 唯一标识
    category: PromptCategory             # 分类
    path_stem: str                       # 文件路径（不含语言后缀和扩展名）
    variable_keys: List[str]             # 必需变量列表
    optional_keys: List[str] = field(default_factory=list)  # 可选变量
    description: str = ""                # 描述
    version: str = "1.0"                 # 版本
    
    def get_path(self, lang: str = "zh") -> str:
        """获取指定语言的文件路径"""
        return f"{self.path_stem}.{lang}.txt"


class PromptCatalog:
    """Prompt 目录
    
    管理所有 Prompt 模板的注册和查询。
    """
    
    # 预定义的 Prompt 目录
    ENTRIES: Dict[str, PromptEntry] = {
        # ===== 分镜相关 =====
        "storyboard_plan": PromptEntry(
            id="storyboard_plan",
            category=PromptCategory.STORYBOARD,
            path_stem="storyboard/plan",
            variable_keys=["chapter_text", "characters_json"],
            optional_keys=["chapter_num", "style_hints"],
            description="分镜规划 - 将文本拆解为连续镜头",
        ),
        "storyboard_detail": PromptEntry(
            id="storyboard_detail",
            category=PromptCategory.STORYBOARD,
            path_stem="storyboard/detail",
            variable_keys=["panels_json", "characters_json", "locations_json"],
            description="分镜细化 - 添加摄影和灯光细节",
        ),
        "cinematographer": PromptEntry(
            id="cinematographer",
            category=PromptCategory.STORYBOARD,
            path_stem="storyboard/cinematographer",
            variable_keys=["panels_json", "characters_info"],
            optional_keys=["locations_description"],
            description="摄影指导 - 设计灯光、景深、色调",
        ),
        
        "storyboard_edit": PromptEntry(
            id="storyboard_edit",
            category=PromptCategory.STORYBOARD,
            path_stem="storyboard/edit",
            variable_keys=["scene_data", "original_prompt", "user_instruction"],
            description="分镜编辑 - 根据用户指令修改单个镜头",
        ),

        # ===== 角色相关 =====
        "character_extract": PromptEntry(
            id="character_extract",
            category=PromptCategory.CHARACTER,
            path_stem="character/extract",
            variable_keys=["novel_text"],
            description="角色提取 - 从小说中提取角色信息",
        ),
        "character_visual": PromptEntry(
            id="character_visual",
            category=PromptCategory.CHARACTER,
            path_stem="character/visual",
            variable_keys=["character_profiles"],
            description="角色视觉设计 - 生成角色外观描述",
        ),
        "character_reference_to_sheet": PromptEntry(
            id="character_reference_to_sheet",
            category=PromptCategory.CHARACTER,
            path_stem="character/reference_to_sheet",
            variable_keys=["character_info"],
            description="参考图转角色设定图 - 基于参考图生成标准角色立绘",
        ),
        
        # ===== 场景相关 =====
        "scene_regenerate": PromptEntry(
            id="scene_regenerate",
            category=PromptCategory.SCENE,
            path_stem="scene/regenerate",
            variable_keys=["scene_json", "characters_json", "feedback"],
            description="场景重新生成 - 根据反馈修改场景",
        ),
        
        # ===== 图像生成 =====
        "image_prompt": PromptEntry(
            id="image_prompt",
            category=PromptCategory.IMAGE,
            path_stem="image/prompt_generate",
            variable_keys=["scene_description", "characters_in_scene"],
            optional_keys=["style", "aspect_ratio"],
            description="生成图像 Prompt",
        ),
        "image_prompt_modify": PromptEntry(
            id="image_prompt_modify",
            category=PromptCategory.IMAGE,
            path_stem="image/prompt_modify",
            variable_keys=["prompt_input", "video_prompt_input", "user_instruction"],
            description="图像/视频提示词修改 - 根据用户指令修改提示词",
        ),
        "image_single_panel": PromptEntry(
            id="image_single_panel",
            category=PromptCategory.IMAGE,
            path_stem="image/single_panel",
            variable_keys=["scene_data", "source_text", "style"],
            optional_keys=["aspect_ratio", "character_references", "location_references"],
            description="单镜头图像生成 - 专业分镜画师风格",
        ),
        
        # ===== 语音相关 =====
        "voice_analysis": PromptEntry(
            id="voice_analysis",
            category=PromptCategory.VOICE,
            path_stem="voice/analysis",
            variable_keys=["storyboard_json", "characters_json"],
            description="语音分析 - 确定每个角色的声音特征",
        ),
    }
    
    @classmethod
    def get(cls, prompt_id: str) -> Optional[PromptEntry]:
        """获取 Prompt 条目"""
        return cls.ENTRIES.get(prompt_id)
    
    @classmethod
    def list_by_category(cls, category: PromptCategory) -> List[PromptEntry]:
        """按分类列出 Prompt"""
        return [e for e in cls.ENTRIES.values() if e.category == category]
    
    @classmethod
    def list_all(cls) -> List[PromptEntry]:
        """列出所有 Prompt"""
        return list(cls.ENTRIES.values())
    
    @classmethod
    def register(cls, entry: PromptEntry) -> None:
        """注册新的 Prompt"""
        cls.ENTRIES[entry.id] = entry

