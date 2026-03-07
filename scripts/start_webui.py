"""
启动 Web UI 服务

优雅地启动后端和前端，确保后端就绪后再启动前端
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

# 尝试导入 httpx，如果没有就用 urllib
try:
    import httpx
    def check_health(url: str) -> bool:
        try:
            resp = httpx.get(url, timeout=2)
            return resp.status_code == 200
        except:
            return False
except ImportError:
    import urllib.request
    import urllib.error
    def check_health(url: str) -> bool:
        try:
            req = urllib.request.urlopen(url, timeout=2)
            return req.status == 200
        except:
            return False


def wait_for_service(url: str, name: str, timeout: int = 30) -> bool:
    """等待服务就绪"""
    print(f"       等待 {name} 就绪...", end="", flush=True)
    start = time.time()
    while time.time() - start < timeout:
        if check_health(url):
            print(" ✓")
            return True
        print(".", end="", flush=True)
        time.sleep(1)
    print(" 超时!")
    return False


def main():
    root_dir = Path(__file__).parent.parent
    venv_python = root_dir / ".venv" / "Scripts" / "python.exe"
    
    print("=" * 40)
    print("     Novel2Video - Web UI")
    print("=" * 40)
    print()
    
    # 1. 启动后端
    print("[1/2] 启动 FastAPI 后端...")
    backend_proc = subprocess.Popen(
        [str(venv_python), "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"],
        cwd=str(root_dir),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
    )
    
    # 等待后端就绪
    if not wait_for_service("http://localhost:8000/health", "后端"):
        print("[Error] 后端启动失败")
        return 1
    
    # 2. 启动前端
    print("[2/2] 启动 React 前端...")
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(root_dir / "web"),
        creationflags=subprocess.CREATE_NEW_CONSOLE,
        shell=True,
    )
    
    # 等待前端就绪
    if not wait_for_service("http://localhost:3000", "前端"):
        print("[Warning] 前端可能需要更长时间启动")
    
    print()
    print("=" * 40)
    print("  服务已启动!")
    print("=" * 40)
    print()
    print("  Frontend:  http://localhost:3000")
    print("  API Docs:  http://localhost:8000/docs")
    print()
    
    # 打开浏览器
    webbrowser.open("http://localhost:3000")
    
    print("按 Ctrl+C 退出...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n正在关闭服务...")
        backend_proc.terminate()
        frontend_proc.terminate()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

