"""
CosyVoice 3 自动部署脚本

自动克隆 CosyVoice 仓库、安装依赖、下载模型。
部署到 tools/CosyVoice 目录，与 ComfyUI 并列。

模型: FunAudioLLM/Fun-CosyVoice3-0.5B-2512
仓库: https://github.com/FunAudioLLM/CosyVoice
"""
import os
import sys
import subprocess
from pathlib import Path


# 配置
COSYVOICE_REPO = "https://github.com/FunAudioLLM/CosyVoice.git"
MODEL_REPO = "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
MODEL_DIR_NAME = "Fun-CosyVoice3-0.5B"

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
COSYVOICE_DIR = PROJECT_ROOT / "tools" / "CosyVoice"
MODEL_DIR = COSYVOICE_DIR / "pretrained_models" / MODEL_DIR_NAME
VENV_DIR = COSYVOICE_DIR / ".venv"


def run_cmd(cmd, cwd=None, check=True):
    """运行命令并打印输出"""
    print(f"  > {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=False, text=True
    )
    if check and result.returncode != 0:
        print(f"  [Error] 命令失败 (exit {result.returncode})")
        return False
    return True


def step_clone_repo():
    """Step 1: 克隆 CosyVoice 仓库"""
    if COSYVOICE_DIR.exists() and (COSYVOICE_DIR / "cosyvoice").exists():
        print("[OK] CosyVoice 仓库已存在")
        return True

    print("[1] 克隆 CosyVoice 仓库...")
    # 先浅克隆，加快速度
    if not run_cmd(
        f'git clone --depth 1 "{COSYVOICE_REPO}" "{COSYVOICE_DIR}"',
        check=False
    ):
        print("[Error] 克隆仓库失败")
        return False

    # 初始化子模块
    run_cmd("git submodule update --init --recursive --depth 1", cwd=COSYVOICE_DIR, check=False)

    print("[OK] 仓库克隆完成")
    return True


def step_create_venv():
    """Step 2: 创建 Python 虚拟环境并安装依赖"""
    python_exe = VENV_DIR / "Scripts" / "python.exe"
    if python_exe.exists():
        print("[OK] CosyVoice 虚拟环境已存在")
        return True

    print("[2] 创建 CosyVoice Python 虚拟环境...")
    if not run_cmd(f'python -m venv "{VENV_DIR}"'):
        print("[Error] 创建虚拟环境失败")
        return False

    pip_exe = VENV_DIR / "Scripts" / "pip.exe"

    # 安装 PyTorch (GPU)
    print("    安装 PyTorch...")
    run_cmd(
        f'"{pip_exe}" install torch torchaudio --index-url https://download.pytorch.org/whl/cu128 -q',
        check=False
    )

    # 安装 CosyVoice 依赖
    req_file = COSYVOICE_DIR / "requirements.txt"
    if req_file.exists():
        print("    安装 CosyVoice 依赖...")
        run_cmd(f'"{pip_exe}" install -r "{req_file}" -q', check=False)

    # 安装额外依赖
    print("    安装 FastAPI 服务依赖...")
    run_cmd(f'"{pip_exe}" install fastapi uvicorn python-multipart -q', check=False)

    print("[OK] 依赖安装完成")
    return True


def step_download_model():
    """Step 3: 下载 CosyVoice 3 模型"""
    # 检查模型是否已存在（通过检测关键文件）
    if MODEL_DIR.exists() and any(MODEL_DIR.glob("*.pt")) or any(MODEL_DIR.glob("*.safetensors")):
        print("[OK] CosyVoice 3 模型已存在")
        return True

    print("[3] 下载 CosyVoice 3 模型...")
    print(f"    模型: {MODEL_REPO}")
    print(f"    目标: {MODEL_DIR}")

    pip_exe = VENV_DIR / "Scripts" / "pip.exe"
    python_exe = VENV_DIR / "Scripts" / "python.exe"

    # 确保 huggingface_hub 已安装
    run_cmd(f'"{pip_exe}" install huggingface_hub -q', check=False)

    # 使用 huggingface-cli 下载
    hf_mirror = os.environ.get("HF_MIRROR", "https://hf-mirror.com")
    env_str = f'set HF_ENDPOINT={hf_mirror} &&' if hf_mirror else ''

    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)

    download_cmd = (
        f'{env_str} "{python_exe}" -c "'
        f"from huggingface_hub import snapshot_download; "
        f"snapshot_download('{MODEL_REPO}', local_dir=r'{MODEL_DIR}')"
        f'"'
    )

    if not run_cmd(download_cmd, check=False):
        print("[Warning] huggingface_hub 下载失败，尝试 git clone...")
        model_url = f"{hf_mirror}/{MODEL_REPO}" if hf_mirror else f"https://huggingface.co/{MODEL_REPO}"
        run_cmd(f'git clone "{model_url}" "{MODEL_DIR}"', check=False)

    # 验证
    if MODEL_DIR.exists() and any(MODEL_DIR.iterdir()):
        print("[OK] 模型下载完成")
        return True
    else:
        print("[Error] 模型下载失败")
        return False


def main(auto_mode: bool = False):
    """主函数"""
    print("=" * 60)
    print("CosyVoice 3 自动部署工具")
    print("=" * 60)
    print()
    print("Fun-CosyVoice 3.0 - 0.5B 参数语音合成模型")
    print("- 9 种语言 + 18+ 中国方言")
    print("- 零样本声音克隆")
    print("- 情感/语速/音量指令控制")
    print("- 150ms 低延迟流式输出")
    print()

    # 检查是否全部就绪
    if auto_mode:
        python_exe = VENV_DIR / "Scripts" / "python.exe"
        model_ready = MODEL_DIR.exists() and any(MODEL_DIR.iterdir()) if MODEL_DIR.exists() else False
        if python_exe.exists() and model_ready:
            print("[OK] CosyVoice 3 已部署就绪")
            return True

    success = True
    success = step_clone_repo() and success
    success = step_create_venv() and success
    success = step_download_model() and success

    print()
    print("=" * 60)
    if success:
        print("[OK] CosyVoice 3 部署完成!")
        print()
        print(f"  仓库: {COSYVOICE_DIR}")
        print(f"  模型: {MODEL_DIR}")
        print(f"  环境: {VENV_DIR}")
        print()
        print("  启动命令:")
        python_exe = VENV_DIR / "Scripts" / "python.exe"
        server_py = COSYVOICE_DIR / "runtime" / "python" / "fastapi" / "server.py"
        print(f'  "{python_exe}" "{server_py}" --port 50000 --model_dir pretrained_models/{MODEL_DIR_NAME}')
    else:
        print("[Warning] 部分步骤失败，请检查错误信息")
    print("=" * 60)
    return success


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    result = main(auto_mode=auto)
    sys.exit(0 if result else 1)
