# 小说转视频 - 环境安装脚本
# PowerShell脚本

Write-Host "=== 小说转视频 - 环境安装 ===" -ForegroundColor Cyan
Write-Host ""

# 检查Python版本
Write-Host "[1/5] 检查Python环境..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "错误: 未找到Python，请先安装Python 3.10+" -ForegroundColor Red
    exit 1
}
Write-Host "  Python版本: $pythonVersion" -ForegroundColor Green

# 创建虚拟环境
Write-Host "`n[2/5] 创建虚拟环境..." -ForegroundColor Yellow
if (!(Test-Path "venv")) {
    python -m venv venv
    Write-Host "  虚拟环境创建成功" -ForegroundColor Green
} else {
    Write-Host "  虚拟环境已存在" -ForegroundColor Green
}

# 激活虚拟环境
Write-Host "`n[3/5] 激活虚拟环境..." -ForegroundColor Yellow
.\venv\Scripts\Activate.ps1

# 安装依赖
Write-Host "`n[4/5] 安装依赖..." -ForegroundColor Yellow
pip install -r requirements.txt

# 检查外部服务
Write-Host "`n[5/5] 检查外部服务..." -ForegroundColor Yellow

# 检查Ollama
$ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaInstalled) {
    Write-Host "  Ollama: 已安装" -ForegroundColor Green
    Write-Host "  提示: 运行 'ollama pull glm4:9b' 下载模型" -ForegroundColor Cyan
} else {
    Write-Host "  Ollama: 未安装" -ForegroundColor Yellow
    Write-Host "  请从 https://ollama.com/download 安装" -ForegroundColor Cyan
}

# 检查FFmpeg
$ffmpegInstalled = Get-Command ffmpeg -ErrorAction SilentlyContinue
if ($ffmpegInstalled) {
    Write-Host "  FFmpeg: 已安装" -ForegroundColor Green
} else {
    Write-Host "  FFmpeg: 未安装" -ForegroundColor Yellow
    Write-Host "  请从 https://ffmpeg.org/download.html 安装" -ForegroundColor Cyan
}

Write-Host "`n=== 安装完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Cyan
Write-Host "  1. 配置 .env 文件 (复制 .env.example)"
Write-Host "  2. 启动本地服务 (Ollama, ComfyUI, CosyVoice)"
Write-Host "  3. 运行 'python -m src.main ui' 启动Web界面"
Write-Host ""
