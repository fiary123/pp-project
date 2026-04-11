# ===== Gemini CLI safe launcher =====
#运行方式：powershell -ExecutionPolicy Bypass -File .\start-gemini.ps1


# 1) 清理可能导致 403 的 Cloud 环境变量
Remove-Item Env:GOOGLE_CLOUD_PROJECT -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_CLOUD_USE_VERTEXAI -ErrorAction SilentlyContinue
Remove-Item Env:GOOGLE_API_KEY -ErrorAction SilentlyContinue

# 如果你想固定走 AI Studio Key，可取消下一行注释并填入你的 key
# $env:GEMINI_API_KEY = "你的_GEMINI_API_KEY"

# 2) 切换到项目目录

# 3) 显示当前关键环境状态
Write-Host "Current directory: $(Get-Location)"
Write-Host "GOOGLE_CLOUD_PROJECT = $env:GOOGLE_CLOUD_PROJECT"
Write-Host "GOOGLE_CLOUD_USE_VERTEXAI = $env:GOOGLE_CLOUD_USE_VERTEXAI"
Write-Host "Starting Gemini CLI..." -ForegroundColor Green

# 4) 启动 Gemini CLI
gemini