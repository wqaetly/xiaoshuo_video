"""
小说转视频 - 主入口
"""
import argparse
from pathlib import Path
from typing import Optional, List


def main():
    parser = argparse.ArgumentParser(
        description="小说转视频生成系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m src.main create --name 我的项目 --novel novel.txt
  python -m src.main run --project 我的项目 --resume
  python -m src.main list
  python -m src.main export --project 我的项目 --output ./export
  python -m src.main clean --project 我的项目 --temp
  python -m src.main batch --projects 项目1,项目2 --phase generate_images
  python -m src.main ui
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # create 命令
    create_parser = subparsers.add_parser("create", help="创建新项目")
    create_parser.add_argument("--name", required=True, help="项目名称")
    create_parser.add_argument("--novel", required=True, help="小说文件路径")
    create_parser.add_argument("--style", default="anime", 
                               choices=["anime", "realistic", "illustration", "chinese_fantasy"],
                               help="视频风格 (默认: anime)")

    # run 命令
    run_parser = subparsers.add_parser("run", help="运行生成")
    run_parser.add_argument("--project", required=True, help="项目名称")
    run_parser.add_argument("--resume", action="store_true", help="断点续传")
    run_parser.add_argument("--phase", help="指定运行阶段")
    run_parser.add_argument("--parallel", action="store_true", help="使用并行模式")

    # ui 命令
    ui_parser = subparsers.add_parser("ui", help="启动Web界面")
    ui_parser.add_argument("--host", default="127.0.0.1", help="服务器地址")
    ui_parser.add_argument("--port", type=int, default=7860, help="端口号")
    ui_parser.add_argument("--share", action="store_true", help="创建公共链接")

    # status 命令
    status_parser = subparsers.add_parser("status", help="查看项目状态")
    status_parser.add_argument("--project", required=True, help="项目名称")

    # list 命令
    list_parser = subparsers.add_parser("list", help="列出所有项目")
    list_parser.add_argument("--detail", action="store_true", help="显示详细信息")

    # export 命令
    export_parser = subparsers.add_parser("export", help="导出项目")
    export_parser.add_argument("--project", required=True, help="项目名称")
    export_parser.add_argument("--output", required=True, help="导出路径")
    export_parser.add_argument("--format", default="zip", choices=["zip", "folder"], help="导出格式")
    export_parser.add_argument("--include-temp", action="store_true", help="包含临时文件")

    # clean 命令
    clean_parser = subparsers.add_parser("clean", help="清理项目文件")
    clean_parser.add_argument("--project", help="项目名称 (不指定则清理所有项目)")
    clean_parser.add_argument("--temp", action="store_true", help="清理临时文件")
    clean_parser.add_argument("--output", action="store_true", help="清理输出文件")
    clean_parser.add_argument("--all", action="store_true", help="清理所有生成文件")
    clean_parser.add_argument("--force", action="store_true", help="跳过确认")

    # batch 命令
    batch_parser = subparsers.add_parser("batch", help="批量处理多个项目")
    batch_parser.add_argument("--projects", required=True, help="项目名称列表 (逗号分隔)")
    batch_parser.add_argument("--phase", help="指定运行阶段")
    batch_parser.add_argument("--resume", action="store_true", help="断点续传")
    batch_parser.add_argument("--parallel", action="store_true", help="并行处理项目")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args.name, args.novel, args.style)
    elif args.command == "run":
        cmd_run(args.project, args.resume, args.phase, getattr(args, 'parallel', False))
    elif args.command == "ui":
        cmd_ui(args.host, args.port, args.share)
    elif args.command == "status":
        cmd_status(args.project)
    elif args.command == "list":
        cmd_list(getattr(args, 'detail', False))
    elif args.command == "export":
        cmd_export(args.project, args.output, args.format, getattr(args, 'include_temp', False))
    elif args.command == "clean":
        cmd_clean(args.project, args.temp, args.output, getattr(args, 'all', False), args.force)
    elif args.command == "batch":
        cmd_batch(args.projects, args.phase, args.resume, getattr(args, 'parallel', False))
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


def cmd_run(project_name: str, resume: bool, phase: Optional[str], parallel: bool = False):
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
        elif parallel:
            pipeline.run_parallel(resume=resume)
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


def cmd_list(detail: bool = False):
    """列出所有项目"""
    from .utils.config import get_config
    from .pipeline import PipelineState
    from datetime import datetime

    config = get_config()
    projects_dir = Path(config.paths.projects_dir)

    if not projects_dir.exists():
        print("📁 项目目录不存在")
        return

    projects = [p for p in projects_dir.iterdir() if p.is_dir()]

    if not projects:
        print("📁 暂无项目")
        print(f"   使用 'python -m src.main create --name 项目名 --novel 小说.txt' 创建项目")
        return

    print(f"\n📁 项目列表 ({len(projects)} 个项目)")
    print("-" * 60)

    for project_path in sorted(projects):
        name = project_path.name
        state_file = project_path / "pipeline_state.json"

        if detail:
            # 详细模式
            print(f"\n📂 {name}")
            print(f"   路径: {project_path}")

            # 检查小说文件
            novel_file = project_path / "input" / "novel.txt"
            if novel_file.exists():
                size = novel_file.stat().st_size / 1024
                print(f"   小说: {size:.1f} KB")

            # 检查状态
            if state_file.exists():
                state = PipelineState.load(state_file)
                progress = state.get_progress()
                print(f"   阶段: {state.current_phase.value}")
                print(f"   进度: {progress['completed_scenes']}/{progress['total_scenes']} 场景")
                if progress['error_count'] > 0:
                    print(f"   错误: {progress['error_count']} 个")
            else:
                print(f"   状态: 未开始")

            # 统计文件
            images = list((project_path / "images").glob("*.png")) if (project_path / "images").exists() else []
            videos = list((project_path / "videos").glob("*.mp4")) if (project_path / "videos").exists() else []
            audios = list((project_path / "audio").glob("*.wav")) if (project_path / "audio").exists() else []
            print(f"   资源: {len(images)} 图片, {len(videos)} 视频, {len(audios)} 音频")
        else:
            # 简略模式
            status = "未开始"
            if state_file.exists():
                state = PipelineState.load(state_file)
                status = state.current_phase.value
            print(f"   {name:<20} [{status}]")

    print("-" * 60)


def cmd_export(project_name: str, output_path: str, format: str = "zip", include_temp: bool = False):
    """导出项目"""
    import shutil
    import zipfile
    from .utils.config import get_config

    config = get_config()
    project_path = Path(config.paths.projects_dir) / project_name
    output = Path(output_path)

    if not project_path.exists():
        print(f"错误: 项目不存在: {project_name}")
        return

    print(f"📦 导出项目: {project_name}")

    # 需要导出的目录
    export_dirs = ["input", "output", "characters.json", "storyboard.json", "project.yaml"]
    if include_temp:
        export_dirs.extend(["images", "videos", "audio", "characters"])

    if format == "zip":
        # 导出为ZIP
        zip_path = output if output.suffix == ".zip" else output / f"{project_name}.zip"
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for item in export_dirs:
                item_path = project_path / item
                if item_path.exists():
                    if item_path.is_file():
                        zf.write(item_path, item)
                    else:
                        for file in item_path.rglob("*"):
                            if file.is_file():
                                arc_name = str(file.relative_to(project_path))
                                zf.write(file, arc_name)

        # 计算大小
        size = zip_path.stat().st_size / (1024 * 1024)
        print(f"✅ 导出完成: {zip_path} ({size:.1f} MB)")

    else:
        # 导出为文件夹
        export_path = output / project_name
        if export_path.exists():
            print(f"警告: 目标目录已存在，将被覆盖")
            shutil.rmtree(export_path)

        export_path.mkdir(parents=True, exist_ok=True)

        for item in export_dirs:
            item_path = project_path / item
            if item_path.exists():
                dest = export_path / item
                if item_path.is_file():
                    shutil.copy2(item_path, dest)
                else:
                    shutil.copytree(item_path, dest)

        print(f"✅ 导出完成: {export_path}")


def cmd_clean(project_name: Optional[str], clean_temp: bool, clean_output: bool, clean_all: bool, force: bool):
    """清理项目文件"""
    import shutil
    from .utils.config import get_config

    config = get_config()
    projects_dir = Path(config.paths.projects_dir)

    # 确定要清理的项目
    if project_name:
        project_paths = [projects_dir / project_name]
        if not project_paths[0].exists():
            print(f"错误: 项目不存在: {project_name}")
            return
    else:
        project_paths = [p for p in projects_dir.iterdir() if p.is_dir()]

    if not project_paths:
        print("没有可清理的项目")
        return

    # 确定要清理的目录
    dirs_to_clean = []
    if clean_all:
        dirs_to_clean = ["images", "videos", "audio", "characters", "output"]
    else:
        if clean_temp:
            dirs_to_clean.extend(["images", "videos", "audio", "characters"])
        if clean_output:
            dirs_to_clean.append("output")

    if not dirs_to_clean:
        print("请指定清理选项: --temp, --output, 或 --all")
        return

    # 统计要清理的文件
    total_files = 0
    total_size = 0

    for project_path in project_paths:
        for dir_name in dirs_to_clean:
            dir_path = project_path / dir_name
            if dir_path.exists():
                for f in dir_path.rglob("*"):
                    if f.is_file():
                        total_files += 1
                        total_size += f.stat().st_size

    size_mb = total_size / (1024 * 1024)
    print(f"\n🧹 将清理 {len(project_paths)} 个项目中的 {total_files} 个文件 ({size_mb:.1f} MB)")
    print(f"   目录: {', '.join(dirs_to_clean)}")

    # 确认
    if not force:
        confirm = input("\n确认清理? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("已取消")
            return

    # 执行清理
    cleaned_files = 0
    for project_path in project_paths:
        for dir_name in dirs_to_clean:
            dir_path = project_path / dir_name
            if dir_path.exists():
                for f in dir_path.rglob("*"):
                    if f.is_file():
                        f.unlink()
                        cleaned_files += 1

    print(f"✅ 已清理 {cleaned_files} 个文件")


def cmd_batch(projects_str: str, phase: Optional[str], resume: bool, parallel: bool):
    """批量处理多个项目"""
    from .utils.config import get_config
    from .pipeline import PipelineController, Phase
    import concurrent.futures

    config = get_config()
    projects_dir = Path(config.paths.projects_dir)

    # 解析项目列表
    project_names = [p.strip() for p in projects_str.split(",") if p.strip()]

    if not project_names:
        print("错误: 请指定至少一个项目")
        return

    # 验证项目存在
    valid_projects = []
    for name in project_names:
        project_path = projects_dir / name
        if project_path.exists():
            valid_projects.append((name, project_path))
        else:
            print(f"⚠️ 项目不存在，跳过: {name}")

    if not valid_projects:
        print("错误: 没有有效的项目")
        return

    print(f"\n🚀 批量处理 {len(valid_projects)} 个项目")
    print("-" * 40)

    def process_project(name: str, project_path: Path) -> tuple:
        """处理单个项目"""
        try:
            pipeline = PipelineController(project_path, config)

            if phase:
                phase_enum = Phase(phase)
                pipeline.run_phase(phase_enum)
            else:
                pipeline.run(resume=resume)

            return (name, True, None)
        except Exception as e:
            return (name, False, str(e))

    results = []

    if parallel:
        # 并行处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = {
                executor.submit(process_project, name, path): name
                for name, path in valid_projects
            }

            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    status = "✅" if result[1] else "❌"
                    print(f"   {status} {result[0]}")
                except Exception as e:
                    results.append((name, False, str(e)))
                    print(f"   ❌ {name}: {e}")
    else:
        # 串行处理
        for i, (name, project_path) in enumerate(valid_projects, 1):
            print(f"\n[{i}/{len(valid_projects)}] 处理: {name}")
            result = process_project(name, project_path)
            results.append(result)

            if result[1]:
                print(f"   ✅ 完成")
            else:
                print(f"   ❌ 失败: {result[2]}")

    # 汇总
    print("\n" + "-" * 40)
    success = sum(1 for r in results if r[1])
    failed = len(results) - success
    print(f"📊 完成: {success} 成功, {failed} 失败")
