@echo off
setlocal enabledelayedexpansion
chcp 936 >nul 2>&1
title Novel2Video Setup

echo ========================================
echo     Novel2Video - Setup
echo ========================================
echo.

cd /d "%~dp0"

:: Check Python
echo [1/5] Checking Python...
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo [ERROR] Python not installed or not in PATH
    echo Please download from https://www.python.org/downloads/
    goto end
)
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYVER=%%i
echo       Python %PYVER%

:: Create venv
echo.
echo [2/5] Creating virtual environment...
if not exist ".venv" (
    python -m venv .venv
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create venv
        goto end
    )
    echo       Venv created
) else (
    echo       Venv exists
)

:: Upgrade pip
echo.
echo [3/5] Upgrading pip...
.venv\Scripts\python.exe -m pip install --upgrade pip -q

:: Install deps
echo.
echo [4/5] Installing dependencies...
.venv\Scripts\pip.exe install -r requirements.txt -q
if !errorlevel! neq 0 (
    echo [WARN] Some deps failed, continuing...
)
:: Install edge-tts
.venv\Scripts\pip.exe install edge-tts -q
echo       Dependencies installed

:: Check PyTorch
echo.
echo [5/5] Checking PyTorch...
.venv\Scripts\python.exe -c "import torch; print(f'PyTorch {torch.__version__}')" 2>nul
if !errorlevel! neq 0 (
    echo       Installing PyTorch GPU...
    echo       (This may take a few minutes)
    .venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu128 -q
    if !errorlevel! neq 0 (
        echo [WARN] GPU version failed, trying CPU...
        .venv\Scripts\pip.exe install torch -q
    )
)

:: Check FFmpeg
echo.
echo ----------------------------------------
echo Checking FFmpeg...
where ffmpeg >nul 2>&1
if !errorlevel! neq 0 (
    if exist "tools\ffmpeg\bin\ffmpeg.exe" (
        echo       FFmpeg installed (local)
        goto ffmpeg_done
    )
    echo [INFO] FFmpeg not found, downloading...
    echo.
    .venv\Scripts\python.exe scripts\install_ffmpeg.py
    if !errorlevel! neq 0 (
        echo [WARN] FFmpeg auto-install failed
        echo.
        echo Please install FFmpeg manually:
        echo   Option 1 - Chocolatey: choco install ffmpeg
        echo   Option 2 - Scoop: scoop install ffmpeg
        echo   Option 3 - Download: https://www.gyan.dev/ffmpeg/builds/
        echo.
    ) else (
        echo       FFmpeg installed
    )
) else (
    for /f "tokens=3" %%i in ('ffmpeg -version 2^>^&1 ^| findstr /i "version"') do (
        echo       FFmpeg %%i (system)
        goto ffmpeg_done
    )
)
:ffmpeg_done

:: Create directories
echo.
echo Creating directories...
if not exist "data\projects" mkdir "data\projects"
if not exist "temp" mkdir "temp"
echo       Done

:: Create .env
if not exist ".env" (
    echo.
    echo Creating config...
    copy ".env.example" ".env" >nul 2>&1
    echo       Created .env - please edit and add API keys
)

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo Next steps:
echo   1. Edit .env file, add your video API keys
echo   2. Run start_webui.bat to start
echo.
echo Optional services (local):
echo   - Ollama: https://ollama.ai
echo   - ComfyUI: https://github.com/comfyanonymous/ComfyUI
echo   - CosyVoice: https://github.com/FunAudioLLM/CosyVoice
echo.

:end
pause
endlocal
