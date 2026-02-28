"""日志模块

支持按模块分类输出到不同的日志文件，自动根据配置初始化。
每次启动会创建一个以时间戳命名的新文件夹存放日志。
"""
import sys
from pathlib import Path
from typing import Optional, Dict, Set
from datetime import datetime
from loguru import logger

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 当前会话的日志目录（启动时生成）
_session_log_dir: Optional[Path] = None

# 模块名到日志类别的映射
MODULE_CATEGORY_MAP = {
    # API 相关
    "api": "api",
    "api.": "api",
    "fastapi": "api",
    "uvicorn": "api",

    # LLM 相关
    "llm": "llm",
    "src.llm": "llm",
    "ollama": "llm",

    # ComfyUI/图像相关
    "image": "comfyui",
    "src.image": "comfyui",
    "comfyui": "comfyui",

    # TTS 相关
    "tts": "tts",
    "src.tts": "tts",
    "cosyvoice": "tts",
    "edge_tts": "tts",

    # 视频相关
    "video": "video",
    "src.video": "video",
    "jimeng": "video",
    "kling": "video",
    "wan": "video",

    # Pipeline 相关
    "pipeline": "pipeline",
    "src.pipeline": "pipeline",
    "compose": "pipeline",
    "src.compose": "pipeline",
}

# 已添加的文件处理器 ID 集合
_file_handler_ids: Set[int] = set()
_initialized: bool = False


def _get_module_category(module_name: str) -> str:
    """根据模块名获取日志类别"""
    # 精确匹配
    if module_name in MODULE_CATEGORY_MAP:
        return MODULE_CATEGORY_MAP[module_name]

    # 前缀匹配
    for prefix, category in MODULE_CATEGORY_MAP.items():
        if module_name.startswith(prefix):
            return category

    # 默认归类到 all
    return "all"


def _ensure_log_dir(log_dir: Path) -> None:
    """确保日志目录存在"""
    log_dir.mkdir(parents=True, exist_ok=True)


def setup_logger(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    rotation: str = "10 MB",
    retention: str = "7 days",
    log_dir: Optional[Path] = None,
    separate_modules: bool = True,
    module_files: Optional[Dict[str, str]] = None,
) -> None:
    """配置日志系统

    Args:
        log_level: 日志级别
        log_file: 单一日志文件路径（如果不分模块）
        rotation: 日志文件轮转大小
        retention: 日志保留时间
        log_dir: 日志目录（如果分模块）
        separate_modules: 是否按模块分别记录
        module_files: 模块日志文件名映射
    """
    global _file_handler_ids, _initialized

    # 移除默认处理器
    logger.remove()

    # 移除之前添加的文件处理器
    for handler_id in _file_handler_ids:
        try:
            logger.remove(handler_id)
        except ValueError:
            pass
    _file_handler_ids.clear()

    # 控制台输出格式
    console_format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[name]}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # 文件输出格式
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{extra[name]}:{function}:{line} | "
        "{message}"
    )

    # 添加控制台处理器
    logger.add(
        sys.stderr,
        format=console_format,
        level=log_level,
        colorize=True,
        filter=lambda record: record["extra"].get("name", "__main__"),
    )

    # 如果指定了日志目录，添加文件处理器
    if log_dir:
        _ensure_log_dir(log_dir)

        if separate_modules and module_files:
            # 按模块分别记录
            for category, filename in module_files.items():
                log_path = log_dir / filename

                if category == "all":
                    # 全局日志，记录所有消息
                    handler_id = logger.add(
                        str(log_path),
                        format=file_format,
                        level=log_level,
                        rotation=rotation,
                        retention=retention,
                        encoding="utf-8",
                        enqueue=True,  # 异步写入，提高性能
                    )
                else:
                    # 模块日志，只记录对应类别的消息
                    def make_filter(cat: str):
                        def filter_func(record):
                            module_name = record["extra"].get("name", "")
                            return _get_module_category(module_name) == cat
                        return filter_func

                    handler_id = logger.add(
                        str(log_path),
                        format=file_format,
                        level=log_level,
                        rotation=rotation,
                        retention=retention,
                        encoding="utf-8",
                        filter=make_filter(category),
                        enqueue=True,
                    )
                _file_handler_ids.add(handler_id)
        else:
            # 单一日志文件
            log_path = log_dir / "app.log"
            handler_id = logger.add(
                str(log_path),
                format=file_format,
                level=log_level,
                rotation=rotation,
                retention=retention,
                encoding="utf-8",
                enqueue=True,
            )
            _file_handler_ids.add(handler_id)

    # 兼容旧的单文件模式
    elif log_file:
        _ensure_log_dir(log_file.parent)
        handler_id = logger.add(
            str(log_file),
            format=file_format,
            level=log_level,
            rotation=rotation,
            retention=retention,
            encoding="utf-8",
            enqueue=True,
        )
        _file_handler_ids.add(handler_id)

    _initialized = True


def _cleanup_old_log_dirs(base_log_dir: Path, max_dirs: int = 30) -> None:
    """清理旧的日志目录，只保留最近的 N 个

    Args:
        base_log_dir: 基础日志目录
        max_dirs: 最大保留的日志目录数量，默认 30
    """
    try:
        # 获取所有时间戳命名的日志目录（格式: YYYYMMDD_HHMMSS）
        log_dirs = []
        for item in base_log_dir.iterdir():
            if item.is_dir() and len(item.name) == 15 and item.name[8] == '_':
                # 验证格式是否为时间戳
                try:
                    datetime.strptime(item.name, "%Y%m%d_%H%M%S")
                    log_dirs.append(item)
                except ValueError:
                    continue

        # 按名称排序（时间戳格式天然支持字符串排序）
        log_dirs.sort(key=lambda x: x.name, reverse=True)

        # 删除超出数量限制的旧目录
        dirs_to_remove = log_dirs[max_dirs:]
        for old_dir in dirs_to_remove:
            try:
                import shutil
                shutil.rmtree(old_dir)
            except Exception:
                pass  # 忽略删除失败的目录

        if dirs_to_remove:
            # 使用 print 而非 logger，因为此时 logger 可能尚未初始化
            print(f"[Logger] 已清理 {len(dirs_to_remove)} 个旧日志目录")

    except Exception:
        pass  # 清理失败不影响主流程


def _create_session_log_dir(base_log_dir: Path) -> Path:
    """创建会话日志目录（以时间戳命名）

    Args:
        base_log_dir: 基础日志目录

    Returns:
        当前会话的日志目录路径
    """
    global _session_log_dir

    if _session_log_dir is not None:
        return _session_log_dir

    # 使用启动时间戳创建子目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_dir = base_log_dir / timestamp
    session_dir.mkdir(parents=True, exist_ok=True)

    _session_log_dir = session_dir

    # 创建/更新 latest 符号链接（Windows 上创建快捷方式可能失败，改用文本文件）
    latest_file = base_log_dir / "latest.txt"
    try:
        latest_file.write_text(timestamp, encoding="utf-8")
    except Exception:
        pass  # 忽略写入失败

    # 清理旧的日志目录
    _cleanup_old_log_dirs(base_log_dir, max_dirs=30)

    return session_dir


def get_current_log_dir() -> Optional[Path]:
    """获取当前会话的日志目录

    Returns:
        当前日志目录路径，如果未初始化则返回 None
    """
    return _session_log_dir


def init_logger_from_config() -> None:
    """从配置文件初始化日志系统

    每次启动会创建一个以时间戳命名的新文件夹存放日志。
    """
    global _initialized

    if _initialized:
        return

    try:
        # 延迟导入避免循环依赖
        from .config import get_config
        config = get_config()

        if config.logging.enabled:
            base_log_dir = PROJECT_ROOT / config.logging.log_dir
            # 创建以时间戳命名的会话日志目录
            session_log_dir = _create_session_log_dir(base_log_dir)

            module_files = {
                "api": config.logging.modules.api,
                "llm": config.logging.modules.llm,
                "comfyui": config.logging.modules.comfyui,
                "tts": config.logging.modules.tts,
                "video": config.logging.modules.video,
                "pipeline": config.logging.modules.pipeline,
                "all": config.logging.modules.all,
            }

            setup_logger(
                log_level=config.logging.level,
                log_dir=session_log_dir,
                rotation=config.logging.rotation,
                retention=config.logging.retention,
                separate_modules=config.logging.separate_modules,
                module_files=module_files,
            )

            # 记录启动日志
            startup_logger = get_logger("system")
            startup_logger.info(f"日志系统初始化完成 - 目录: {session_log_dir}")
            startup_logger.info(f"日志级别: {config.logging.level}, 轮转: {config.logging.rotation}")
        else:
            # 只输出到控制台
            setup_logger(log_level="INFO")

    except Exception as e:
        # 配置加载失败时使用默认设置
        setup_logger(log_level="INFO")
        logger.warning(f"从配置初始化日志失败，使用默认设置: {e}")


def get_logger(name: str = __name__):
    """获取命名日志器

    Args:
        name: 模块名，用于日志分类和显示

    Returns:
        绑定了模块名的日志器
    """
    # 确保日志系统已初始化
    if not _initialized:
        init_logger_from_config()

    return logger.bind(name=name)


# 模块导入时初始化（延迟到首次使用）
# 不在这里直接调用 init_logger_from_config()，避免循环导入问题
# 而是在 get_logger() 中检查并初始化
