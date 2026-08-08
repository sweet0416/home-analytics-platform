# Automatic Fund Trade Sync

HAP keeps the `ttskill` login on the Windows machine. Docker receives only the
trade bundle through the protected HAP endpoint, then validates and imports it
idempotently.

## One-time setup

Set the sync token as a user environment variable, then register the daily task:

```powershell
$env:HAP_TTSKILL_SYNC_TOKEN = 'your-HAP-sync-token'
[Environment]::SetEnvironmentVariable('HAP_TTSKILL_SYNC_TOKEN', $env:HAP_TTSKILL_SYNC_TOKEN, 'User')
.\scripts\register-ttskill-trades-task.ps1
```

The default schedule is 22:30. The task runs as the current Windows user so it
can reuse the existing `ttskill` login. It does not run when no user session is
available.

## Manual test

```powershell
.\scripts\run-ttskill-trades-task.ps1
```

Logs are written to `%LOCALAPPDATA%\HAP\logs\ttskill-trades.log`.

## Safety

- Only confirmed trades are imported.
- Re-running the task does not create duplicate transactions.
- The script does not write the sync token to the repository.
- A failed run is logged and can be rerun manually.
