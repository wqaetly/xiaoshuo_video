"""JSON解析增强模块 - 处理LLM输出的不完整/格式错误的JSON"""
import json
import re
from typing import Any, Optional, List, Dict, Union, Type, TypeVar
from pydantic import BaseModel, ValidationError
from ..utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound=BaseModel)


class JSONRepairError(Exception):
    """JSON修复失败异常"""
    pass


def extract_json_from_text(text: str) -> Optional[str]:
    """
    从文本中提取JSON字符串
    支持:
    - ```json ... ``` 代码块
    - 直接的JSON数组 [...]
    - 直接的JSON对象 {...}
    """
    text = text.strip()
    
    json_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(json_block_pattern, text)
    if matches:
        for match in matches:
            match = match.strip()
            if match.startswith('[') or match.startswith('{'):
                return match
    
    start_array = text.find('[')
    start_obj = text.find('{')
    
    if start_array >= 0 and (start_obj < 0 or start_array < start_obj):
        end = text.rfind(']')
        if end > start_array:
            return text[start_array:end + 1]
    elif start_obj >= 0:
        end = text.rfind('}')
        if end > start_obj:
            return text[start_obj:end + 1]
    
    return None


def repair_json(json_str: str) -> str:
    """
    尝试修复常见的JSON格式错误
    """
    if not json_str:
        return json_str
    
    json_str = re.sub(r'//.*$', '', json_str, flags=re.MULTILINE)
    json_str = re.sub(r'/\*[\s\S]*?\*/', '', json_str)
    
    json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)
    
    json_str = re.sub(r"(?<!\\)'", '"', json_str)
    
    json_str = re.sub(r'(\w+)(\s*:)', r'"\1"\2', json_str)
    json_str = re.sub(r'"+"', '"', json_str)
    
    json_str = json_str.replace('\n', ' ').replace('\r', ' ')
    json_str = re.sub(r'\s+', ' ', json_str)
    
    json_str = json_str.replace('True', 'true').replace('False', 'false')
    json_str = json_str.replace('None', 'null')
    
    return json_str


def balance_brackets(json_str: str) -> str:
    """
    平衡括号，尝试修复不完整的JSON
    """
    stack = []
    bracket_pairs = {'{': '}', '[': ']'}
    
    in_string = False
    escape_next = False
    
    for char in json_str:
        if escape_next:
            escape_next = False
            continue
        
        if char == '\\':
            escape_next = True
            continue
        
        if char == '"':
            in_string = not in_string
            continue
        
        if in_string:
            continue
        
        if char in bracket_pairs:
            stack.append(bracket_pairs[char])
        elif char in bracket_pairs.values():
            if stack and stack[-1] == char:
                stack.pop()
    
    result = json_str
    while stack:
        result += stack.pop()
    
    return result


def parse_json_safe(
    text: str,
    default: Any = None,
    repair: bool = True
) -> Any:
    """
    安全解析JSON，自动尝试修复常见错误
    
    Args:
        text: 包含JSON的文本
        default: 解析失败时的默认值
        repair: 是否尝试修复JSON
    
    Returns:
        解析后的Python对象，失败则返回default
    """
    if not text:
        return default
    
    json_str = extract_json_from_text(text)
    if not json_str:
        logger.warning("无法从文本中提取JSON")
        return default
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        if not repair:
            logger.error(f"JSON解析失败: {e}")
            return default
    
    logger.debug("尝试修复JSON...")
    
    try:
        repaired = repair_json(json_str)
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    try:
        balanced = balance_brackets(repaired)
        return json.loads(balanced)
    except json.JSONDecodeError:
        pass
    
    logger.error(f"JSON修复失败，原始文本片段: {json_str[:200]}...")
    return default


def parse_json_with_schema(
    text: str,
    schema_class: Type[T],
    repair: bool = True
) -> Optional[T]:
    """
    使用Pydantic模型解析并验证JSON
    
    Args:
        text: 包含JSON的文本
        schema_class: Pydantic模型类
        repair: 是否尝试修复JSON
    
    Returns:
        验证后的Pydantic模型实例，失败返回None
    """
    data = parse_json_safe(text, default=None, repair=repair)
    
    if data is None:
        return None
    
    try:
        return schema_class.model_validate(data)
    except ValidationError as e:
        logger.error(f"JSON Schema验证失败: {e}")
        return None


def parse_json_array(
    text: str,
    item_schema: Optional[Type[T]] = None,
    repair: bool = True,
    skip_invalid: bool = True
) -> List[Any]:
    """
    解析JSON数组，可选验证每个元素
    
    Args:
        text: 包含JSON数组的文本
        item_schema: 元素的Pydantic模型类（可选）
        repair: 是否尝试修复JSON
        skip_invalid: 是否跳过无效元素（否则整体失败）
    
    Returns:
        解析后的列表
    """
    data = parse_json_safe(text, default=[], repair=repair)
    
    if not isinstance(data, list):
        logger.warning(f"期望数组，实际类型: {type(data)}")
        return []
    
    if item_schema is None:
        return data
    
    result = []
    for i, item in enumerate(data):
        try:
            validated = item_schema.model_validate(item)
            result.append(validated)
        except ValidationError as e:
            if skip_invalid:
                logger.warning(f"数组元素 {i} 验证失败，已跳过: {e}")
            else:
                logger.error(f"数组元素 {i} 验证失败: {e}")
                return []
    
    return result


def create_json_extraction_prompt(
    schema_description: str,
    example: Optional[Dict[str, Any]] = None
) -> str:
    """
    创建JSON提取的提示词补充
    用于指导LLM输出规范的JSON
    """
    prompt = f"""
请严格按照以下JSON格式输出，不要添加任何额外文字说明：

输出格式要求:
{schema_description}

注意事项:
1. 必须是有效的JSON格式
2. 使用双引号包裹字符串
3. 不要在JSON中添加注释
4. 确保所有括号配对完整
5. 不要有尾随逗号
"""
    
    if example:
        prompt += f"\n示例输出:\n```json\n{json.dumps(example, ensure_ascii=False, indent=2)}\n```\n"
    
    return prompt


class StreamingJSONParser:
    """
    流式JSON解析器
    用于解析LLM流式输出中的JSON
    """
    
    def __init__(self):
        self._buffer = ""
        self._complete_objects: List[Any] = []
        self._in_string = False
        self._escape_next = False
        self._brace_count = 0
        self._bracket_count = 0
        self._current_start = -1
    
    def feed(self, chunk: str) -> List[Any]:
        """
        输入数据块，返回已完成解析的对象列表
        """
        new_objects = []
        
        for char in chunk:
            self._buffer += char
            
            if self._escape_next:
                self._escape_next = False
                continue
            
            if char == '\\':
                self._escape_next = True
                continue
            
            if char == '"':
                self._in_string = not self._in_string
                continue
            
            if self._in_string:
                continue
            
            if char == '{':
                if self._brace_count == 0 and self._bracket_count == 0:
                    self._current_start = len(self._buffer) - 1
                self._brace_count += 1
            elif char == '}':
                self._brace_count -= 1
                if self._brace_count == 0 and self._bracket_count == 0 and self._current_start >= 0:
                    obj_str = self._buffer[self._current_start:]
                    try:
                        obj = json.loads(obj_str)
                        new_objects.append(obj)
                        self._complete_objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    self._current_start = -1
            elif char == '[':
                if self._brace_count == 0 and self._bracket_count == 0:
                    self._current_start = len(self._buffer) - 1
                self._bracket_count += 1
            elif char == ']':
                self._bracket_count -= 1
                if self._brace_count == 0 and self._bracket_count == 0 and self._current_start >= 0:
                    obj_str = self._buffer[self._current_start:]
                    try:
                        obj = json.loads(obj_str)
                        new_objects.append(obj)
                        self._complete_objects.append(obj)
                    except json.JSONDecodeError:
                        pass
                    self._current_start = -1
        
        return new_objects
    
    def get_all(self) -> List[Any]:
        """获取所有已解析的对象"""
        return self._complete_objects
    
    def reset(self):
        """重置解析器状态"""
        self._buffer = ""
        self._complete_objects = []
        self._in_string = False
        self._escape_next = False
        self._brace_count = 0
        self._bracket_count = 0
        self._current_start = -1
