[CmdletBinding()]
param(
    [string]$HapBaseUrl = 'http://192.168.100.249:8088',
    [string]$SyncToken = $env:HAP_TTSKILL_SYNC_TOKEN,
    [ValidateSet('y', '3y', '6y', 'n', '2n', '3n', 'ln')]
    [string]$Range = 'y'
)

$ErrorActionPreference = 'Stop'
if ([string]::IsNullOrWhiteSpace($SyncToken)) {
    throw 'Set HAP_TTSKILL_SYNC_TOKEN or pass -SyncToken before synchronizing.'
}
$ttskillCommand = Get-Command ttskill -ErrorAction Stop
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Invoke-TtSkillJson {
    param([string]$Skill, [string]$Action, [hashtable]$Body)
    $requestPath = Join-Path $env:TEMP ("hap-nav-query-{0}.json" -f [guid]::NewGuid())
    try {
        [System.IO.File]::WriteAllText(
            $requestPath,
            ($Body | ConvertTo-Json -Compress),
            $utf8NoBom
        )
        # Read the complete UTF-8 stdout stream. PowerShell's call operator can
        # decode a large JSON response through the console code page.
        $processInfo = New-Object System.Diagnostics.ProcessStartInfo
        $processInfo.FileName = $env:ComSpec
        $cliCommand = '"{0}" invoke {1} --action {2} --body "{3}"' -f `
            $ttskillCommand.Source, $Skill, $Action, $requestPath
        $processInfo.Arguments = '/d /s /c "{0}"' -f $cliCommand
        $processInfo.UseShellExecute = $false
        $processInfo.CreateNoWindow = $true
        $processInfo.RedirectStandardOutput = $true
        $processInfo.RedirectStandardError = $true
        $processInfo.StandardOutputEncoding = $utf8NoBom
        $processInfo.StandardErrorEncoding = $utf8NoBom
        $process = New-Object System.Diagnostics.Process
        $process.StartInfo = $processInfo
        if (-not $process.Start()) { throw "Failed to start ttskill $Skill." }
        $standardOutput = $process.StandardOutput.ReadToEnd()
        $standardError = $process.StandardError.ReadToEnd()
        $process.WaitForExit()
        if ($process.ExitCode -ne 0) {
            throw "ttskill $Skill failed with exit code $($process.ExitCode): $standardError"
        }
        $raw = $standardOutput
        $start = $raw.IndexOf('{')
        $end = $raw.LastIndexOf('}')
        if ($start -lt 0 -or $end -le $start) {
            throw "ttskill $Skill did not return JSON."
        }
        return $raw.Substring($start, $end - $start + 1) | ConvertFrom-Json
    } finally {
        if (Test-Path -LiteralPath $requestPath) {
            Remove-Item -LiteralPath $requestPath -Force
        }
    }
}

function Invoke-HapJson {
    param(
        [string]$Path,
        [object]$Payload
    )
    $uri = '{0}{1}' -f $HapBaseUrl.TrimEnd('/'), $Path
    Add-Type -AssemblyName System.Net.Http
    $client = New-Object System.Net.Http.HttpClient
    $client.DefaultRequestHeaders.Add('X-HAP-Sync-Token', $SyncToken)
    $json = $Payload | ConvertTo-Json -Depth 100 -Compress
    $content = New-Object System.Net.Http.StringContent(
        $json,
        [System.Text.Encoding]::UTF8,
        'application/json'
    )
    try {
        $response = $client.PostAsync($uri, $content).GetAwaiter().GetResult()
        $responseText = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        if (-not $response.IsSuccessStatusCode) {
            throw "HAP returned HTTP $([int]$response.StatusCode): $responseText"
        }
        return $responseText | ConvertFrom-Json
    } finally {
        $content.Dispose()
        $client.Dispose()
    }
}

function Import-HapNav {
    param([object]$Payload)
    return Invoke-HapJson -Path '/api/v1/fund/integrations/ttskill/nav-info' -Payload $Payload
}

function Complete-HapNavSync {
    return Invoke-HapJson -Path '/api/v1/fund/integrations/ttskill/nav-sync-complete' -Payload @{}
}

function Find-FundHoldings {
    param([object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        $items = @($Value)
        $rows = @($items | Where-Object {
            $code = if ($_.PSObject.Properties.Name -contains 'fundCode') { $_.fundCode } else { $_.fund_code }
            [string]$code -match '^\d{6}$'
        })
        if ($rows.Count -gt 0) { return $rows }
        foreach ($item in $items) {
            $found = @(Find-FundHoldings $item)
            if ($found.Count -gt 0) { return $found }
        }
        return @()
    }
    foreach ($property in @($Value.PSObject.Properties)) {
        $found = @(Find-FundHoldings $property.Value)
        if ($found.Count -gt 0) { return $found }
    }
    return @()
}

$holdingPayload = Invoke-TtSkillJson -Skill 'ACCOUNT_HOLDING' -Action 'holding_list' -Body @{}
$holdings = @(Find-FundHoldings $holdingPayload.data.raw_result.body)
$holdings = @($holdings | Sort-Object {
    if ($_.PSObject.Properties.Name -contains 'fundCode') { $_.fundCode } else { $_.fund_code }
} -Unique)
if ($holdings.Count -eq 0) {
    throw 'ACCOUNT_HOLDING returned no six-digit fund holdings. Check the ttskill login or response format.'
}
$successCount = 0
$updatedCount = 0
foreach ($holding in $holdings) {
    try {
        $fundCode = if ($holding.PSObject.Properties.Name -contains 'fundCode') { $holding.fundCode } else { $holding.fund_code }
        $fundName = if ($holding.PSObject.Properties.Name -contains 'fundName') { $holding.fundName } else { $holding.fund_name }
        $payload = Invoke-TtSkillJson -Skill 'TTFUND_NAV_INFO' -Action 'query' -Body @{
            fund_id = [string]$fundCode
            range = $Range
        }
        $importResult = Import-HapNav -Payload $payload
        if ($importResult.data.updated -eq $true) {
            $updatedCount++
        }
        $successCount++
        Write-Output ("Synced {0} {1}" -f $fundCode, $fundName)
    } catch {
        Write-Warning ("Failed {0} {1}: {2}" -f $fundCode, $fundName, $_.Exception.Message)
    }
}
Write-Output ("NAV sync finished: {0}/{1} funds processed." -f $successCount, $holdings.Count)
if ($updatedCount -gt 0) {
    $automationResult = Complete-HapNavSync
    Write-Output ("AI automation: {0} - {1}" -f $automationResult.data.status, $automationResult.data.message)
} else {
    Write-Output 'AI automation skipped: no new NAV data was imported.'
}
