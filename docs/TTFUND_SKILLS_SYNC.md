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

The script invokes `TTFUND_BASE_INFOS` locally, captures UTF-8 output without
PowerShell's legacy native-command decoding, and sends it to HAP. It never
copies the Tiantian login token into Docker.
