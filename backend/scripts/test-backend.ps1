param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $BackendRoot ".venv\Scripts\python.exe"
$FailedChecks = @()

function Stop-WithMessage {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Message
    )

    [Console]::Error.WriteLine($Message)
    exit 1
}

function New-BackendVenv {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        & py -3.12 -m venv .venv
        return
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        & python -m venv .venv
        return
    }

    Stop-WithMessage "Python 3.12 was not found. Install Python 3.12 or create backend\.venv manually."
}

function Test-PythonModule {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ModuleName
    )

    & $VenvPython -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('$ModuleName') else 1)"
    return $LASTEXITCODE -eq 0
}

function Invoke-SetupCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Description,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $VenvPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "$Description failed with exit code $LASTEXITCODE."
    }
}

function Invoke-BackendCheck {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Name,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    Write-Host ""
    Write-Host "==> $Name"
    & $VenvPython @Arguments
    if ($LASTEXITCODE -ne 0) {
        $script:FailedChecks += $Name
    }
}

Push-Location $BackendRoot
try {
    if (-not (Test-Path $VenvPython)) {
        New-BackendVenv
    }

    if (-not $SkipInstall) {
        Invoke-SetupCommand "pip upgrade" @("-m", "pip", "install", "--upgrade", "pip")
        Invoke-SetupCommand "dependency installation" @(
            "-m",
            "pip",
            "install",
            "-r",
            "requirements-dev.txt"
        )
    }

    if (-not (Test-PythonModule "pytest")) {
        Stop-WithMessage "pytest is not installed in backend\.venv. Run scripts\test-backend.cmd without -SkipInstall."
    }

    if (-not (Test-PythonModule "ruff")) {
        Stop-WithMessage "ruff is not installed in backend\.venv. Run scripts\test-backend.cmd without -SkipInstall."
    }

    Invoke-BackendCheck "Python syntax" @("-m", "compileall", "-q", "app", "tests", "alembic")
    Invoke-BackendCheck "Pytest" @("-m", "pytest")
    Invoke-BackendCheck "Ruff" @("-m", "ruff", "check", "app", "tests")

    if ($FailedChecks.Count -gt 0) {
        Stop-WithMessage "Backend checks failed: $($FailedChecks -join ', ')."
    }

    Write-Host ""
    Write-Host "All backend checks passed."
}
finally {
    Pop-Location
}
