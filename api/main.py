"""
FastAPI 主应用入口
"""
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .routers import projects, scenes, characters, generation, tasks, editor, settings, files
from .websocket import log_ws
from .exceptions import register_exception_handlers

# 初始化日志系统 - 必须在其他模块之前
from src.utils.logger import init_logger_from_config, get_logger
init_logger_from_config()

# API 模块日志器
api_logger = get_logger("api.main")
request_logger = get_logger("api.request")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    import asyncio
    from .services.generation_service import get_generation_service
    from .websocket.log_ws import get_connection_manager

    api_logger.info("FastAPI 应用启动中...")

    # 设置 WebSocket 广播回调
    generation_service = get_generation_service()
    ws_manager = get_connection_manager()

    # 保存主事件循环引用，用于跨线程调度
    main_loop = asyncio.get_running_loop()

    def on_progress_update(project_name: str, progress_data: dict):
        """进度更新时广播到 WebSocket（按项目隔离）

        注意：此回调从生成任务线程中调用，需要跨线程调度到主事件循环
        """
        try:
            # 使用 run_coroutine_threadsafe 从工作线程调度到主事件循环
            future = asyncio.run_coroutine_threadsafe(
                ws_manager.send_progress(
                    project_name=project_name,
                    phase=progress_data.get("phase", ""),
                    task=progress_data.get("task", ""),
                    progress=progress_data.get("progress", 0.0),
                    message=progress_data.get("message", ""),
                ),
                main_loop
            )
            # 不阻塞等待结果，让协程异步执行
        except Exception as e:
            api_logger.error(f"WebSocket 广播失败: {e}")

    generation_service.on_progress_callback = on_progress_update

    api_logger.info("FastAPI 应用启动完成")
    yield
    # 关闭时清理
    api_logger.info("FastAPI 应用关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="小说转视频 API",
        description="小说转视频生成系统的后端 API",
        version="1.0.0",
        lifespan=lifespan,
    )

    # 配置 CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 开发环境允许所有来源，生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(projects.router, prefix="/api/projects", tags=["项目管理"])
    app.include_router(scenes.router, prefix="/api/scenes", tags=["分镜场景"])
    app.include_router(characters.router, prefix="/api/characters", tags=["角色管理"])
    app.include_router(generation.router, prefix="/api/generation", tags=["生成控制"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["任务队列"])
    app.include_router(editor.router, prefix="/api/editor", tags=["视频编辑"])
    app.include_router(settings.router, prefix="/api/settings", tags=["系统设置"])
    app.include_router(files.router, prefix="/api/files", tags=["文件管理"])

    # WebSocket 路由
    app.include_router(log_ws.router, prefix="/api/ws", tags=["WebSocket"])

    # 注册全局异常处理器
    register_exception_handlers(app)

    # 挂载静态文件服务
    data_dir = Path(__file__).parent.parent / "data"
    if data_dir.exists():
        app.mount("/static", StaticFiles(directory=str(data_dir)), name="static")

    @app.get("/", tags=["健康检查"])
    async def root():
        """API 根路径"""
        return {
            "message": "小说转视频 API",
            "version": "1.0.0",
            "docs": "/docs",
        }

    @app.get("/health", tags=["健康检查"])
    async def health_check():
        """健康检查端点"""
        return {"status": "healthy"}

    return app


app = create_app()

