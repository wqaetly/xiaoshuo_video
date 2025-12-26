"""
FFmpeg 自动下载安装脚本
将 FFmpeg 下载到项目目录，无需修改系统环境变量
"""
import os
import sys
import zipfile
import shutil
import urllib.request
import tempfile
from pathlib import Path

# FFmpeg 下载地址 (Windows)
FFMPEG_URLS = {
    "win32": {
        "url": "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
        "mirror": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
    },
    "darwin": {
        "url": "https://evermeet.cx/ffmpeg/getrelease/zip",
        "note": "macOS 建议使用 brew install ffmpeg",
    },
    "linux": {
        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "note": "Linux 建议使用包管理器安装",
    }
}

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
FFMPEG_DIR = PROJECT_ROOT / "tools" / "ffmpeg"


class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_info(msg: str):
    print(f"{Colors.BLUE}[INFO]{Colors.RESET} {msg}")


def print_success(msg: str):
    print(f"{Colors.GREEN}[OK]{Colors.RESET} {msg}")


def print_warning(msg: str):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {msg}")


def print_error(msg: str):
    print(f"{Colors.RED}[ERROR]{Colors.RESET} {msg}")


def get_ffmpeg_paths() -> tuple:
    """获取 FFmpeg 可执行文件路径"""
    if sys.platform == "win32":
        ffmpeg = FFMPEG_DIR / "bin" / "ffmpeg.exe"
        ffprobe = FFMPEG_DIR / "bin" / "ffprobe.exe"
    else:
        ffmpeg = FFMPEG_DIR / "ffmpeg"
        ffprobe = FFMPEG_DIR / "ffprobe"
    return ffmpeg, ffprobe


def check_ffmpeg_installed() -> bool:
    """检查 FFmpeg 是否已安装在项目目录"""
    ffmpeg, ffprobe = get_ffmpeg_paths()
    return ffmpeg.exists() and ffprobe.exists()


def check_system_ffmpeg() -> bool:
    """检查系统是否已安装 FFmpeg"""
    return shutil.which("ffmpeg") is not None


def download_with_progress(url: str, dest: Path, desc: str = "下载中"):
    """带进度显示的下载"""
    print_info(f"{desc}: {url}")
    
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total_size / (1024 * 1024)
            sys.stdout.write(f"\r       {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)")
            sys.stdout.flush()
    
    try:
        urllib.request.urlretrieve(url, dest, progress_hook)
        print()  # 换行
        return True
    except Exception as e:
        print()
        print_error(f"下载失败: {e}")
        return False


def install_ffmpeg_windows() -> bool:
    """Windows 平台安装 FFmpeg"""
    urls = FFMPEG_URLS["win32"]
    
    # 创建目标目录
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 下载到临时文件
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_file = temp_path / "ffmpeg.zip"
        
        # 尝试主下载地址
        print_info("正在下载 FFmpeg...")
        if not download_with_progress(urls["url"], zip_file, "从官方源下载"):
            # 尝试镜像
            print_warning("官方源下载失败，尝试镜像...")
            if not download_with_progress(urls["mirror"], zip_file, "从镜像下载"):
                return False
        
        # 解压
        print_info("正在解压...")
        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                zf.extractall(temp_path)
            
            # 找到解压后的目录 (通常是 ffmpeg-x.x-essentials_build)
            extracted_dirs = [d for d in temp_path.iterdir() if d.is_dir() and "ffmpeg" in d.name.lower()]
            if not extracted_dirs:
                print_error("解压后未找到 FFmpeg 目录")
                return False
            
            extracted_dir = extracted_dirs[0]
            
            # 复制 bin 目录
            src_bin = extracted_dir / "bin"
            if not src_bin.exists():
                # 有些版本直接在根目录
                src_bin = extracted_dir
            
            dest_bin = FFMPEG_DIR / "bin"
            dest_bin.mkdir(parents=True, exist_ok=True)
            
            # 复制可执行文件
            for exe in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
                src_file = src_bin / exe
                if src_file.exists():
                    shutil.copy2(src_file, dest_bin / exe)
                    print_success(f"已安装: {exe}")
            
            return True
            
        except Exception as e:
            print_error(f"解压失败: {e}")
            return False


def install_ffmpeg() -> bool:
    """安装 FFmpeg 到项目目录"""
    print(f"\n{Colors.BOLD}{'='*50}")
    print("   FFmpeg 自动安装")
    print(f"{'='*50}{Colors.RESET}\n")
    
    # 检查是否已安装
    if check_ffmpeg_installed():
        ffmpeg, _ = get_ffmpeg_paths()
        print_success(f"FFmpeg 已安装: {ffmpeg}")
        return True
    
    # 检查系统 FFmpeg
    if check_system_ffmpeg():
        print_info("检测到系统已安装 FFmpeg")
        print_info("如需使用项目内置版本，请删除系统 FFmpeg 后重新运行")
        return True
    
    # 根据平台安装
    if sys.platform == "win32":
        success = install_ffmpeg_windows()
    elif sys.platform == "darwin":
        print_warning("macOS 平台建议使用 Homebrew 安装:")
        print("       brew install ffmpeg")
        print_info("或者手动下载并放置到 tools/ffmpeg/ 目录")
        return False
    else:
        print_warning("Linux 平台建议使用包管理器安装:")
        print("       Ubuntu/Debian: sudo apt install ffmpeg")
        print("       CentOS/RHEL: sudo yum install ffmpeg")
        print("       Arch: sudo pacman -S ffmpeg")
        return False
    
    if success:
        print(f"\n{Colors.GREEN}{'='*50}")
        print("   FFmpeg 安装完成!")
        print(f"{'='*50}{Colors.RESET}\n")
        ffmpeg, ffprobe = get_ffmpeg_paths()
        print(f"  FFmpeg:  {ffmpeg}")
        print(f"  FFprobe: {ffprobe}")
        print()
    
    return success


def get_ffmpeg_path() -> str:
    """获取 FFmpeg 路径 (供其他模块调用)"""
    ffmpeg, _ = get_ffmpeg_paths()
    if ffmpeg.exists():
        return str(ffmpeg)
    # 回退到系统路径
    system_ffmpeg = shutil.which("ffmpeg")
    return system_ffmpeg or "ffmpeg"


def get_ffprobe_path() -> str:
    """获取 FFprobe 路径 (供其他模块调用)"""
    _, ffprobe = get_ffmpeg_paths()
    if ffprobe.exists():
        return str(ffprobe)
    # 回退到系统路径
    system_ffprobe = shutil.which("ffprobe")
    return system_ffprobe or "ffprobe"


if __name__ == "__main__":
    success = install_ffmpeg()
    sys.exit(0 if success else 1)
