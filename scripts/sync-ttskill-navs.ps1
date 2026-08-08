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
        # Summary mode omits holding_list_result and nav_history, so batch sync
        # must consume the complete Skills response.
        $output = & $ttskillCommand.Source invoke $Skill --action $Action --body $requestPath 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "ttskill $Skill failed with exit code $LASTEXITCODE."
        }
        $raw = ($output | ForEach-Object { [string]$_ }) -join "`n"
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

function Import-HapNav {
    param([object]$Payload)
    $headers = @{ 'X-HAP-Sync-Token' = $SyncToken }
    $uri = '{0}/api/v1/fund/integrations/ttskill/nav-info' -f $HapBaseUrl.TrimEnd('/')
    return Invoke-RestMethod -Method Post -Uri $uri -Headers $headers `
        -ContentType 'application/json; charset=utf-8' `
        -Body ($Payload | ConvertTo-Json -Depth 100 -Compress)
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
foreach ($holding in $holdings) {
    try {
        $fundCode = if ($holding.PSObject.Properties.Name -contains 'fundCode') { $holding.fundCode } else { $holding.fund_code }
        $fundName = if ($holding.PSObject.Properties.Name -contains 'fundName') { $holding.fundName } else { $holding.fund_name }
        $payload = Invoke-TtSkillJson -Skill 'TTFUND_NAV_INFO' -Action 'query' -Body @{
            fund_id = [string]$fundCode
            range = $Range
        }
        $null = Import-HapNav -Payload $payload
        $successCount++
        Write-Output ("Synced {0} {1}" -f $fundCode, $fundName)
    } catch {
        Write-Warning ("Failed {0} {1}: {2}" -f $fundCode, $fundName, $_.Exception.Message)
    }
}
Write-Output ("NAV sync finished: {0}/{1} funds processed." -f $successCount, $holdings.Count)
