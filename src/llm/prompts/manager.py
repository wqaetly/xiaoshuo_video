"""
增强型 Prompt 管理器

支持目录结构、多语言、变量验证。
"""
from pathlib import Path
from typing import Dict, Optional, List

from .catalog import PromptCatalog, PromptEntry, PromptCategory
from .template import PromptTemplate
from .validator import validate_variables
from ...utils.logger import get_logger
from ...utils.file_utils import read_text

logger = get_logger(__name__)

# 默认配置目录
DEFAULT_PROMPTS_DIR = Path(__file__).parent.parent.parent.parent / "config" / "prompts"


class EnhancedPromptManager:
    """增强型 Prompt 管理器
    
    特性:
    - 按目录分类加载
    - 多语言支持 (zh/en)
    - 变量验证
    - 回退机制
    """
    
    def __init__(
        self,
        prompts_dir: Optional[Path] = None,
        default_lang: str = "zh",
    ):
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self.default_lang = default_lang
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {}  # {id: {lang: template}}
        self._load_templates()
    
    def _load_templates(self) -> None:
        """加载所有模板"""
        if not self.prompts_dir.exists():
            logger.warning(f"Prompt 目录不存在: {self.prompts_dir}")
            return
        
        # 加载目录中的所有 .txt 文件
        for txt_file in self.prompts_dir.rglob("*.txt"):
            self._load_template_file(txt_file)
        
        logger.info(f"已加载 {len(self._templates)} 个 Prompt 模板")
    
    def _load_template_file(self, file_path: Path) -> None:
        """加载单个模板文件"""
        try:
            # 解析文件名: name.lang.txt 或 name.txt
            stem = file_path.stem  # e.g., "plan.zh" or "plan"
            parts = stem.rsplit(".", 1)
            
            if len(parts) == 2 and parts[1] in ("zh", "en"):
                name = parts[0]
                lang = parts[1]
            else:
                name = stem
                lang = self.default_lang
            
            # 获取相对路径作为 ID 的一部分
            rel_path = file_path.relative_to(self.prompts_dir).parent
            if str(rel_path) != ".":
                template_id = f"{rel_path}/{name}".replace("\\", "/")
            else:
                template_id = name
            
            # 查找目录条目获取变量信息
            entry = PromptCatalog.get(template_id.replace("/", "_"))
            required_vars = entry.variable_keys if entry else None
            optional_vars = entry.optional_keys if entry else None
            
            # 加载模板
            template = PromptTemplate.from_file(
                file_path,
                name=template_id,
                required_vars=required_vars,
                optional_vars=optional_vars,
            )
            
            # 存储
            if template_id not in self._templates:
                self._templates[template_id] = {}
            self._templates[template_id][lang] = template
            
            logger.debug(f"加载模板: {template_id} [{lang}]")
            
        except Exception as e:
            logger.error(f"加载模板失败 {file_path}: {e}")
    
    def get(
        self,
        prompt_id: str,
        lang: Optional[str] = None,
    ) -> Optional[PromptTemplate]:
        """获取模板"""
        lang = lang or self.default_lang
        templates = self._templates.get(prompt_id)
        
        if templates is None:
            return None
        
        # 优先返回指定语言，回退到默认语言
        if lang in templates:
            return templates[lang]
        elif self.default_lang in templates:
            return templates[self.default_lang]
        else:
            # 返回任意可用的
            return next(iter(templates.values()), None)
    
    def format(
        self,
        prompt_id: str,
        lang: Optional[str] = None,
        validate: bool = True,
        **kwargs
    ) -> Optional[str]:
        """格式化指定模板"""
        template = self.get(prompt_id, lang)
        if template is None:
            logger.error(f"模板不存在: {prompt_id}")
            return None
        
        try:
            return template.format(**kwargs)
        except ValueError as e:
            logger.error(f"格式化模板失败: {e}")
            return None
    
    def list_templates(self, category: Optional[PromptCategory] = None) -> List[str]:
        """列出所有模板 ID"""
        if category:
            entries = PromptCatalog.list_by_category(category)
            return [e.id for e in entries]
        return list(self._templates.keys())
    
    def reload(self) -> None:
        """重新加载所有模板"""
        self._templates.clear()
        self._load_templates()


# 单例
_prompt_manager: Optional[EnhancedPromptManager] = None


def get_prompt_manager() -> EnhancedPromptManager:
    """获取 Prompt 管理器单例"""
    global _prompt_manager
    if _prompt_manager is None:
        _prompt_manager = EnhancedPromptManager()
    return _prompt_manager

