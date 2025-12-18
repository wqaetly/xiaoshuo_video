"""
小说转视频 - 主入口
"""
import argparse
from pathlib import Path
from typing import Optional


def main():
    parser = argparse.ArgumentParser(description="小说转视频生成系统")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建新项目")
    create_parser.add_argument("--name", required=True, help="项目名称")
    create_parser.add_argument("--novel", required=True, help="小说文件路径")
    create_parser.add_argument("--style", default="anime", help="视频风格")

    # run 命令
    run_parser = subparsers.add_parser("run", help="运行生成")
    run_parser.add_argument("--project", required=True, help="项目名称")
    run_parser.add_argument("--resume", action="store_true", help="断点续传")
    run_parser.add_argument("--phase", help="指定运行阶段")

    # ui 命令
    ui_parser = subparsers.add_parser("ui", help="启动Web界面")
    ui_parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    ui_parser.add_argument("--port", type=int, default=7860, help="端口号")
    ui_parser.add_argument("--share", action="store_true", help="创建公共链接")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看项目状态")
    status_parser.add_argument("--project", required=True, help="项目名称")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args.name, args.novel, args.style)
    elif args.command == "run":
        cmd_run(args.project, args.resume, args.phase)
    elif args.command == "ui":
        cmd_ui(args.host, args.port, args.share)
    elif args.command == "status":
        cmd_status(args.project)
    else:
        parser.print_help()


def cmd_create(name: str, novel_path: str, style: str):
    """创建新项目"""
    from .utils.config import get_config
    from .utils.file_utils import ensure_dir
    import shutil
    import yaml

    config = get_config()
    project_path = Path(config.paths.projects_dir) / name

    if project_path.exists():
        print(f"错误: 项目 {name} 已存在")
        return

    # 创建目录
    for dir_name in ["input", "characters", "images", "videos", "audio", "output"]:
        ensure_dir(project_path / dir_name)

    # 复制小说文件
    novel_src = Path(novel_path)
    if not novel_src.exists():
        print(f"错误: 小说文件不存在: {novel_path}")
        return

    shutil.copy(novel_src, project_path / "input" / "novel.txt")

    # 创建项目配置
    project_config = {
        "project": {"name": name},
        "video": {"style": style},
    }
    with open(project_path / "project.yaml", "w", encoding="utf-8") as f:
        yaml.dump(project_config, f, allow_unicode=True)

    print(f"✅ 项目 {name} 创建成功!")
    print(f"   路径: {project_path}")
    print(f"   下一步: python -m src.main run --project {name}")


def cmd_run(project_name: str, resume: bool, phase: Optional[str]):
    """运行生成"""
    from .utils.config import get_config
    from .pipeline import PipelineController, Phase

    config = get_config()
    project_path = Path(config.paths.projects_dir) / project_name

    if not project_path.exists():
        print(f"错误: 项目不存在: {project_name}")
        return

    pipeline = PipelineController(project_path, config)

    def progress_callback(stage: str, detail: str, progress: float):
        bar_length = 30
        filled = int(bar_length * progress)
        bar = "█" * filled + "░" * (bar_length - filled)
        print(f"\r[{bar}] {progress*100:.1f}% | {stage}: {detail}", end="", flush=True)

    pipeline.on_progress = progress_callback

    try:
        if phase:
            phase_enum = Phase(phase)
            pipeline.run_phase(phase_enum)
        else:
            pipeline.run(resume=resume)
        print("\n✅ 生成完成!")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")


def cmd_ui(host: str, port: int, share: bool):
    """启动Web界面"""
    from .webui import launch
    print(f"🚀 启动Web界面: http://{host}:{port}")
    launch(server_name=host, server_port=port, share=share)


def cmd_status(project_name: str):
    """查看项目状态"""
    from .utils.config import get_config
    from .pipeline import PipelineState

    config = get_config()
    project_path = Path(config.paths.projects_dir) / project_name

    if not project_path.exists():
        print(f"错误: 项目不存在: {project_name}")
        return

    state_file = project_path / "pipeline_state.json"
    if not state_file.exists():
        print(f"项目 {project_name} 尚未开始生成")
        return

    state = PipelineState.load(state_file)
    progress = state.get_progress()

    print(f"\n📊 项目状态: {project_name}")
    print(f"   当前阶段: {state.current_phase.value}")
    print(f"   场景进度: {progress['completed_scenes']}/{progress['total_scenes']}")
    print(f"   错误数量: {progress['error_count']}")

    if state.errors:
        print("\n⚠️ 最近错误:")
        for err in state.errors[-5:]:
            print(f"   - [{err['phase']}] {err['message'][:50]}")


if __name__ == "__main__":
    main()
