@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Novel2Video - Web UI

echo ========================================
echo     Novel2Video - Web UI
echo ========================================
echo.

cd /d "%~dp0"

REM Check virtual environment, create if not exists
if not exist ".venv\Scripts\python.exe" (
    echo [Info] Virtual environment not found, setting up...
    echo.
    
    REM Check Python
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [Error] Python not installed or not in PATH
        echo Please download from https://www.python.org/downloads/
        goto end
    )
    
    REM Create venv
    echo [1/3] Creating virtual environment...
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [Error] Failed to create virtual environment
        goto end
    )
    echo       Done
    
    REM Upgrade pip
    echo [2/3] Upgrading pip...
    .venv\Scripts\python.exe -m pip install --upgrade pip -q
    
    REM Install dependencies
    echo [3/3] Installing dependencies...
    echo       This may take a few minutes...
    .venv\Scripts\pip.exe install -r requirements.txt -q
    if !errorlevel! neq 0 (
        echo [Warning] Some dependencies failed, continuing...
    )
    echo       Done
    echo.
)

echo Checking environment...
echo.

REM Check FFmpeg
set FFMPEG_OK=0
if exist "tools\ffmpeg\bin\ffmpeg.exe" (
    set FFMPEG_OK=1
    echo [OK] FFmpeg installed - project
)
where ffmpeg >nul 2>&1
if !errorlevel! equ 0 (
    set FFMPEG_OK=1
    echo [OK] FFmpeg installed - system
)
if !FFMPEG_OK! equ 0 (
    echo [Warning] FFmpeg not found - installing...
    .venv\Scripts\python.exe scripts\install_ffmpeg.py
    if !errorlevel! equ 0 (
        set FFMPEG_OK=1
        echo [OK] FFmpeg installed successfully
    ) else (
        echo [Warning] FFmpeg install failed - video composing unavailable
    )
)

REM Check PyTorch
.venv\Scripts\python.exe -c "import torch" 2>nul
if !errorlevel! neq 0 (
    echo [Info] Installing PyTorch GPU version...
    echo        This may take a few minutes...
    echo.
    .venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu128 -q
    if !errorlevel! neq 0 (
        echo [Warning] GPU version failed, trying CPU version...
        .venv\Scripts\pip.exe install torch -q
    )
    echo.
) else (
    echo [OK] PyTorch installed
)

REM Check edge-tts
.venv\Scripts\python.exe -c "import edge_tts" 2>nul
if !errorlevel! neq 0 (
    echo [Info] Installing edge-tts...
    .venv\Scripts\pip.exe install edge-tts -q
)

REM Check key dependencies
.venv\Scripts\python.exe -c "import gradio, pydantic, requests" 2>nul
if !errorlevel! neq 0 (
    echo [Info] Installing missing dependencies...
    .venv\Scripts\pip.exe install -r requirements.txt -q
)

REM Ensure directories exist
if not exist "data\projects" mkdir "data\projects"
if not exist "temp" mkdir "temp"

REM Check .env
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [Info] Created .env file, please edit and add API keys
        echo.
    )
)

REM ========================================
REM Step 1: Check ComfyUI installation
REM ========================================
echo.
echo Checking ComfyUI installation...
if not exist "tools\ComfyUI_windows_portable\run_nvidia_gpu.bat" (
    echo [Warning] ComfyUI not installed
    echo.
    echo ========================================
    echo   ComfyUI needs to be installed first
    echo ========================================
    echo.
    echo Please follow these steps:
    echo.
    echo 1. Download ComfyUI Portable from:
    echo    https://github.com/comfyanonymous/ComfyUI/releases/latest/download/ComfyUI_windows_portable_nvidia.7z
    echo.
    echo 2. Extract to: %~dp0tools\
    echo    ^(You should have: tools\ComfyUI_windows_portable\run_nvidia_gpu.bat^)
    echo.
    echo 3. Run this script again
    echo.
    echo [Info] Opening download page in browser...
    start "" "https://github.com/comfyanonymous/ComfyUI/releases/latest"
    echo.
    echo Press any key to continue without ComfyUI...
    pause >nul
    goto skip_comfyui
) else (
    echo [OK] ComfyUI installed
)

REM ========================================
REM Step 2: Check and download model BEFORE starting ComfyUI
REM ========================================
echo.
echo Checking image generation model...
set MODEL_OK=0

REM Check Z-Image-Turbo model files
if exist "tools\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\z_image_turbo_bf16.safetensors" (
    if exist "tools\ComfyUI_windows_portable\ComfyUI\models\text_encoders\qwen_3_4b.safetensors" (
        if exist "tools\ComfyUI_windows_portable\ComfyUI\models\vae\ae.safetensors" (
            set MODEL_OK=1
            echo [OK] Z-Image-Turbo model available
        )
    )
)

if !MODEL_OK! equ 0 (
    echo [Warning] Z-Image-Turbo model not found
    echo.
    echo ========================================
    echo   Image Model Download Required
    echo ========================================
    echo.
    echo Model: Z-Image-Turbo ^(Alibaba Tongyi, 6B params^)
    echo Size:  ~20 GB total
    echo Style: Photorealistic, fast 8-step generation
    echo.
    echo Attempting automatic download...
    echo.
    .venv\Scripts\python.exe scripts\download_z_image_turbo.py
    if !errorlevel! neq 0 (
        echo.
        echo [Warning] Automatic download failed ^(network issue^)
        echo.
        echo Please download manually from:
        echo   https://huggingface.co/Comfy-Org/z_image_turbo
        echo.
        echo Required files:
        echo   - diffusion_models/z_image_turbo_bf16.safetensors
        echo   - text_encoders/qwen_3_4b.safetensors
        echo   - vae/ae.safetensors
        echo.
        echo Save to: tools\ComfyUI_windows_portable\ComfyUI\models\
        echo.
        echo Press any key after downloading to continue...
        pause >nul
    ) else (
        echo [OK] Z-Image-Turbo model installed
    )
)

REM ========================================
REM Step 3: Install ComfyUI-Custom-Scripts plugin
REM ========================================
echo.
echo Checking ComfyUI plugins...
if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes" (
    if not exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Custom-Scripts" (
        echo [Info] Installing ComfyUI-Custom-Scripts plugin...
        cd /d "%~dp0tools\ComfyUI_windows_portable\ComfyUI\custom_nodes"
        git clone https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git >nul 2>&1
        cd /d "%~dp0"
        if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-Custom-Scripts" (
            echo [OK] ComfyUI-Custom-Scripts installed
        ) else (
            echo [Warning] Plugin install failed, please install manually
        )
    ) else (
        echo [OK] ComfyUI-Custom-Scripts available
    )
)

REM Copy default workflow to ComfyUI user folder
if exist "tools\ComfyUI_windows_portable\ComfyUI" (
    if not exist "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows" (
        mkdir "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows" 2>nul
    )
    copy /Y "config\comfyui_workflows\z_image_turbo_scene.json" "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows\z_image_turbo_scene.json" >nul 2>&1
    echo [OK] Default workflow configured
)

REM ========================================
REM Step 4: Start ComfyUI service
REM ========================================
echo.
echo Checking ComfyUI service...

curl -s -o nul -w "" http://localhost:8188/ >nul 2>&1
if !errorlevel! neq 0 (
    echo [Info] Starting ComfyUI service...
    start /min "ComfyUI" cmd /c "cd /d "%~dp0tools\ComfyUI_windows_portable" && run_nvidia_gpu.bat"
    echo [Info] Waiting for ComfyUI to start...
    timeout /t 15 /nobreak >nul
    
    REM Verify ComfyUI started
    curl -s -o nul -w "" http://localhost:8188/ >nul 2>&1
    if !errorlevel! equ 0 (
        echo [OK] ComfyUI service started
    ) else (
        echo [Warning] ComfyUI may still be starting, please wait...
    )
) else (
    echo [OK] ComfyUI service running
)

:skip_comfyui

REM Check Ollama
echo.
echo Checking Ollama service...
curl -s -o nul -w "" http://localhost:11434/api/tags >nul 2>&1
if !errorlevel! neq 0 (
    echo [Warning] Ollama service not running
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        echo [Info] Starting Ollama service...
        start /min "Ollama" ollama serve
        echo [Info] Waiting for Ollama to start...
        timeout /t 5 /nobreak >nul
        
        REM Verify Ollama started
        curl -s -o nul -w "" http://localhost:11434/api/tags >nul 2>&1
        if !errorlevel! equ 0 (
            echo [OK] Ollama service started
        ) else (
            echo [Warning] Ollama may still be starting, please wait...
        )
    ) else (
        echo [Warning] Ollama not installed
        echo [Info] Downloading and installing Ollama...
        
        REM Create temp directory
        if not exist "temp" mkdir temp
        
        REM Download Ollama installer
        echo        Downloading installer...
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'temp\OllamaSetup.exe'}" 2>nul
        
        if exist "temp\OllamaSetup.exe" (
            echo        Running installer...
            echo        Please follow the installation wizard...
            start /wait temp\OllamaSetup.exe
            
            REM Check if installation succeeded
            where ollama >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Ollama installed successfully
                echo [Info] Starting Ollama service...
                start /min "Ollama" ollama serve
                timeout /t 5 /nobreak >nul
            ) else (
                echo [Warning] Ollama installation may require restart
                echo          Please restart this script after installation completes
            )
            
            REM Cleanup
            del /q temp\OllamaSetup.exe 2>nul
        ) else (
            echo [Error] Failed to download Ollama
            echo         Please download manually from: https://ollama.com/download
        )
    )
) else (
    echo [OK] Ollama service running
)

REM Check if Ollama has required model
curl -s http://localhost:11434/api/tags 2>nul | findstr /i "qwen" >nul 2>&1
if !errorlevel! neq 0 (
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        curl -s -o nul -w "" http://localhost:11434/api/tags >nul 2>&1
        if !errorlevel! equ 0 (
            echo [Info] Qwen model not found, downloading...
            echo        This may take 10-30 minutes depending on network speed...
            ollama pull qwen2.5:14b
            if !errorlevel! equ 0 (
                echo [OK] Qwen model downloaded successfully
            ) else (
                echo [Warning] Model download failed, please run manually:
                echo          ollama pull qwen2.5:14b
            )
        )
    )
) else (
    echo [OK] Qwen model available
)

echo.
echo ========================================
echo Starting Web UI...
echo Browser: http://127.0.0.1:7860

REM Bypass proxy for localhost
set NO_PROXY=localhost,127.0.0.1
set no_proxy=localhost,127.0.0.1
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

.venv\Scripts\python.exe -m src.main ui

:end
endlocal
pause
