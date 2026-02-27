"""
API 全局异常处理

统一的异常处理中间件，将后端异常转换为友好的 API 响应
"""
from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from loguru import logger

from src.exceptions import (
    XiaoshuoVideoError,
    ServiceUnavailableError,
    ServiceTimeoutError,
    APIError,
    APIRateLimitError,
    ProjectNotFoundError,
    ProjectExistsError,
    InvalidInputError,
    MissingConfigError,
    InvalidConfigError,
)


class ErrorResponse(BaseModel):
    """统一错误响应格式"""
    success: bool = False
    error_code: str
    message: str
    detail: Optional[str] = None
    suggestion: Optional[str] = None


# 错误码映射
ERROR_CODES = {
    "service_unavailable": "服务暂时不可用",
    "service_timeout": "服务响应超时",
    "api_error": "外部API调用失败",
    "rate_limit": "请求过于频繁",
    "project_not_found": "项目不存在",
    "project_exists": "项目已存在",
    "invalid_input": "输入参数无效",
    "config_error": "配置错误",
    "generation_error": "生成过程出错",
    "internal_error": "内部服务器错误",
}

# 针对特定错误的排查建议
ERROR_SUGGESTIONS = {
    "ServiceUnavailableError": {
        "ollama": "请确保 Ollama 服务已启动：运行 'ollama serve' 或检查 http://localhost:11434",
        "comfyui": "请确保 ComfyUI 服务已启动：运行 'python main.py' 或检查 http://localhost:8188",
        "cosyvoice": "请确保 CosyVoice 服务已启动，检查 http://localhost:9880",
        "default": "请检查相关服务是否已正确启动",
    },
    "ServiceTimeoutError": "服务响应超时，请检查服务负载或网络连接",
    "APIRateLimitError": "请求过于频繁，请稍后重试",
    "ProjectNotFoundError": "请确认项目名称是否正确，或刷新项目列表",
    "InvalidInputError": "请检查输入参数是否符合要求",
    "MissingConfigError": "请检查 config/settings.yaml 配置文件",
}


def get_suggestion(exc: Exception) -> Optional[str]:
    """获取错误排查建议"""
    exc_name = type(exc).__name__
    
    if isinstance(exc, ServiceUnavailableError):
        service = exc.service_name.lower()
        suggestions = ERROR_SUGGESTIONS.get("ServiceUnavailableError", {})
        if isinstance(suggestions, dict):
            return suggestions.get(service, suggestions.get("default"))
    
    suggestion = ERROR_SUGGESTIONS.get(exc_name)
    return suggestion if isinstance(suggestion, str) else None


def create_error_response(
    error_code: str,
    message: str,
    detail: Optional[str] = None,
    suggestion: Optional[str] = None,
    status_code: int = 500
) -> JSONResponse:
    """创建统一格式的错误响应"""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error_code": error_code,
            "message": message,
            "detail": detail,
            "suggestion": suggestion,
        }
    )


def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器"""
    
    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError):
        logger.warning(f"服务不可用: {exc.service_name} - {exc.url}")
        return create_error_response(
            error_code="service_unavailable",
            message=f"服务 {exc.service_name} 暂时不可用",
            detail=exc.details,
            suggestion=get_suggestion(exc),
            status_code=503
        )
    
    @app.exception_handler(ServiceTimeoutError)
    async def service_timeout_handler(request: Request, exc: ServiceTimeoutError):
        logger.warning(f"服务超时: {exc.service_name} - {exc.timeout}s")
        return create_error_response(
            error_code="service_timeout",
            message=f"服务 {exc.service_name} 响应超时",
            detail=f"等待 {exc.timeout} 秒后超时",
            suggestion=get_suggestion(exc),
            status_code=504
        )
    
    @app.exception_handler(APIRateLimitError)
    async def rate_limit_handler(request: Request, exc: APIRateLimitError):
        return create_error_response(
            error_code="rate_limit",
            message="请求过于频繁",
            detail=exc.details,
            suggestion=f"请等待 {exc.retry_after} 秒后重试" if exc.retry_after else "请稍后重试",
            status_code=429
        )
    
    @app.exception_handler(ProjectNotFoundError)
    async def project_not_found_handler(request: Request, exc: ProjectNotFoundError):
        return create_error_response(
            error_code="project_not_found",
            message=f"项目 '{exc.project_name}' 不存在",
            suggestion=get_suggestion(exc),
            status_code=404
        )
    
    @app.exception_handler(ProjectExistsError)
    async def project_exists_handler(request: Request, exc: ProjectExistsError):
        return create_error_response(
            error_code="project_exists",
            message=f"项目 '{exc.project_name}' 已存在",
            suggestion="请使用其他名称或删除现有项目",
            status_code=409
        )

    @app.exception_handler(InvalidInputError)
    async def invalid_input_handler(request: Request, exc: InvalidInputError):
        return create_error_response(
            error_code="invalid_input",
            message=f"输入参数无效: {exc.field}",
            detail=exc.details,
            suggestion=get_suggestion(exc),
            status_code=400
        )

    @app.exception_handler(MissingConfigError)
    async def missing_config_handler(request: Request, exc: MissingConfigError):
        return create_error_response(
            error_code="config_error",
            message=f"缺少配置: {exc.config_key}",
            detail=f"配置文件: {exc.config_file}" if exc.config_file else None,
            suggestion="请检查 config/settings.yaml 配置文件是否正确",
            status_code=500
        )

    @app.exception_handler(InvalidConfigError)
    async def invalid_config_handler(request: Request, exc: InvalidConfigError):
        return create_error_response(
            error_code="config_error",
            message=f"配置无效: {exc.config_key}",
            detail=exc.reason,
            suggestion="请检查 config/settings.yaml 配置文件",
            status_code=500
        )

    @app.exception_handler(XiaoshuoVideoError)
    async def app_error_handler(request: Request, exc: XiaoshuoVideoError):
        """捕获所有自定义异常"""
        logger.error(f"应用错误: {exc}")
        return create_error_response(
            error_code="generation_error",
            message=exc.message,
            detail=exc.details,
            status_code=500
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """处理 FastAPI HTTPException"""
        return create_error_response(
            error_code="http_error",
            message=str(exc.detail),
            status_code=exc.status_code
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """捕获所有未处理的异常"""
        logger.exception(f"未处理的异常: {exc}")
        return create_error_response(
            error_code="internal_error",
            message="服务器内部错误",
            detail=str(exc) if app.debug else None,
            suggestion="请稍后重试，如果问题持续存在请查看服务器日志",
            status_code=500
        )

