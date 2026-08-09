[CmdletBinding()]
param(
    [string]$HapBaseUrl = 'http://192.168.100.249:8088',
    [string]$SyncToken = $env:HAP_TTSKILL_SYNC_TOKEN,
    [int]$Months = 1,
    [int]$DetailDelaySeconds = 2,
    [switch]$PreviewOnly,
    [switch]$AutoConfirm,
    [string]$BundlePath = ''
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SyncToken)) { throw 'Set HAP_TTSKILL_SYNC_TOKEN or pass -SyncToken before synchronizing.' }
if ($Months -notin @(1, 3, 6, 12)) { throw 'Months must be one of 1, 3, 6, or 12.' }
if ($DetailDelaySeconds -lt 0 -or $DetailDelaySeconds -gt 60) { throw 'DetailDelaySeconds must be between 0 and 60.' }

$ttskillCommand = Get-Command ttskill -ErrorAction Stop
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Invoke-TtSkillJson {
    param([Parameter(Mandatory = $true)] [string]$Action, [Parameter(Mandatory = $true)] [hashtable]$Body)
    $requestPath = Join-Path $env:TEMP ("hap-trade-query-{0}.json" -f [guid]::NewGuid())
    $responsePath = Join-Path $env:TEMP ("hap-trade-response-{0}.json" -f [guid]::NewGuid())
    try {
        $request = @{ body = $Body } | ConvertTo-Json -Depth 20 -Compress
        [System.IO.File]::WriteAllText($requestPath, $request, $utf8NoBom)
        # Trade import needs the complete raw result, not the CLI summary envelope.
        # Read it from a file so PowerShell does not corrupt non-ASCII JSON in the pipe.
        $maxAttempts = 3
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            if (Test-Path -LiteralPath $responsePath) { Remove-Item -LiteralPath $responsePath -Force }
            $cliOutput = @(
                & $ttskillCommand.Source invoke TRADE_QUERY --action $Action --body $requestPath --output $responsePath 2>&1
            )
            if ($LASTEXITCODE -eq 0) { break }

            $errorText = ($cliOutput | ForEach-Object { [string]$_ }) -join "`n"
            if ($errorText -notmatch '429|调用次数|rate limit' -or $attempt -eq $maxAttempts) {
                throw "ttskill $Action failed with exit code $LASTEXITCODE. $errorText"
            }

            $retryDelay = 60
            Write-Warning ("ttskill {0} hit the rate limit; retrying in {1}s ({2}/{3})." -f $Action, $retryDelay, $attempt, $maxAttempts)
            Start-Sleep -Seconds $retryDelay
        }
        if (-not (Test-Path -LiteralPath $responsePath)) { throw "ttskill $Action did not write a JSON response file." }
        $rawText = [System.IO.File]::ReadAllText($responsePath)
        try {
            return ($rawText | ConvertFrom-Json)
        } catch {
            $logDirectory = Join-Path $env:LOCALAPPDATA 'HAP\logs'
            New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
            $rawText | Set-Content -LiteralPath (Join-Path $logDirectory "ttskill-$Action-response.txt") -Encoding UTF8
            throw "ttskill $Action returned invalid JSON. Raw response saved to $logDirectory."
        }
    } finally {
        if (Test-Path -LiteralPath $requestPath) { Remove-Item -LiteralPath $requestPath -Force }
        if (Test-Path -LiteralPath $responsePath) { Remove-Item -LiteralPath $responsePath -Force }
    }
}

function Invoke-HapImport {
    param([Parameter(Mandatory = $true)] [string]$Path, [Parameter(Mandatory = $true)] [object]$Payload)
    $json = $Payload | ConvertTo-Json -Depth 100 -Compress
    $headers = @{ 'X-HAP-Sync-Token' = $SyncToken }
    $endpoint = '{0}/api/v1/fund/integrations/ttskill/trades/{1}' -f $HapBaseUrl.TrimEnd('/'), $Path
    return Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers -ContentType 'application/json; charset=utf-8' -Body $json
}

function Find-TradeRows {
    param([object]$Value)
    if ($null -eq $Value) { return @() }
    if ($Value -is [System.Collections.IEnumerable] -and $Value -isnot [string]) {
        $items = @($Value)
        if ($items.Count -gt 0 -and ($items | Where-Object {
            $_.PSObject.Properties.Name -contains 'tradeId' -or
            $_.PSObject.Properties.Name -contains 'trade_id'
        })) { return $items }
        foreach ($item in $items) {
            $found = @(Find-TradeRows $item)
            if ($found.Count -gt 0) { return $found }
        }
        return @()
    }
    foreach ($property in @($Value.PSObject.Properties)) {
        $found = @(Find-TradeRows $property.Value)
        if ($found.Count -gt 0) { return $found }
    }
    return @()
}

$dateType = switch ($Months) {
    1 { '1' }
    3 { '6' }
    6 { '2' }
    12 { '3' }
}

$listPayload = Invoke-TtSkillJson -Action 'trade_list' -Body @{
    tradeType = 'fund'
    dateType = $dateType
    busType = '0'
    statu = '0'
    pageSize = 500
}
$rows = @(Find-TradeRows $listPayload.data.raw_result.body)
$rows = @($rows | Where-Object {
    $_.PSObject.Properties.Name -contains 'tradeId' -or
    $_.PSObject.Properties.Name -contains 'trade_id'
})
$tradeCount = $rows.Count
Write-Output ("Skills returned {0} trade rows." -f $tradeCount)
if ($tradeCount -eq 0) {
    Write-Output 'No fund trades returned. Nothing to import.'
    exit 0
}
$detailPayloads = @()
foreach ($row in $rows) {
    if ($detailPayloads.Count -gt 0 -and $DetailDelaySeconds -gt 0) {
        Start-Sleep -Seconds $DetailDelaySeconds
    }
    $tradeId = if ($row.PSObject.Properties.Name -contains 'tradeId') { $row.tradeId } else { $row.trade_id }
    $fundCode = if ($row.PSObject.Properties.Name -contains 'fundCode') { $row.fundCode } else { $row.fund_code }
    $detailPayloads += Invoke-TtSkillJson -Action 'trade_detail' -Body @{
        fundCode = [string]$fundCode
        tradeId = [string]$tradeId
        tradeType = 'fund'
        dateType = $dateType
        busType = '0'
        statu = '0'
        pageSize = 500
    }
}

$bundle = @{
    list_payload = $listPayload
    detail_payloads = $detailPayloads
    account_name = '天天基金'
}
if (-not [string]::IsNullOrWhiteSpace($BundlePath)) {
    $bundle | ConvertTo-Json -Depth 100 | Set-Content -LiteralPath $BundlePath -Encoding UTF8
    Write-Output ("Sync bundle saved to: {0}" -f $BundlePath)
}

$previewResponse = Invoke-HapImport -Path 'preview' -Payload $bundle
$preview = $previewResponse.data
Write-Output ("Trades: {0} | Create: {1} | Update: {2} | Skip: {3} | Error: {4}" -f $preview.total, $preview.create_count, $preview.update_count, $preview.skip_count, $preview.error_count)
$preview.items | Select-Object trade_id, fund_code, business_type, action, reason | Format-Table -AutoSize

if ($PreviewOnly) {
    Write-Output 'Preview mode finished. No data was written to HAP.'
    exit 0
}

if (-not $AutoConfirm) {
    $confirmation = Read-Host 'Import the previewed changes into HAP? Enter Y to confirm; any other input cancels'
    if ($confirmation -notin @('Y', 'y')) {
        Write-Output 'Import cancelled. No data was written to HAP.'
        exit 0
    }
} else {
    Write-Output 'Automatic mode enabled. Importing the previewed changes.'
}

$importResponse = Invoke-HapImport -Path 'import' -Payload $bundle
$import = $importResponse.data
Write-Output ("Import complete: Create {0} | Update {1} | Skip {2} | Error {3}" -f $import.create_count, $import.update_count, $import.skip_count, $import.error_count)
