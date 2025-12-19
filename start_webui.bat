@echo off
setlocal enabledelayedexpansion
title Novel2Video - Web UI

echo ========================================
echo     Novel to Video - Web UI
echo ========================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Error] Virtual environment not found
    echo.
    echo Please run these commands first:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    goto end
)

echo Checking dependencies...
.venv\Scripts\python.exe -c "import torch" 2>nul
if !errorlevel! neq 0 (
    echo.
    echo [Warning] PyTorch not installed
    echo.
    echo Installing PyTorch GPU version CUDA 12.8 ...
    echo This may take a few minutes...
    echo.
    .venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cu128
    if !errorlevel! neq 0 (
        echo.
        echo [Error] PyTorch installation failed
        echo Please install manually:
        echo   .venv\Scripts\pip install torch --index-url https://download.pytorch.org/whl/cu128
        echo.
        goto end
    )
    echo.
)

echo Starting Web UI...
echo Open browser: http://127.0.0.1:7860
echo.
echo Press Ctrl+C to stop
echo ========================================
.venv\Scripts\python.exe -m src.main ui

:end
pause
endlocal
