"""
增强型 Prompt 模板系统

借鉴 waoowaoo 项目设计:
- 目录分类 (storyboard/character/scene 等)
- 多语言支持 (zh/en)
- 变量验证
- Prompt 目录
"""

from .catalog import PromptCatalog, PromptEntry
from .manager import EnhancedPromptManager, get_prompt_manager
from .template import PromptTemplate
from .validator import validate_variables

__all__ = [
    "PromptCatalog",
    "PromptEntry",
    "EnhancedPromptManager",
    "get_prompt_manager",
    "PromptTemplate",
    "validate_variables",
]

