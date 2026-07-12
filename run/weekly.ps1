# weekly.ps1 -- weekly SEO pass (shows live progress + saves a log)
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot
New-Item -ItemType Directory -Force -Path "run\logs" | Out-Null
$log = "run\logs\weekly_$(Get-Date -Format yyyy-MM-dd).log"
$env:PYTHONUNBUFFERED = "1"
Write-Host "[$(Get-Date -Format HH:mm:ss)] Weekly SEO pass... (log: $log)" -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -u -m src.seo --weekly 2>&1 | Tee-Object -FilePath $log
Write-Host "[$(Get-Date -Format HH:mm:ss)] Done." -ForegroundColor Green
