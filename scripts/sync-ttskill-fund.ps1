[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^\d{6}$')]
    [string]$FundCode,

    [string]$HapBaseUrl = 'http://192.168.100.249:8088',

    [string]$SyncToken = $env:HAP_TTSKILL_SYNC_TOKEN
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SyncToken)) {
    throw 'Set HAP_TTSKILL_SYNC_TOKEN or pass -SyncToken before synchronizing.'
}

$ttskillCommand = Get-Command ttskill -ErrorAction Stop
$requestPath = Join-Path $env:TEMP ("ttskill-{0}-{1}.json" -f $FundCode, [guid]::NewGuid())
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

try {
    $requestJson = @{ fcode = $FundCode } | ConvertTo-Json -Compress
    [System.IO.File]::WriteAllText($requestPath, $requestJson, $utf8NoBom)

    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = $env:ComSpec
    $cliCommand = '"{0}" invoke TTFUND_BASE_INFOS --action query_by_code --body "{1}"' -f `
        $ttskillCommand.Source, $requestPath
    $processInfo.Arguments = '/d /s /c "{0}"' -f $cliCommand
    $processInfo.UseShellExecute = $false
    $processInfo.CreateNoWindow = $true
    $processInfo.RedirectStandardOutput = $true
    $processInfo.RedirectStandardError = $true
    $processInfo.StandardOutputEncoding = $utf8NoBom
    $processInfo.StandardErrorEncoding = $utf8NoBom

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $processInfo
    if (-not $process.Start()) {
        throw 'Failed to start ttskill.'
    }
    $standardOutput = $process.StandardOutput.ReadToEnd()
    $standardError = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    if ($process.ExitCode -ne 0) {
        throw "ttskill failed with exit code $($process.ExitCode): $standardError"
    }

    $skillPayload = $standardOutput | ConvertFrom-Json
    $apiBody = $skillPayload | ConvertTo-Json -Depth 100 -Compress
    $endpoint = '{0}/api/v1/fund/integrations/ttskill/base-infos' -f `
        $HapBaseUrl.TrimEnd('/')
    $headers = @{ 'X-HAP-Sync-Token' = $SyncToken }
    $response = Invoke-RestMethod `
        -Method Post `
        -Uri $endpoint `
        -Headers $headers `
        -ContentType 'application/json; charset=utf-8' `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($apiBody))

    $response.data
}
finally {
    if (Test-Path -LiteralPath $requestPath) {
        Remove-Item -LiteralPath $requestPath -Force
    }
}
