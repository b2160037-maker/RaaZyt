# publish.ps1 -- build + upload long video and 3 Shorts (shows live progress + saves a log)
$ProjectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $ProjectRoot
New-Item -ItemType Directory -Force -Path "run\logs" | Out-Null
$log = "run\logs\publish_$(Get-Date -Format yyyy-MM-dd).log"
$env:PYTHONUNBUFFERED = "1"
Write-Host "[$(Get-Date -Format HH:mm:ss)] Video ban rahi hai... isme 30-50 min lag sakte hain. Ruko mat." -ForegroundColor Cyan
Write-Host "   (Live progress niche aayega. Log: $log)" -ForegroundColor DarkGray
& ".\.venv\Scripts\python.exe" -u -m src.run_all 2>&1 | Tee-Object -FilePath $log
Write-Host "[$(Get-Date -Format HH:mm:ss)] Publish finished (upar 'ALL DONE' / video link dekho, ya error log me)." -ForegroundColor Green
