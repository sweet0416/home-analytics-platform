# Tiantian Skills fund synchronization

HAP keeps the Tiantian Skills login and device credentials on the Windows
machine where the official CLI login succeeded. Docker receives only selected
fund metadata and NAV snapshots through an authenticated import endpoint.

## Server configuration

Generate a dedicated random value and configure the same value in the HAP
stack environment:

```text
FUND_TTSKILL_SYNC_ENABLED=true
FUND_TTSKILL_SYNC_TOKEN=<random value>
```

Do not commit the real token to Git.

## Windows synchronization

Open PowerShell in the repository and set the token for the current session:

```powershell
$env:HAP_TTSKILL_SYNC_TOKEN = '<same random value>'
```

Synchronize one fund:

```powershell
.\scripts\sync-ttskill-fund.ps1 -FundCode 009777
```

Synchronize the signed-in Tiantian account holdings:

```powershell
.\scripts\sync-ttskill-holdings.ps1
```

The account script invokes `ACCOUNT_HOLDING` with the `holding_list` action.
HAP stores each result as a new read-only snapshot and compares fund asset
values with manually maintained positions. It does not create shares, infer a
cost basis, or overwrite manual positions. The database stores only the fields
needed for the comparison; raw responses and account identifiers are not kept.

The scripts invoke the official skills locally, capture UTF-8 output without
PowerShell's legacy native-command decoding, read the HAP response as UTF-8
bytes, and send only the required snapshots to HAP. They never copy the
Tiantian login token into Docker.

After synchronization, remove the temporary HAP token and overwrite any
clipboard content that may contain the command:

```powershell
Remove-Item Env:HAP_TTSKILL_SYNC_TOKEN -ErrorAction SilentlyContinue
Set-Clipboard -Value '[cleared]'
```
