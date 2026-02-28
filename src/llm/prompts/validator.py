"""
Prompt 变量验证器

确保模板变量与调用时传入的变量一致。
"""
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass

from .catalog import PromptCatalog, PromptEntry
from ...utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    missing_required: List[str]
    extra_unused: List[str]
    warnings: List[str]


def validate_variables(
    prompt_id: str,
    provided_vars: Dict[str, Any],
    strict: bool = False,
) -> ValidationResult:
    """验证提供的变量是否满足 Prompt 要求
    
    Args:
        prompt_id: Prompt ID
        provided_vars: 提供的变量字典
        strict: 是否严格模式（报告未使用的变量）
        
    Returns:
        ValidationResult
    """
    entry = PromptCatalog.get(prompt_id)
    if entry is None:
        return ValidationResult(
            is_valid=False,
            missing_required=[],
            extra_unused=[],
            warnings=[f"未知的 Prompt ID: {prompt_id}"]
        )
    
    provided_keys = set(provided_vars.keys())
    required_keys = set(entry.variable_keys)
    optional_keys = set(entry.optional_keys)
    all_expected = required_keys | optional_keys
    
    # 检查缺少的必需变量
    missing = required_keys - provided_keys
    
    # 检查多余的变量
    extra = provided_keys - all_expected if strict else []
    
    # 生成警告
    warnings = []
    if extra:
        warnings.append(f"提供了未使用的变量: {list(extra)}")
    
    is_valid = len(missing) == 0
    
    if not is_valid:
        logger.warning(f"Prompt '{prompt_id}' 变量验证失败: 缺少 {list(missing)}")
    
    return ValidationResult(
        is_valid=is_valid,
        missing_required=list(missing),
        extra_unused=list(extra),
        warnings=warnings
    )


def check_template_variables(
    template_content: str,
    expected_vars: List[str],
) -> ValidationResult:
    """检查模板内容中的变量是否与预期一致
    
    用于验证模板文件是否正确。
    """
    import re
    
    # 提取模板中的变量
    pattern = r'\{(\w+)\}'
    found_vars = set(re.findall(pattern, template_content))
    expected_set = set(expected_vars)
    
    # 模板中有但预期中没有的变量
    extra_in_template = found_vars - expected_set
    # 预期中有但模板中没有的变量
    missing_in_template = expected_set - found_vars
    
    warnings = []
    if extra_in_template:
        warnings.append(f"模板中有未记录的变量: {list(extra_in_template)}")
    if missing_in_template:
        warnings.append(f"模板中缺少预期变量: {list(missing_in_template)}")
    
    return ValidationResult(
        is_valid=len(missing_in_template) == 0,
        missing_required=list(missing_in_template),
        extra_unused=list(extra_in_template),
        warnings=warnings
    )

