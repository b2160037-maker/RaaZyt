# setup.ps1 -- ONE-TIME setup on Windows. Run in PowerShell (right-click > Run with PowerShell,
# or:  powershell -ExecutionPolicy Bypass -File .\run\setup.ps1 )
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot
Write-Host "Project: $ProjectRoot" -ForegroundColor Cyan

# 1) Python check
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) { Write-Host "Python not found. Install Python 3.11+ from https://www.python.org/downloads/ (tick 'Add to PATH')." -ForegroundColor Red; exit 1 }
python --version

# 2) create venv + install deps
if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment (.venv) ..." -ForegroundColor Cyan
    python -m venv .venv
}
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

# 3) ffmpeg check
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "ffmpeg NOT found. Install it (needed for video):" -ForegroundColor Yellow
    Write-Host "   winget install --id=Gyan.FFmpeg -e   (then reopen PowerShell)" -ForegroundColor Yellow
} else { Write-Host "ffmpeg OK" -ForegroundColor Green }

# 4) .env check
if (-not (Test-Path ".\.env")) {
    Copy-Item ".\.env.example" ".\.env" -ErrorAction SilentlyContinue
    Write-Host "Created .env from template -- open .env and paste your API keys." -ForegroundColor Yellow
}
Write-Host "`nSetup done. Next: fill .env, keep token.json + client_secret.json in this folder, then run .\run\install_tasks.ps1" -ForegroundColor Green
