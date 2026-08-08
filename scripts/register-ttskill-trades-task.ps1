[CmdletBinding()]
param(
    [string]$RepositoryPath = (Split-Path $PSScriptRoot -Parent),
    [string]$TaskName = 'HAP - Sync Fund Trades',
    [string]$HapBaseUrl = 'http://192.168.100.249:8088',
    [int]$Months = 1,
    [datetime]$StartAt = (Get-Date).Date.AddHours(22).AddMinutes(30)
)

$ErrorActionPreference = 'Stop'
$runner = Join-Path $RepositoryPath 'scripts\run-ttskill-trades-task.ps1'
if (-not (Test-Path -LiteralPath $runner)) { throw "Runner script not found: $runner" }
if ([string]::IsNullOrWhiteSpace($env:HAP_TTSKILL_SYNC_TOKEN)) {
    throw 'Set the HAP_TTSKILL_SYNC_TOKEN user environment variable before registering the task.'
}

$powershell = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$arguments = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -HapBaseUrl "{1}" -Months {2}' -f $runner, $HapBaseUrl, $Months
$action = New-ScheduledTaskAction -Execute $powershell -Argument $arguments -WorkingDirectory $RepositoryPath
$trigger = New-ScheduledTaskTrigger -Daily -At $StartAt
$principal = New-ScheduledTaskPrincipal -UserId ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME) -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 1) -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'HAP daily fund transaction sync through the local ttSkill login.' -Force | Out-Null
Write-Output "Registered: $TaskName"
Write-Output "Schedule: daily at $($StartAt.ToString('HH:mm'))"
Write-Output "Log: $env:LOCALAPPDATA\HAP\logs\ttskill-trades.log"
