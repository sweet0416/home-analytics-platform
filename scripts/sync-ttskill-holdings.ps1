[CmdletBinding()]
param(
    [string]$HapBaseUrl = 'http://192.168.100.249:8088',

    [string]$SyncToken = $env:HAP_TTSKILL_SYNC_TOKEN
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SyncToken)) {
    throw 'Set HAP_TTSKILL_SYNC_TOKEN or pass -SyncToken before synchronizing.'
}

$ttskillCommand = Get-Command ttskill -ErrorAction Stop
$requestPath = Join-Path $env:TEMP ("ttskill-holdings-{0}.json" -f [guid]::NewGuid())
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

try {
    [System.IO.File]::WriteAllText($requestPath, '{}', $utf8NoBom)

    $processInfo = New-Object System.Diagnostics.ProcessStartInfo
    $processInfo.FileName = $env:ComSpec
    $cliCommand = '"{0}" invoke ACCOUNT_HOLDING --action holding_list --body "{1}"' -f `
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
    $endpoint = '{0}/api/v1/fund/integrations/ttskill/holdings' -f `
        $HapBaseUrl.TrimEnd('/')

    Add-Type -AssemblyName System.Net.Http
    $httpClient = New-Object System.Net.Http.HttpClient
    $httpClient.DefaultRequestHeaders.Add('X-HAP-Sync-Token', $SyncToken)
    $content = New-Object System.Net.Http.ByteArrayContent(
        , [System.Text.Encoding]::UTF8.GetBytes($apiBody)
    )
    $content.Headers.ContentType = New-Object System.Net.Http.Headers.MediaTypeHeaderValue(
        'application/json'
    )
    $content.Headers.ContentType.CharSet = 'utf-8'

    try {
        $httpResponse = $httpClient.PostAsync($endpoint, $content).GetAwaiter().GetResult()
        $responseBytes = $httpResponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()
        $responseText = [System.Text.Encoding]::UTF8.GetString($responseBytes)
        if (-not $httpResponse.IsSuccessStatusCode) {
            throw "HAP synchronization failed with HTTP $([int]$httpResponse.StatusCode): $responseText"
        }

        $response = $responseText | ConvertFrom-Json
        $response.data
    }
    finally {
        $content.Dispose()
        $httpClient.Dispose()
    }
}
finally {
    if (Test-Path -LiteralPath $requestPath) {
        Remove-Item -LiteralPath $requestPath -Force
    }
}
