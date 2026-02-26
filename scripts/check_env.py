"""
环境检查脚本 - 检查项目运行所需的依赖和服务
"""
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_status(name: str, status: bool, message: str = ""):
    """打印状态"""
    icon = "[OK]" if status else "[X]"
    color = Colors.GREEN if status else Colors.RED
    msg = f" - {message}" if message else ""
    print(f"  {color}{icon}{Colors.RESET} {name}{msg}")

def print_header(title: str):
    """打印标题"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}[{title}]{Colors.RESET}")

def check_python_version() -> Tuple[bool, str]:
    """检查Python版本"""
    version = sys.version_info
    if version.major >= 3 and version.minor >= 10:
        return True, f"{version.major}.{version.minor}.{version.micro}"
    return False, f"{version.major}.{version.minor} (需要 3.10+)"

def check_command(cmd: str, version_arg: str = "--version") -> Tuple[bool, str]:
    """检查命令是否可用"""
    # 先检查项目内置的 FFmpeg
    if cmd in ("ffmpeg", "ffprobe"):
        project_root = Path(__file__).parent.parent
        if sys.platform == "win32":
            project_path = project_root / "tools" / "ffmpeg" / "bin" / f"{cmd}.exe"
        else:
            project_path = project_root / "tools" / "ffmpeg" / cmd
        
        if project_path.exists():
            try:
                result = subprocess.run(
                    [str(project_path), version_arg],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                version = result.stdout.strip().split('\n')[0] if result.stdout else "已安装"
                return True, f"{version} (项目内置)"
            except Exception:
                return True, "已安装 (项目内置)"
    
    # 检查系统路径
    path = shutil.which(cmd)
    if not path:
        return False, "未安装"
    try:
        result = subprocess.run(
            [cmd, version_arg],
            capture_output=True,
            text=True,
            timeout=10
        )
        version = result.stdout.strip().split('\n')[0] if result.stdout else "已安装"
        return True, version
    except Exception as e:
        return True, f"已安装 (版本检查失败: {e})"

def check_python_package(package: str) -> Tuple[bool, str]:
    """检查Python包是否安装"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", f"import {package}; print(getattr({package}, '__version__', 'installed'))"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            version = result.stdout.strip()
            return True, version
        return False, "未安装"
    except Exception:
        return False, "检查失败"

def check_service(url: str, timeout: int = 3) -> Tuple[bool, str]:
    """检查服务是否可用"""
    try:
        import requests
        response = requests.get(url, timeout=timeout)
        return True, f"状态码 {response.status_code}"
    except ImportError:
        return False, "requests未安装"
    except Exception as e:
        return False, str(e)[:30]

def check_gpu() -> Tuple[bool, str]:
    """检查GPU/CUDA"""
    try:
        result = subprocess.run(
            [sys.executable, "-c", "import torch; print(f'CUDA {torch.version.cuda}' if torch.cuda.is_available() else 'CPU only')"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            info = result.stdout.strip()
            has_cuda = "CUDA" in info
            return has_cuda, info
        return False, "torch未安装"
    except Exception:
        return False, "检查失败"

def get_ffmpeg_install_instructions() -> str:
    """获取FFmpeg安装说明"""
    if sys.platform == "win32":
        return """
    安装方法 (选择一种):
    1. Chocolatey: choco install ffmpeg
    2. Scoop: scoop install ffmpeg
    3. 手动下载: https://www.gyan.dev/ffmpeg/builds/
       下载后解压，将bin目录添加到系统PATH"""
    elif sys.platform == "darwin":
        return "    安装: brew install ffmpeg"
    else:
        return "    安装: sudo apt install ffmpeg  # 或 yum install ffmpeg"

def run_checks() -> Dict[str, bool]:
    """运行所有检查"""
    results = {}
    
    print(f"\n{Colors.BOLD}{'='*50}")
    print("   小说转视频 - 环境检查")
    print(f"{'='*50}{Colors.RESET}")
    
    # 1. 基础环境
    print_header("基础环境")
    
    ok, msg = check_python_version()
    print_status("Python", ok, msg)
    results["python"] = ok
    
    ok, msg = check_command("ffmpeg", "-version")
    print_status("FFmpeg", ok, msg)
    results["ffmpeg"] = ok
    if not ok:
        print(f"{Colors.YELLOW}{get_ffmpeg_install_instructions()}{Colors.RESET}")
    
    ok, msg = check_command("ffprobe", "-version")
    print_status("FFprobe", ok, msg)
    results["ffprobe"] = ok
    
    # 2. Python依赖
    print_header("Python依赖")
    
    packages = [
        ("fastapi", "fastapi"),
        ("pydantic", "pydantic"),
        ("requests", "requests"),
        ("PIL", "pillow"),
        ("yaml", "pyyaml"),
        ("edge_tts", "edge-tts"),
        ("loguru", "loguru"),
        ("dotenv", "python-dotenv"),
    ]
    
    for import_name, display_name in packages:
        ok, msg = check_python_package(import_name)
        print_status(display_name, ok, msg)
        results[display_name] = ok
    
    # 3. GPU加速
    print_header("GPU加速 (可选)")
    
    ok, msg = check_gpu()
    print_status("PyTorch CUDA", ok, msg)
    results["cuda"] = ok
    
    # 4. 本地服务
    print_header("本地服务 (可选)")
    
    services = [
        ("Ollama", "http://localhost:11434"),
        ("ComfyUI", "http://localhost:8188"),
        ("CosyVoice", "http://localhost:9880"),
    ]
    
    for name, url in services:
        ok, msg = check_service(url)
        print_status(name, ok, msg)
        results[name.lower()] = ok
    
    # 5. 项目文件
    print_header("项目文件")
    
    project_root = Path(__file__).parent.parent
    files = [
        ("config/settings.yaml", "配置文件"),
        ("src/main.py", "主程序"),
        ("src/webui.py", "Web界面"),
        ("data/projects", "项目目录"),
    ]
    
    for file_path, desc in files:
        full_path = project_root / file_path
        exists = full_path.exists()
        print_status(desc, exists, file_path)
        results[file_path] = exists
    
    # 确保项目目录存在
    projects_dir = project_root / "data" / "projects"
    if not projects_dir.exists():
        projects_dir.mkdir(parents=True, exist_ok=True)
        print(f"  {Colors.YELLOW}→ 已创建项目目录{Colors.RESET}")
    
    # 总结
    print(f"\n{Colors.BOLD}{'='*50}{Colors.RESET}")
    
    critical_ok = results.get("python", False) and results.get("ffmpeg", False)
    deps_ok = all(results.get(pkg, False) for _, pkg in packages)
    
    if critical_ok and deps_ok:
        print(f"{Colors.GREEN}[OK] 环境检查通过，可以启动程序{Colors.RESET}")
        return results
    else:
        if not results.get("ffmpeg", False):
            print(f"{Colors.RED}[X] FFmpeg未安装，视频合成功能将不可用{Colors.RESET}")
        if not deps_ok:
            missing = [pkg for _, pkg in packages if not results.get(pkg, False)]
            print(f"{Colors.RED}[X] 缺少依赖: {', '.join(missing)}{Colors.RESET}")
            print(f"  运行: pip install {' '.join(missing)}")
        
        return results

def install_missing_packages():
    """安装缺失的包"""
    print(f"\n{Colors.BLUE}正在安装缺失的依赖...{Colors.RESET}")
    
    project_root = Path(__file__).parent.parent
    requirements = project_root / "requirements.txt"
    
    if requirements.exists():
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
    else:
        print(f"{Colors.RED}requirements.txt 不存在{Colors.RESET}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="环境检查工具")
    parser.add_argument("--install", action="store_true", help="自动安装缺失的Python包")
    parser.add_argument("--quiet", action="store_true", help="静默模式，仅输出错误")
    args = parser.parse_args()
    
    results = run_checks()
    
    if args.install:
        install_missing_packages()
        print("\n重新检查...")
        results = run_checks()
    
    # 返回码: 0=全部通过, 1=有警告, 2=有错误
    critical_failed = not results.get("python", False) or not results.get("ffmpeg", False)
    sys.exit(2 if critical_failed else 0)
