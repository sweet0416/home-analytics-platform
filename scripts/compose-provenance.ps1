[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]] $ComposeArgs
)

$ErrorActionPreference = "Stop"

$env:HAP_GIT_SHA = (& git rev-parse HEAD).Trim()
$env:HAP_BUILD_TIME = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

if ([string]::IsNullOrWhiteSpace($env:HAP_BACKEND_IMAGE)) {
    $env:HAP_BACKEND_IMAGE = "hap-backend:local"
}
if ([string]::IsNullOrWhiteSpace($env:HAP_FRONTEND_IMAGE)) {
    $env:HAP_FRONTEND_IMAGE = "hap-frontend:local"
}
if ([string]::IsNullOrWhiteSpace($env:HAP_TTSKILL_IMAGE)) {
    $env:HAP_TTSKILL_IMAGE = "hap-ttskill-agent:local"
}

& docker compose @ComposeArgs
exit $LASTEXITCODE
