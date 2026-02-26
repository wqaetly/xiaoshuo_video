"""
FastAPI 主应用入口
"""
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers import projects, scenes, characters, generation, tasks, editor, settings, files
from .websocket import log_ws


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    yield
    # 关闭时清理


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
    app.include_router(log_ws.router, prefix="/ws", tags=["WebSocket"])

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

