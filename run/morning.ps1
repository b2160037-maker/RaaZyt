# morning.ps1 -- pick today's topic (shows live progress + saves a log)
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot
New-Item -ItemType Directory -Force -Path "run\logs" | Out-Null
$log = "run\logs\morning_$(Get-Date -Format yyyy-MM-dd).log"
$env:PYTHONUNBUFFERED = "1"
Write-Host "[$(Get-Date -Format HH:mm:ss)] Topic chun raha hoon... (log: $log)" -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -u -m src.topic --announce 2>&1 | Tee-Object -FilePath $log
Write-Host "[$(Get-Date -Format HH:mm:ss)] Done." -ForegroundColor Green
