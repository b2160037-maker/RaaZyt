# install_tasks.ps1 -- register the 3 automatic tasks in Windows Task Scheduler.
# Right-click PowerShell > "Run as Administrator", then:
#   powershell -ExecutionPolicy Bypass -File .\run\install_tasks.ps1
$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path $PSScriptRoot -Parent
$run = Join-Path $ProjectRoot "run"

function Add-RaazTask($name, $script, $trigger) {
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$run\$script`""
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -WakeToRun `
        -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
        -ExecutionTimeLimit (New-TimeSpan -Hours 3)
    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger `
        -Settings $settings -Description "RAAZ FILES YouTube automation" -Force | Out-Null
    Write-Host "Installed task: $name" -ForegroundColor Green
}

# Times are your PC's LOCAL time. Task Scheduler runs EXACTLY on time (no GitHub delay).
Add-RaazTask "RaazFiles-Morning" "morning.ps1" (New-ScheduledTaskTrigger -Daily -At 6:00AM)
Add-RaazTask "RaazFiles-Publish" "publish.ps1" (New-ScheduledTaskTrigger -Daily -At 12:00PM)
Add-RaazTask "RaazFiles-Weekly"  "weekly.ps1"  (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 10:00AM)

Write-Host "`nAll tasks installed. '-StartWhenAvailable' means if the PC was OFF at the time, the task runs as soon as you turn it on. See them in Task Scheduler." -ForegroundColor Cyan
