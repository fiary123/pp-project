# SmartPet One-Click Launcher
# Usage: powershell -ExecutionPolicy Bypass -File .\start.ps1

$PROJECT_ROOT = $PSScriptRoot
$FRONTEND_DIR = "$PROJECT_ROOT\pet-frontend"

Write-Host "[1/2] Starting Backend (FastAPI :8000)..." -ForegroundColor Green
Start-Process cmd -ArgumentList "/k", "cd /d `"$PROJECT_ROOT`" && conda activate pet_adoption && uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000"

Start-Sleep -Seconds 2

Write-Host "[2/2] Starting Frontend (Vite :5173)..." -ForegroundColor Cyan
Start-Process cmd -ArgumentList "/k", "cd /d `"$FRONTEND_DIR`" && npm run dev"

Write-Host ""
Write-Host "  Frontend : http://127.0.0.1:5173" -ForegroundColor White
Write-Host "  Backend  : http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  API Docs : http://127.0.0.1:8000/docs" -ForegroundColor White
