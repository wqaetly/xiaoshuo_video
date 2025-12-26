"""
自定义异常类

统一的异常处理，便于错误追踪和用户友好的错误提示
"""
from typing import Optional


class XiaoshuoVideoError(Exception):
    """基础异常类"""

    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


# ============ 服务相关异常 ============


class ServiceError(XiaoshuoVideoError):
    """服务相关错误基类"""

    pass


class ServiceUnavailableError(ServiceError):
    """服务不可用"""

    def __init__(self, service_name: str, url: str, details: Optional[str] = None):
        self.service_name = service_name
        self.url = url
        message = f"服务 {service_name} 不可用 ({url})"
        super().__init__(message, details)


class ServiceTimeoutError(ServiceError):
    """服务超时"""

    def __init__(self, service_name: str, timeout: float, details: Optional[str] = None):
        self.service_name = service_name
        self.timeout = timeout
        message = f"服务 {service_name} 响应超时 ({timeout}秒)"
        super().__init__(message, details)


class APIError(ServiceError):
    """API调用错误"""

    def __init__(
        self,
        api_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        details: Optional[str] = None,
    ):
        self.api_name = api_name
        self.status_code = status_code
        self.response_body = response_body
        message = f"API {api_name} 调用失败"
        if status_code:
            message += f" (状态码: {status_code})"
        super().__init__(message, details)


class APIRateLimitError(APIError):
    """API 速率限制"""

    def __init__(self, api_name: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        details = f"请在 {retry_after} 秒后重试" if retry_after else "请稍后重试"
        super().__init__(api_name, status_code=429, details=details)


class APIQuotaExceededError(APIError):
    """API 配额超限"""

    def __init__(self, api_name: str, details: Optional[str] = None):
        super().__init__(api_name, details=details or "API配额已用尽，请充值或等待重置")


# ============ 生成相关异常 ============


class GenerationError(XiaoshuoVideoError):
    """生成相关错误基类"""

    pass


class LLMGenerationError(GenerationError):
    """LLM 生成错误"""

    def __init__(self, model: str, prompt_type: str, details: Optional[str] = None):
        self.model = model
        self.prompt_type = prompt_type
        message = f"LLM生成失败 (模型: {model}, 类型: {prompt_type})"
        super().__init__(message, details)


class ImageGenerationError(GenerationError):
    """图像生成错误"""

    def __init__(self, scene_id: str, details: Optional[str] = None):
        self.scene_id = scene_id
        message = f"图像生成失败 (场景: {scene_id})"
        super().__init__(message, details)


class VideoGenerationError(GenerationError):
    """视频生成错误"""

    def __init__(self, scene_id: str, provider: str, details: Optional[str] = None):
        self.scene_id = scene_id
        self.provider = provider
        message = f"视频生成失败 (场景: {scene_id}, 提供商: {provider})"
        super().__init__(message, details)


class AudioGenerationError(GenerationError):
    """音频生成错误"""

    def __init__(self, scene_id: str, details: Optional[str] = None):
        self.scene_id = scene_id
        message = f"音频生成失败 (场景: {scene_id})"
        super().__init__(message, details)


class CompositionError(GenerationError):
    """视频合成错误"""

    def __init__(self, stage: str, details: Optional[str] = None):
        self.stage = stage
        message = f"视频合成失败 (阶段: {stage})"
        super().__init__(message, details)


# ============ 数据相关异常 ============


class DataError(XiaoshuoVideoError):
    """数据相关错误基类"""

    pass


class InvalidInputError(DataError):
    """无效输入"""

    def __init__(self, field: str, expected: str, got: Optional[str] = None):
        self.field = field
        self.expected = expected
        self.got = got
        message = f"无效输入: {field}"
        details = f"期望 {expected}"
        if got:
            details += f", 实际 {got}"
        super().__init__(message, details)


class FileNotFoundError(DataError):
    """文件未找到"""

    def __init__(self, file_path: str, file_type: str = "文件"):
        self.file_path = file_path
        self.file_type = file_type
        message = f"{file_type}不存在: {file_path}"
        super().__init__(message)


class ParseError(DataError):
    """解析错误"""

    def __init__(self, content_type: str, details: Optional[str] = None):
        self.content_type = content_type
        message = f"解析{content_type}失败"
        super().__init__(message, details)


class JSONParseError(ParseError):
    """JSON解析错误"""

    def __init__(self, source: str = "LLM输出", details: Optional[str] = None):
        self.source = source
        super().__init__(f"JSON ({source})", details)


# ============ 项目相关异常 ============


class ProjectError(XiaoshuoVideoError):
    """项目相关错误基类"""

    pass


class ProjectNotFoundError(ProjectError):
    """项目不存在"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        message = f"项目不存在: {project_name}"
        super().__init__(message)


class ProjectExistsError(ProjectError):
    """项目已存在"""

    def __init__(self, project_name: str):
        self.project_name = project_name
        message = f"项目已存在: {project_name}"
        super().__init__(message)


class InvalidProjectStateError(ProjectError):
    """无效的项目状态"""

    def __init__(self, project_name: str, current_state: str, required_state: str):
        self.project_name = project_name
        self.current_state = current_state
        self.required_state = required_state
        message = f"项目 {project_name} 状态无效"
        details = f"当前: {current_state}, 需要: {required_state}"
        super().__init__(message, details)


# ============ 配置相关异常 ============


class ConfigError(XiaoshuoVideoError):
    """配置相关错误基类"""

    pass


class MissingConfigError(ConfigError):
    """缺少配置"""

    def __init__(self, config_key: str, config_file: Optional[str] = None):
        self.config_key = config_key
        self.config_file = config_file
        message = f"缺少配置: {config_key}"
        if config_file:
            message += f" (文件: {config_file})"
        super().__init__(message)


class InvalidConfigError(ConfigError):
    """无效配置"""

    def __init__(self, config_key: str, value: str, reason: str):
        self.config_key = config_key
        self.value = value
        self.reason = reason
        message = f"配置无效: {config_key}={value}"
        super().__init__(message, reason)
