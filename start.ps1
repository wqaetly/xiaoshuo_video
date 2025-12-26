# Novel2Video - PowerShell 启动脚本
# 使用方法: 右键 -> 使用 PowerShell 运行

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "Novel2Video - Web UI"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "     小说转视频 - Web UI" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Set-Location $PSScriptRoot

# 检查虚拟环境
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[错误] 虚拟环境未创建" -ForegroundColor Red
    Write-Host ""
    Write-Host "请先运行 setup.bat 进行安装" -ForegroundColor Yellow
    Read-Host "按回车键退出"
    exit 1
}

Write-Host "正在检查环境..." -ForegroundColor Gray
Write-Host ""

# 检查 FFmpeg (项目内置或系统)
$projectFfmpeg = Join-Path $PSScriptRoot "tools\ffmpeg\bin\ffmpeg.exe"
if (Test-Path $projectFfmpeg) {
    Write-Host "[OK] FFmpeg 已安装 (项目内置)" -ForegroundColor Green
} else {
    $ffmpeg = Get-Command ffmpeg -ErrorAction SilentlyContinue
    if ($ffmpeg) {
        Write-Host "[OK] FFmpeg 已安装 (系统)" -ForegroundColor Green
    } else {
        Write-Host "[警告] FFmpeg 未安装 - 正在自动下载..." -ForegroundColor Yellow
        & .venv\Scripts\python.exe scripts\install_ffmpeg.py
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] FFmpeg 安装成功" -ForegroundColor Green
        } else {
            Write-Host "[警告] FFmpeg 安装失败 - 视频合成功能将不可用" -ForegroundColor Yellow
            Write-Host "       手动安装: choco install ffmpeg 或 scoop install ffmpeg" -ForegroundColor Gray
        }
    }
}

# 检查 PyTorch
$torchCheck = & .venv\Scripts\python.exe -c "import torch; print(f'PyTorch {torch.__version__}' + (' (CUDA)' if torch.cuda.is_available() else ' (CPU)'))" 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] $torchCheck" -ForegroundColor Green
} else {
    Write-Host "[提示] PyTorch 未安装，正在安装GPU版本..." -ForegroundColor Yellow
    & .venv\Scripts\pip.exe install torch --index-url https://download.pytorch.org/whl/cu128 -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[警告] GPU版本安装失败，尝试CPU版本..." -ForegroundColor Yellow
        & .venv\Scripts\pip.exe install torch -q
    }
}

# 检查 edge-tts
$edgeTtsCheck = & .venv\Scripts\python.exe -c "import edge_tts" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[提示] edge-tts 未安装，正在安装..." -ForegroundColor Yellow
    & .venv\Scripts\pip.exe install edge-tts -q
}

# 检查关键依赖
$depsCheck = & .venv\Scripts\python.exe -c "import gradio, pydantic, requests" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[提示] 部分依赖缺失，正在安装..." -ForegroundColor Yellow
    & .venv\Scripts\pip.exe install -r requirements.txt -q
}

# 确保目录存在
if (-not (Test-Path "data\projects")) {
    New-Item -ItemType Directory -Path "data\projects" -Force | Out-Null
}

# 检查 .env
if (-not (Test-Path ".env") -and (Test-Path ".env.example")) {
    Copy-Item ".env.example" ".env"
    Write-Host "[提示] 已创建.env文件，请编辑填入API密钥" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "启动 Web UI..." -ForegroundColor Green
Write-Host "浏览器打开: http://127.0.0.1:7860" -ForegroundColor White
Write-Host ""
Write-Host "按 Ctrl+C 停止服务" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

& .venv\Scripts\python.exe -m src.main ui

Read-Host "按回车键退出"
