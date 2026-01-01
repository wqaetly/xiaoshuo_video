"""下载 SDXL 模型到 ComfyUI"""
import os
import sys
from pathlib import Path
import requests
from tqdm import tqdm

# 模型配置
MODELS = {
    "animagine-xl-4.0": {
        "url": "https://huggingface.co/cagliostrolab/animagine-xl-4.0/resolve/main/animagine-xl-4.0.safetensors",
        "filename": "animagine-xl-4.0.safetensors",
        "size_gb": 6.5,
        "description": "Animagine XL 4.0 - 高质量动漫风格模型"
    },
    "sd_xl_base": {
        "url": "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors",
        "filename": "sd_xl_base_1.0.safetensors",
        "size_gb": 6.9,
        "description": "SDXL Base 1.0 - 官方基础模型"
    }
}

def get_comfyui_models_path():
    """获取 ComfyUI 模型路径"""
    script_dir = Path(__file__).parent.parent
    comfyui_path = script_dir / "tools" / "ComfyUI_windows_portable" / "ComfyUI" / "models" / "checkpoints"
    
    if not comfyui_path.exists():
        comfyui_path.mkdir(parents=True, exist_ok=True)
    
    return comfyui_path

def download_file(url: str, dest_path: Path, desc: str = "Downloading"):
    """下载文件并显示进度"""
    response = requests.get(url, stream=True, timeout=30)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))
    
    with open(dest_path, 'wb') as f:
        with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc) as pbar:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    pbar.update(len(chunk))

def check_model_exists(models_path: Path, filename: str) -> bool:
    """检查模型是否已存在"""
    model_path = models_path / filename
    return model_path.exists()

def download_model(model_key: str = "animagine-xl-4.0"):
    """下载指定模型"""
    if model_key not in MODELS:
        print(f"[Error] 未知模型: {model_key}")
        print(f"可用模型: {', '.join(MODELS.keys())}")
        return False
    
    model_info = MODELS[model_key]
    models_path = get_comfyui_models_path()
    dest_path = models_path / model_info["filename"]
    
    print(f"\n{'='*50}")
    print(f"  {model_info['description']}")
    print(f"{'='*50}")
    print(f"文件大小: ~{model_info['size_gb']} GB")
    print(f"保存路径: {dest_path}")
    print()
    
    if dest_path.exists():
        print(f"[OK] 模型已存在: {model_info['filename']}")
        return True
    
    print(f"[Info] 开始下载 {model_info['filename']}...")
    print("       这可能需要 10-30 分钟，取决于网络速度...")
    print()
    
    try:
        download_file(model_info["url"], dest_path, model_info["filename"])
        print(f"\n[OK] 模型下载完成: {model_info['filename']}")
        return True
    except KeyboardInterrupt:
        print("\n[Warning] 下载已取消")
        if dest_path.exists():
            dest_path.unlink()
        return False
    except Exception as e:
        print(f"\n[Error] 下载失败: {e}")
        if dest_path.exists():
            dest_path.unlink()
        return False

def list_available_models():
    """列出可用模型"""
    models_path = get_comfyui_models_path()
    
    print("\n可用模型:")
    print("-" * 60)
    for key, info in MODELS.items():
        status = "[已安装]" if check_model_exists(models_path, info["filename"]) else "[未安装]"
        print(f"  {key}: {info['description']} {status}")
    print("-" * 60)

def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="下载 SDXL 模型到 ComfyUI")
    parser.add_argument("--model", "-m", default="animagine-xl-4.0", 
                       choices=list(MODELS.keys()),
                       help="要下载的模型 (默认: animagine-xl-4.0)")
    parser.add_argument("--list", "-l", action="store_true",
                       help="列出可用模型")
    parser.add_argument("--check", "-c", action="store_true",
                       help="检查模型是否已安装")
    
    args = parser.parse_args()
    
    if args.list:
        list_available_models()
        return 0
    
    if args.check:
        models_path = get_comfyui_models_path()
        model_info = MODELS[args.model]
        if check_model_exists(models_path, model_info["filename"]):
            print(f"[OK] 模型已安装: {model_info['filename']}")
            return 0
        else:
            print(f"[Warning] 模型未安装: {model_info['filename']}")
            return 1
    
    success = download_model(args.model)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
