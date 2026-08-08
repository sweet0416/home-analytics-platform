[CmdletBinding()]
param(
    [string]$HapBaseUrl = 'http://192.168.100.249:8088',
    [int]$Months = 1
)

$ErrorActionPreference = 'Stop'
$scriptPath = Join-Path $PSScriptRoot 'sync-ttskill-trades.ps1'
$logDirectory = Join-Path $env:LOCALAPPDATA 'HAP\logs'
$logPath = Join-Path $logDirectory 'ttskill-trades.log'
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

$startedAt = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
Add-Content -LiteralPath $logPath -Value "[$startedAt] scheduled trade sync started"
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $scriptPath `
        -HapBaseUrl $HapBaseUrl -Months $Months -AutoConfirm *>&1 |
        Tee-Object -FilePath $logPath -Append
    if ($LASTEXITCODE -ne 0) { throw "sync script exited with code $LASTEXITCODE" }
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] scheduled trade sync completed"
} catch {
    Add-Content -LiteralPath $logPath -Value "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] scheduled trade sync failed: $($_.Exception.Message)"
    throw
}
