"""
分析阶段处理器

负责小说文本分析、角色提取和分镜生成。
"""
from typing import Dict, Any

from .base import BasePhaseHandler
from ..state import Phase
from ...utils.logger import get_logger
from ...utils.file_utils import save_json, load_json

logger = get_logger(__name__)


class AnalyzePhaseHandler(BasePhaseHandler):
    """分析阶段处理器
    
    执行以下任务：
    1. 读取小说文本
    2. 提取角色信息
    3. 生成分镜脚本
    """
    
    phase = Phase.ANALYZE
    phase_name = "分析"
    
    def execute(self) -> None:
        """执行分析阶段"""
        ctx = self.context
        
        self.report_progress("读取小说内容...", 0.0)
        
        novel_path = ctx.project_path / "input" / "novel.txt"
        if not novel_path.exists():
            raise FileNotFoundError(f"小说文件不存在: {novel_path}")
        
        novel_text = novel_path.read_text(encoding="utf-8")
        
        # 提取角色
        self.report_progress("提取角色信息...", 0.2)
        characters = self.controller._character_extractor.extract(novel_text)
        save_json(ctx.project_path / "characters.json", characters)
        
        # 生成分镜
        self.report_progress("生成分镜脚本...", 0.5)
        storyboard = self.controller._storyboard_gen.generate(novel_text, characters)
        save_json(ctx.project_path / "storyboard.json", storyboard)
        
        ctx.state.total_scenes = storyboard["total_scenes"]
        self.controller._save_state()
        
        self.report_progress(
            f"完成: {len(characters['characters'])}个角色, {ctx.state.total_scenes}个场景",
            1.0
        )


class CharacterDesignPhaseHandler(BasePhaseHandler):
    """角色设计阶段处理器
    
    为每个角色生成立绘图像。
    """
    
    phase = Phase.CHARACTER_DESIGN
    phase_name = "角色设计"
    
    def execute(self) -> None:
        """执行角色设计阶段"""
        ctx = self.context
        
        self.report_progress("生成角色立绘...", 0.0)
        
        characters = load_json(ctx.project_path / "characters.json")
        char_list = characters.get("characters", [])
        total = len(char_list)
        
        for i, char in enumerate(char_list):
            # 检查中断
            if ctx.should_stop():
                from ...exceptions import StopRequestedException
                raise StopRequestedException("用户中断")
            
            char_id = char["id"]
            
            # 检查是否已完成
            if ctx.state.is_scene_completed(char_id, "character"):
                continue
            
            self.report_progress(
                f"生成 {char['name']} ({i+1}/{total})",
                i / total
            )
            
            try:
                self.controller._char_designer.generate_character(
                    char,
                    ctx.project_path / "characters"
                )
                ctx.state.mark_scene_completed(char_id, "character")
                self.controller._save_state()
            except Exception as e:
                # 检查是否是中断异常
                if "中断" in str(e) or "stop" in str(e).lower():
                    raise
                logger.error(f"角色 {char_id} 生成失败: {e}")
                ctx.state.add_error("character_design", char_id, str(e))
        
        self.report_progress("角色立绘生成完成", 1.0)

