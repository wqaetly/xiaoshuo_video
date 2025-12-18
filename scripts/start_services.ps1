# 启动所有本地服务
# PowerShell脚本

Write-Host "=== 启动本地服务 ===" -ForegroundColor Cyan
Write-Host ""

# 启动Ollama
Write-Host "[1/3] 检查Ollama服务..." -ForegroundColor Yellow
$ollamaRunning = Test-NetConnection -ComputerName localhost -Port 11434 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($ollamaRunning.TcpTestSucceeded) {
    Write-Host "  Ollama 已运行 (http://localhost:11434)" -ForegroundColor Green
} else {
    Write-Host "  启动Ollama..." -ForegroundColor Yellow
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 3
    Write-Host "  Ollama 已启动" -ForegroundColor Green
}

# 启动ComfyUI (如果存在)
Write-Host "`n[2/3] 检查ComfyUI服务..." -ForegroundColor Yellow
$comfyuiRunning = Test-NetConnection -ComputerName localhost -Port 8188 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($comfyuiRunning.TcpTestSucceeded) {
    Write-Host "  ComfyUI 已运行 (http://localhost:8188)" -ForegroundColor Green
} else {
    if (Test-Path ".\ComfyUI\main.py") {
        Write-Host "  启动ComfyUI..." -ForegroundColor Yellow
        Start-Process powershell -ArgumentList "-Command", "cd ComfyUI; python main.py" -WindowStyle Minimized
        Start-Sleep -Seconds 5
        Write-Host "  ComfyUI 已启动" -ForegroundColor Green
    } else {
        Write-Host "  ComfyUI 未安装，跳过" -ForegroundColor Yellow
    }
}

# 启动CosyVoice (如果存在)
Write-Host "`n[3/3] 检查CosyVoice服务..." -ForegroundColor Yellow
$cosyvoiceRunning = Test-NetConnection -ComputerName localhost -Port 9880 -WarningAction SilentlyContinue -ErrorAction SilentlyContinue
if ($cosyvoiceRunning.TcpTestSucceeded) {
    Write-Host "  CosyVoice 已运行 (http://localhost:9880)" -ForegroundColor Green
} else {
    if (Test-Path ".\CosyVoice\api.py") {
        Write-Host "  启动CosyVoice..." -ForegroundColor Yellow
        Start-Process powershell -ArgumentList "-Command", "cd CosyVoice; python api.py" -WindowStyle Minimized
        Start-Sleep -Seconds 5
        Write-Host "  CosyVoice 已启动" -ForegroundColor Green
    } else {
        Write-Host "  CosyVoice 未安装，跳过" -ForegroundColor Yellow
    }
}

Write-Host "`n=== 服务启动完成 ===" -ForegroundColor Green
Write-Host ""
Write-Host "现在可以运行: python -m src.main ui" -ForegroundColor Cyan
