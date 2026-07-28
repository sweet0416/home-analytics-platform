param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"

$BackendRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $BackendRoot ".venv\Scripts\python.exe"

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

Push-Location $BackendRoot
try {
    if (-not (Test-Path $VenvPython)) {
        New-BackendVenv
    }

    if (-not $SkipInstall) {
        & $VenvPython -m pip install --upgrade pip
        & $VenvPython -m pip install -r requirements-dev.txt
    }

    if (-not (Test-PythonModule "pytest")) {
        Stop-WithMessage "pytest is not installed in backend\.venv. Run scripts\test-backend.cmd without -SkipInstall."
    }

    if (-not (Test-PythonModule "ruff")) {
        Stop-WithMessage "ruff is not installed in backend\.venv. Run scripts\test-backend.cmd without -SkipInstall."
    }

    & $VenvPython -m compileall app tests alembic
    & $VenvPython -m pytest
    & $VenvPython -m ruff check app tests
}
finally {
    Pop-Location
}
