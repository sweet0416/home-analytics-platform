[CmdletBinding()]
param(
    [string]$HapBaseUrl = 'http://192.168.100.249:8088',
    [string]$SyncToken = $env:HAP_TTSKILL_SYNC_TOKEN,
    [int]$Months = 1,
    [switch]$PreviewOnly
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SyncToken)) {
    throw 'Set HAP_TTSKILL_SYNC_TOKEN or pass -SyncToken before synchronizing.'
}
if ($Months -lt 1 -or $Months -gt 12) {
    throw 'Months must be between 1 and 12.'
}

$ttskillCommand = Get-Command ttskill -ErrorAction Stop
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

function Invoke-TtSkillJson {
    param(
        [Parameter(Mandatory = $true)] [string]$Action,
        [Parameter(Mandatory = $true)] [hashtable]$Body
    )

    $requestPath = Join-Path $env:TEMP ("hap-trade-query-{0}.json" -f [guid]::NewGuid())
    try {
        $request = @{ body = $Body } | ConvertTo-Json -Depth 20 -Compress
        [System.IO.File]::WriteAllText($requestPath, $request, $utf8NoBom)
        $output = & $ttskillCommand.Source invoke TRADE_QUERY `
            --action $Action `
            --body $requestPath
        if ($LASTEXITCODE -ne 0) {
            throw "ttskill $Action failed with exit code $LASTEXITCODE."
        }
        return (($output -join "`n") | ConvertFrom-Json)
    }
    finally {
        if (Test-Path -LiteralPath $requestPath) {
            Remove-Item -LiteralPath $requestPath -Force
        }
    }
}

function Invoke-HapImport {
    param(
        [Parameter(Mandatory = $true)] [string]$Path,
        [Parameter(Mandatory = $true)] [object]$Payload
    )

    $json = $Payload | ConvertTo-Json -Depth 100 -Compress
    $headers = @{ 'X-HAP-Sync-Token' = $SyncToken }
    $endpoint = '{0}/api/v1/fund/integrations/ttskill/trades/{1}' -f `
        $HapBaseUrl.TrimEnd('/'), $Path
    return Invoke-RestMethod -Method Post -Uri $endpoint -Headers $headers `
        -ContentType 'application/json; charset=utf-8' -Body $json
}

$listPayload = Invoke-TtSkillJson -Action 'trade_list' -Body @{
    tradeType = 'fund'
    dateType = if ($Months -eq 1) { '1' } elseif ($Months -eq 3) { '6' } elseif ($Months -eq 6) { '2' } else { '3' }
    busType = '0'
    statu = '0'
    pageSize = 500
}
$rows = @($listPayload.data.raw_result.body.trade_list_result.trades)
$detailPayloads = @()
foreach ($row in $rows) {
    $detailPayloads += Invoke-TtSkillJson -Action 'trade_detail' -Body @{
        fundCode = [string]$row.fundCode
        tradeId = [string]$row.tradeId
        tradeType = 'fund'
        dateType = '1'
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
$previewResponse = Invoke-HapImport -Path 'preview' -Payload $bundle
$preview = $previewResponse.data

Write-Output ("流水总数: {0} | 新增: {1} | 更新: {2} | 跳过: {3} | 错误: {4}" -f `
    $preview.total, $preview.create_count, $preview.update_count, $preview.skip_count, $preview.error_count)
$preview.items | Select-Object trade_id, fund_code, business_type, action, reason | Format-Table -AutoSize

if ($PreviewOnly) {
    Write-Output '预览模式结束，未写入 HAP。'
    exit 0
}

$confirmation = Read-Host '确认将新增/更新项写入 HAP？输入 Y 确认，其他输入取消'
if ($confirmation -notin @('Y', 'y')) {
    Write-Output '已取消，未写入 HAP。'
    exit 0
}

$importResponse = Invoke-HapImport -Path 'import' -Payload $bundle
$import = $importResponse.data
Write-Output ("导入完成: 新增 {0} | 更新 {1} | 跳过 {2} | 错误 {3}" -f `
    $import.create_count, $import.update_count, $import.skip_count, $import.error_count)
