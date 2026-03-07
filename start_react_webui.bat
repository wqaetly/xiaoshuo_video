@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Novel2Video - React Web UI

echo ========================================
echo     Novel2Video - React Web UI
echo ========================================
echo.

cd /d "%~dp0"

REM ========================================
REM Step 1: Check Python virtual environment
REM ========================================
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

REM ========================================
REM Step 2: Check and install FastAPI dependencies
REM ========================================
.venv\Scripts\python.exe -c "import fastapi, uvicorn" 2>nul
if !errorlevel! neq 0 (
    echo [Info] Installing FastAPI dependencies...
    .venv\Scripts\pip.exe install fastapi uvicorn[standard] python-multipart websockets -q
    if !errorlevel! equ 0 (
        echo [OK] FastAPI dependencies installed
    ) else (
        echo [Error] Failed to install FastAPI dependencies
        goto end
    )
) else (
    echo [OK] FastAPI dependencies available
)

REM ========================================
REM Step 3: Check Node.js and npm
REM ========================================
where node >nul 2>&1
if !errorlevel! neq 0 (
    echo [Error] Node.js not installed or not in PATH
    echo Please download from https://nodejs.org/
    echo.
    echo [Info] Opening download page...
    start "" "https://nodejs.org/"
    goto end
) else (
    for /f "tokens=*" %%v in ('node --version') do echo [OK] Node.js %%v installed
)

REM ========================================
REM Step 4: Check and install frontend dependencies
REM ========================================
if not exist "web\node_modules" (
    echo [Info] Installing frontend dependencies...
    echo       This may take a few minutes...
    cd web
    npm install -q
    if !errorlevel! neq 0 (
        echo [Warning] Some npm packages failed, trying again...
        npm install
    )
    cd ..
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies available
)

REM ========================================
REM Step 5: Check FFmpeg
REM ========================================
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
    .venv\Scripts\python.exe scripts\install_ffmpeg.py 2>nul
    if !errorlevel! equ 0 (
        set FFMPEG_OK=1
        echo [OK] FFmpeg installed successfully
    ) else (
        echo [Warning] FFmpeg install failed - video composing unavailable
    )
)

REM ========================================
REM Step 6: Check PyTorch
REM ========================================
.venv\Scripts\python.exe -c "import torch" 2>nul
if !errorlevel! neq 0 (
    echo [Info] Installing PyTorch GPU version...
    .venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu128 -q
    if !errorlevel! neq 0 (
        echo [Warning] GPU version failed, trying CPU version...
        .venv\Scripts\pip.exe install torch -q
    )
    echo [OK] PyTorch installed
) else (
    echo [OK] PyTorch installed
)

REM Check edge-tts
.venv\Scripts\python.exe -c "import edge_tts" 2>nul
if !errorlevel! neq 0 (
    echo [Info] Installing edge-tts...
    .venv\Scripts\pip.exe install edge-tts -q
    echo [OK] edge-tts installed
) else (
    echo [OK] edge-tts installed
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
REM Step 7: Check ComfyUI installation and model
REM ========================================
echo.
echo Checking ComfyUI...
if not exist "tools\ComfyUI_windows_portable\run_nvidia_gpu.bat" (
    echo [Warning] ComfyUI not installed - image generation unavailable
    echo          Download from: https://github.com/comfyanonymous/ComfyUI/releases
    goto skip_comfyui
)
echo [OK] ComfyUI installed

REM Check Z-Image-Turbo model
set MODEL_OK=0
if exist "tools\ComfyUI_windows_portable\ComfyUI\models\diffusion_models\z_image_turbo_bf16.safetensors" (
    if exist "tools\ComfyUI_windows_portable\ComfyUI\models\text_encoders\qwen_3_4b.safetensors" (
        if exist "tools\ComfyUI_windows_portable\ComfyUI\models\vae\ae.safetensors" (
            set MODEL_OK=1
        )
    )
)
if !MODEL_OK! equ 1 (
    echo [OK] Z-Image-Turbo model available
) else (
    echo [Warning] Z-Image-Turbo model not found
    echo [Info] Attempting automatic download...
    .venv\Scripts\python.exe scripts\download_z_image_turbo.py
    if !errorlevel! equ 0 (
        echo [OK] Z-Image-Turbo model installed
    ) else (
        echo [Warning] Model download failed - manual download required
        echo          https://huggingface.co/Comfy-Org/z_image_turbo
    )
)

REM Copy default workflow
if exist "tools\ComfyUI_windows_portable\ComfyUI" (
    if not exist "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows" (
        mkdir "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows" 2>nul
    )
    copy /Y "config\comfyui_workflows\z_image_turbo_scene.json" "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows\z_image_turbo_scene.json" >nul 2>&1
    copy /Y "config\comfyui_workflows\z_image_i2l.json" "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows\z_image_i2l.json" >nul 2>&1
)

REM Check Z-Image-i2L plugin for character consistency
if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI_RH_ZImageI2L" (
    echo [OK] Z-Image-i2L plugin installed
) else (
    echo [Info] Installing Z-Image-i2L plugin for character consistency...
    if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes" (
        cd /d "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes"
        git clone https://github.com/HM-RunningHub/ComfyUI_RH_ZImageI2L.git 2>nul
        cd /d "%~dp0"
        if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI_RH_ZImageI2L" (
            echo [OK] Z-Image-i2L plugin installed
        ) else (
            echo [Warning] Plugin install failed - manual install required
            echo          https://github.com/HM-RunningHub/ComfyUI_RH_ZImageI2L
        )
    )
)

REM Check VideoHelperSuite plugin (for video output)
if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-VideoHelperSuite" (
    echo [OK] VideoHelperSuite plugin installed
) else (
    echo [Info] Installing VideoHelperSuite plugin for video output...
    if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes" (
        cd /d "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes"
        git clone https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git 2>nul
        cd /d "%~dp0"
        if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI-VideoHelperSuite" (
            echo [OK] VideoHelperSuite plugin installed
        ) else (
            echo [Warning] Plugin install failed - manual install required
            echo          https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite
        )
    )
)

REM Copy Wan I2V workflow
if exist "tools\ComfyUI_windows_portable\ComfyUI" (
    copy /Y "config\comfyui_workflows\wan2_i2v.json" "tools\ComfyUI_windows_portable\ComfyUI\user\default\workflows\wan2_i2v.json" >nul 2>&1
)

REM Check Yvann-Nodes plugin (audio reactive effects)
if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI_Yvann-Nodes" (
    echo [OK] Yvann-Nodes plugin installed ^(audio reactive^)
) else (
    echo [Info] Installing Yvann-Nodes plugin for audio reactive effects...
    if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes" (
        cd /d "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes"
        git clone https://github.com/yvann-ba/ComfyUI_Yvann-Nodes.git 2>nul
        cd /d "%~dp0"
        if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\ComfyUI_Yvann-Nodes" (
            echo [OK] Yvann-Nodes plugin installed
        ) else (
            echo [Warning] Plugin install failed - manual install required
            echo          https://github.com/yvann-ba/ComfyUI_Yvann-Nodes
        )
    )
)

REM Check SaltAI_AudioViz plugin (alternative audio reactive)
if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\SaltAI_AudioViz" (
    echo [OK] SaltAI AudioViz plugin installed
) else (
    echo [Info] Installing SaltAI AudioViz plugin...
    if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes" (
        cd /d "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes"
        git clone https://github.com/get-salt-AI/SaltAI_AudioViz.git 2>nul
        cd /d "%~dp0"
        if exist "tools\ComfyUI_windows_portable\ComfyUI\custom_nodes\SaltAI_AudioViz" (
            echo [OK] SaltAI AudioViz plugin installed
        ) else (
            echo [Warning] Plugin install failed - optional
        )
    )
)

REM ========================================
REM Check ComfyUI plugin dependencies
REM ========================================
echo.
echo Checking ComfyUI plugin dependencies...
set COMFY_PYTHON=tools\ComfyUI_windows_portable\python_embeded\python.exe

if exist "%COMFY_PYTHON%" (
    REM Check OpenCV (required by VideoHelperSuite)
    %COMFY_PYTHON% -c "import cv2" 2>nul
    if !errorlevel! neq 0 (
        echo [Info] Installing OpenCV for VideoHelperSuite...
        %COMFY_PYTHON% -m pip install opencv-python -q
        if !errorlevel! equ 0 (
            echo [OK] OpenCV installed
        ) else (
            echo [Warning] OpenCV install failed
        )
    ) else (
        echo [OK] OpenCV available
    )

    REM Check imageio-ffmpeg (required by VideoHelperSuite)
    %COMFY_PYTHON% -c "import imageio_ffmpeg" 2>nul
    if !errorlevel! neq 0 (
        echo [Info] Installing imageio-ffmpeg for VideoHelperSuite...
        %COMFY_PYTHON% -m pip install imageio-ffmpeg -q
        if !errorlevel! equ 0 (
            echo [OK] imageio-ffmpeg installed
        ) else (
            echo [Warning] imageio-ffmpeg install failed
        )
    ) else (
        echo [OK] imageio-ffmpeg available
    )

    REM Check diffsynth (required by ZImageI2L)
    %COMFY_PYTHON% -c "import diffsynth" 2>nul
    if !errorlevel! neq 0 (
        echo [Info] Installing diffsynth for ZImageI2L...
        %COMFY_PYTHON% -m pip install diffsynth -q
        if !errorlevel! equ 0 (
            echo [OK] diffsynth installed
        ) else (
            echo [Warning] diffsynth install failed
        )
    ) else (
        echo [OK] diffsynth available
    )
)

REM Start ComfyUI service
echo Checking ComfyUI service...
curl -s -o nul -w "" http://localhost:8188/ >nul 2>&1
if !errorlevel! neq 0 (
    echo [Info] Starting ComfyUI service...
    start /min "ComfyUI" cmd /c "cd /d "%~dp0tools\ComfyUI_windows_portable" && run_nvidia_gpu.bat"
    echo [Info] Waiting for ComfyUI to start...
    timeout /t 15 /nobreak >nul
    echo [OK] ComfyUI service started
) else (
    echo [OK] ComfyUI service running
)

:skip_comfyui

REM ========================================
REM Step 8: Check Ollama
REM ========================================
echo.
echo Checking Ollama service...
curl -s -o nul -w "" http://localhost:11434/api/tags >nul 2>&1
if !errorlevel! neq 0 (
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        echo [Info] Starting Ollama service...
        start /min "Ollama" ollama serve
        timeout /t 5 /nobreak >nul
        echo [OK] Ollama service started
    ) else (
        echo [Warning] Ollama not installed
        echo [Info] Installing Ollama...
        if not exist "temp" mkdir temp
        powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://ollama.com/download/OllamaSetup.exe' -OutFile 'temp\OllamaSetup.exe'}" 2>nul
        if exist "temp\OllamaSetup.exe" (
            echo        Running installer...
            start /wait temp\OllamaSetup.exe
            del /q temp\OllamaSetup.exe 2>nul
            where ollama >nul 2>&1
            if !errorlevel! equ 0 (
                echo [OK] Ollama installed
                start /min "Ollama" ollama serve
                timeout /t 5 /nobreak >nul
            )
        ) else (
            echo [Warning] Download failed - please install from https://ollama.com/download
        )
    )
) else (
    echo [OK] Ollama service running
)

REM Check GLM-4 model (better Chinese understanding for novel parsing)
curl -s http://localhost:11434/api/tags 2>nul | findstr /i "glm4" >nul 2>&1
if !errorlevel! neq 0 (
    where ollama >nul 2>&1
    if !errorlevel! equ 0 (
        curl -s -o nul -w "" http://localhost:11434/api/tags >nul 2>&1
        if !errorlevel! equ 0 (
            echo [Info] GLM-4 model not found, downloading...
            echo        This may take 5-15 minutes...
            ollama pull glm4:9b
            if !errorlevel! equ 0 (
                echo [OK] GLM-4 model downloaded
            ) else (
                echo [Warning] Model download failed - run: ollama pull glm4:9b
            )
        )
    )
) else (
    echo [OK] GLM-4 model available
)

REM ========================================
REM Step 9: Start services with Python script
REM ========================================
echo.
echo ========================================
echo Starting services...
echo ========================================
echo.

REM Bypass proxy for localhost
set NO_PROXY=localhost,127.0.0.1
set no_proxy=localhost,127.0.0.1

REM Use Python script to start services (waits for backend to be ready)
.venv\Scripts\python.exe scripts\start_webui.py

echo.
echo Press any key to exit...
pause >nul

:end
endlocal

