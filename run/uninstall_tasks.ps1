# uninstall_tasks.ps1 -- remove the scheduled tasks.
foreach ($n in "RaazFiles-Morning","RaazFiles-Publish","RaazFiles-Weekly") {
    Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed $n"
}
