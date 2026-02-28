"""
Prompt 模板类

增强版模板，支持变量验证和多语言。
"""
import re
from pathlib import Path
from typing import Set, Dict, Any, Optional, List
from dataclasses import dataclass

from ...utils.logger import get_logger
from ...utils.file_utils import read_text

logger = get_logger(__name__)


@dataclass
class TemplateVariable:
    """模板变量"""
    name: str
    required: bool = True
    default: Optional[str] = None


class PromptTemplate:
    """增强型 Prompt 模板
    
    特性:
    - 自动提取变量
    - 变量验证
    - 多语言支持
    - 格式化错误处理
    """
    
    def __init__(
        self,
        template: str,
        name: str = "unnamed",
        required_vars: Optional[List[str]] = None,
        optional_vars: Optional[List[str]] = None,
    ):
        self.template = template
        self.name = name
        self.required_vars = set(required_vars or [])
        self.optional_vars = set(optional_vars or [])
        self._extracted_vars = self._extract_variables()
    
    def _extract_variables(self) -> Set[str]:
        """提取模板中的所有变量"""
        # 匹配 {variable_name} 格式
        pattern = r'\{(\w+)\}'
        return set(re.findall(pattern, self.template))
    
    @property
    def variables(self) -> Set[str]:
        """获取所有变量名"""
        return self._extracted_vars.copy()
    
    def validate(self, **kwargs) -> tuple[bool, List[str]]:
        """验证提供的变量是否完整
        
        Returns:
            (is_valid, missing_vars)
        """
        provided = set(kwargs.keys())
        
        # 检查必需变量
        if self.required_vars:
            missing = self.required_vars - provided
        else:
            # 如果未指定必需变量，则所有提取的变量都是必需的
            missing = self._extracted_vars - provided
        
        return len(missing) == 0, list(missing)
    
    def format(self, **kwargs) -> str:
        """格式化模板
        
        Args:
            **kwargs: 变量值
            
        Returns:
            格式化后的字符串
            
        Raises:
            ValueError: 缺少必需变量
        """
        is_valid, missing = self.validate(**kwargs)
        if not is_valid:
            raise ValueError(f"模板 '{self.name}' 缺少必需变量: {missing}")
        
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        
        return result
    
    def safe_format(self, **kwargs) -> str:
        """安全格式化模板
        
        未提供的变量保留原样，不抛出异常。
        """
        result = self.template
        for key, value in kwargs.items():
            result = result.replace(f"{{{key}}}", str(value))
        return result
    
    @classmethod
    def from_file(
        cls,
        path: Path,
        name: Optional[str] = None,
        required_vars: Optional[List[str]] = None,
        optional_vars: Optional[List[str]] = None,
    ) -> "PromptTemplate":
        """从文件加载模板"""
        if not path.exists():
            raise FileNotFoundError(f"模板文件不存在: {path}")
        
        template_text = read_text(path)
        template_name = name or path.stem
        
        return cls(
            template=template_text,
            name=template_name,
            required_vars=required_vars,
            optional_vars=optional_vars,
        )
    
    @classmethod
    def from_string(
        cls,
        template: str,
        name: str = "inline",
        required_vars: Optional[List[str]] = None,
    ) -> "PromptTemplate":
        """从字符串创建模板"""
        return cls(
            template=template,
            name=name,
            required_vars=required_vars,
        )

