@echo off
chcp 65001 >nul 2>&1
setlocal enabledelayedexpansion
title Novel2Video - Web UI

echo ========================================
echo     Novel2Video - Web UI
echo ========================================
echo.

cd /d "%~dp0"

REM Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [Error] Virtual environment not found
    echo.
    echo Please run setup.bat first
    echo Or manually execute:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    goto end
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

REM Check .env
if not exist ".env" (
    if exist ".env.example" (
        copy ".env.example" ".env" >nul
        echo [Info] Created .env file, please edit and add API keys
        echo.
    )
)

echo.
echo ========================================
echo Starting Web UI...
echo Browser: http://127.0.0.1:7860
echo.
echo Press Ctrl+C to stop
echo ========================================
echo.

.venv\Scripts\python.exe -m src.main ui

:end
endlocal
pause
