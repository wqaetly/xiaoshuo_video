"""
Wan 2.2 模型下载脚本

下载 Wan 2.2 Image-to-Video (14B MoE) 所需的模型文件到 ComfyUI 目录。
模型来源: https://huggingface.co/Comfy-Org/Wan_2.2_ComfyUI_repackaged

Wan 2.2 使用 MoE 架构 (高噪声+低噪声双专家)，画质和运动表现大幅提升。

需要下载的文件:
- diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors (~14GB)
- diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors (~14GB)
- text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors (~5GB)
- vae/wan_2.1_vae.safetensors (~300MB)
- clip_vision/clip_vision_h.safetensors (~3.9GB)
"""
import os
import sys
from pathlib import Path

import requests
from tqdm import tqdm


# 模型下载配置
HF_BASE = os.environ.get("HF_MIRROR", "https://hf-mirror.com")
REPO_22 = "Comfy-Org/Wan_2.2_ComfyUI_repackaged"
REPO_21 = "Comfy-Org/Wan_2.1_ComfyUI_repackaged"

MODELS = {
    "diffusion_models": {
        "wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors":
            f"{HF_BASE}/{REPO_22}/resolve/main/split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors":
            f"{HF_BASE}/{REPO_22}/resolve/main/split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
    },
    "text_encoders": {
        "umt5_xxl_fp8_e4m3fn_scaled.safetensors":
            f"{HF_BASE}/{REPO_22}/resolve/main/split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors"
    },
    "vae": {
        "wan_2.1_vae.safetensors":
            f"{HF_BASE}/{REPO_22}/resolve/main/split_files/vae/wan_2.1_vae.safetensors"
    },
    "clip_vision": {
        "clip_vision_h.safetensors":
            f"{HF_BASE}/{REPO_21}/resolve/main/split_files/clip_vision/clip_vision_h.safetensors"
    },
}


def get_comfyui_models_dir() -> Path:
    """获取 ComfyUI models 目录 - 优先使用项目内的 ComfyUI"""
    script_dir = Path(__file__).parent.parent
    project_comfyui = script_dir / "tools" / "ComfyUI_windows_portable" / "ComfyUI" / "models"
    if project_comfyui.exists():
        return project_comfyui

    if (script_dir / "tools" / "ComfyUI_windows_portable" / "ComfyUI").exists():
        return project_comfyui

    comfyui_path = os.environ.get("COMFYUI_PATH")
    if comfyui_path:
        return Path(comfyui_path) / "models"

    common_paths = [
        Path.home() / "ComfyUI" / "models",
        Path("C:/ComfyUI/models"),
        Path("D:/ComfyUI/models"),
    ]
    for path in common_paths:
        if path.exists():
            return path

    print(f"将下载到项目内 ComfyUI 目录: {project_comfyui}")
    return project_comfyui


def download_file(url: str, dest_path: Path, chunk_size: int = 8192) -> bool:
    """下载文件，支持断点续传"""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        print(f"  文件已存在，跳过: {dest_path.name}")
        return True

    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")

    downloaded_size = 0
    if temp_path.exists():
        downloaded_size = temp_path.stat().st_size

    headers = {}
    if downloaded_size > 0:
        headers["Range"] = f"bytes={downloaded_size}-"
        print(f"  断点续传，已下载: {downloaded_size / 1024 / 1024:.1f} MB")

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)

        if response.status_code == 416:
            temp_path.rename(dest_path)
            return True

        response.raise_for_status()

        total_size = int(response.headers.get("content-length", 0))
        if downloaded_size > 0:
            total_size += downloaded_size

        mode = "ab" if downloaded_size > 0 else "wb"

        with open(temp_path, mode) as f:
            with tqdm(
                total=total_size,
                initial=downloaded_size,
                unit="B",
                unit_scale=True,
                desc=dest_path.name,
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))

        temp_path.rename(dest_path)
        print(f"  下载完成: {dest_path.name}")
        return True

    except Exception as e:
        print(f"  下载失败 {dest_path.name}: {e}")
        return False


def main(auto_mode: bool = False):
    """主函数
    
    Args:
        auto_mode: 自动模式，跳过交互提示，检测到模型已存在时直接退出
    """
    print("=" * 60)
    print("Wan 2.2 Image-to-Video 模型下载工具")
    print("=" * 60)
    print()
    print("Wan 2.2 使用 MoE (混合专家) 架构")
    print("- 27B 总参数, 每步仅激活 14B (高/低噪声双专家)")
    print("- 相比 2.1 画质和运动表现大幅提升")
    print("- 使用 FP8 量化版适配 16GB 显存")
    print("- 支持 480P/720P 分辨率")
    print()

    if HF_BASE != "https://hf-mirror.com":
        print(f"使用镜像源: {HF_BASE}")
        print()

    models_dir = get_comfyui_models_dir()
    print(f"ComfyUI models 目录: {models_dir}")
    print()

    # 自动模式: 检查是否全部存在，是则直接退出
    if auto_mode:
        all_exist = True
        for subdir, files in MODELS.items():
            for filename in files:
                if not (models_dir / subdir / filename).exists():
                    all_exist = False
                    break
            if not all_exist:
                break
        if all_exist:
            print("[OK] Wan 2.1 模型文件已就绪，跳过下载")
            return

    if not auto_mode:
        custom_path = input("按 Enter 使用上述路径，或输入自定义路径: ").strip()
        if custom_path:
            models_dir = Path(custom_path)

    print()
    print("开始下载模型文件...")
    print("-" * 60)

    success_count = 0
    total_count = sum(len(files) for files in MODELS.values())

    for subdir, files in MODELS.items():
        for filename, url in files.items():
            dest_path = models_dir / subdir / filename
            print(f"\n[{subdir}/{filename}]")
            if download_file(url, dest_path):
                success_count += 1

    print()
    print("=" * 60)
    print(f"下载完成: {success_count}/{total_count} 个文件")

    if success_count == total_count:
        print("\n所有模型文件已就绪!")
        print("\n模型存放位置:")
        for subdir, files in MODELS.items():
            for filename in files:
                print(f"  - {models_dir / subdir / filename}")
        print("\n请重启 ComfyUI 以加载新模型")
    else:
        print("\n部分文件下载失败，请重新运行脚本继续下载")

    print("=" * 60)


if __name__ == "__main__":
    auto = "--auto" in sys.argv
    main(auto_mode=auto)
