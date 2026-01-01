"""
Z-Image-Turbo 模型下载脚本

下载 Z-Image-Turbo 所需的模型文件到 ComfyUI 目录
模型来源: https://huggingface.co/Tongyi-MAI/Z-Image-Turbo

需要下载的文件:
- diffusion_models/z_image_turbo_bf16.safetensors (约 12GB)
- text_encoders/qwen_3_4b.safetensors (约 8GB)  
- vae/ae.safetensors (约 335MB)
"""
import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm


# 模型下载配置
MODELS = {
    "diffusion_models": {
        "z_image_turbo_bf16.safetensors": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors"
    },
    "text_encoders": {
        "qwen_3_4b.safetensors": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors"
    },
    "vae": {
        "ae.safetensors": "https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors"
    }
}


def get_comfyui_models_dir() -> Path:
    """获取 ComfyUI models 目录 - 优先使用项目内的 ComfyUI"""
    # 优先使用项目内的 ComfyUI
    script_dir = Path(__file__).parent.parent
    project_comfyui = script_dir / "tools" / "ComfyUI_windows_portable" / "ComfyUI" / "models"
    if project_comfyui.exists():
        return project_comfyui
    
    # 如果项目内没有，创建目录结构
    if (script_dir / "tools" / "ComfyUI_windows_portable" / "ComfyUI").exists():
        return project_comfyui
    
    # 尝试从环境变量获取
    comfyui_path = os.environ.get("COMFYUI_PATH")
    if comfyui_path:
        return Path(comfyui_path) / "models"
    
    # 常见安装路径
    common_paths = [
        Path.home() / "ComfyUI" / "models",
        Path("C:/ComfyUI/models"),
        Path("D:/ComfyUI/models"),
    ]
    
    for path in common_paths:
        if path.exists():
            return path
    
    # 默认使用项目内路径
    print(f"将下载到项目内 ComfyUI 目录: {project_comfyui}")
    return project_comfyui


def download_file(url: str, dest_path: Path, chunk_size: int = 8192) -> bool:
    """下载文件，支持断点续传"""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 检查是否已存在
    if dest_path.exists():
        print(f"文件已存在，跳过: {dest_path.name}")
        return True
    
    # 临时文件用于断点续传
    temp_path = dest_path.with_suffix(dest_path.suffix + ".tmp")
    
    # 获取已下载大小
    downloaded_size = 0
    if temp_path.exists():
        downloaded_size = temp_path.stat().st_size
    
    headers = {}
    if downloaded_size > 0:
        headers["Range"] = f"bytes={downloaded_size}-"
        print(f"断点续传，已下载: {downloaded_size / 1024 / 1024:.1f} MB")
    
    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # 处理断点续传响应
        if response.status_code == 416:  # Range Not Satisfiable
            # 文件已完整下载
            temp_path.rename(dest_path)
            return True
        
        response.raise_for_status()
        
        # 获取总大小
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
                desc=dest_path.name
            ) as pbar:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        # 下载完成，重命名
        temp_path.rename(dest_path)
        print(f"下载完成: {dest_path.name}")
        return True
        
    except Exception as e:
        print(f"下载失败 {dest_path.name}: {e}")
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("Z-Image-Turbo 模型下载工具")
    print("=" * 60)
    print()
    print("该模型是阿里通义实验室发布的高效图像生成模型")
    print("- 6B 参数，仅需 8 步即可生成高质量图像")
    print("- 支持 16GB 显存的消费级显卡")
    print("- 擅长生成照片级真实感图像")
    print()
    
    # 获取 ComfyUI 目录
    models_dir = get_comfyui_models_dir()
    print(f"ComfyUI models 目录: {models_dir}")
    print()
    
    # 允许用户自定义路径
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
            print(f"\n下载: {subdir}/{filename}")
            if download_file(url, dest_path):
                success_count += 1
    
    print()
    print("=" * 60)
    print(f"下载完成: {success_count}/{total_count} 个文件")
    
    if success_count == total_count:
        print("\n所有模型文件已就绪！")
        print("\n模型存放位置:")
        print(f"  - {models_dir}/diffusion_models/z_image_turbo_bf16.safetensors")
        print(f"  - {models_dir}/text_encoders/qwen_3_4b.safetensors")
        print(f"  - {models_dir}/vae/ae.safetensors")
        print("\n请确保 ComfyUI 已更新到最新版本以支持 Z-Image-Turbo")
    else:
        print("\n部分文件下载失败，请重新运行脚本继续下载")
    
    print("=" * 60)


if __name__ == "__main__":
    main()
