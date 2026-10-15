<#
.SYNOPSIS
  Create (or refresh) the project virtual environment .venv on Windows and verify it.

.DESCRIPTION
  Preferred path: uv + the committed universal lock file (uv.lock). Versions are
  exactly the tested ones and the Python version comes from .python-version
  (uv downloads it if needed).
  Fallback when uv is not installed: python -m venv + pip with the version
  ranges of pyproject.toml (works, but is NOT locked).

  The .venv folder is machine specific: never copy it between Windows and
  Linux. On Linux run ./setup_linux.sh instead.
  The 'aria' extra (projectaria-tools) is skipped on Windows: it has no
  Windows wheels. Aria VRS processing runs on Linux.

.PARAMETER Extras
  Comma-separated optional extras: cv, route, presentation ('dev' is added unless -NoDev).

.PARAMETER NoDev
  Do not install the dev extra (pytest, ruff); tests are then skipped.

.PARAMETER Recreate
  Delete the existing .venv before installing.

.PARAMETER SkipTests
  Do not run the test suite after the installation.

.PARAMETER Python
  Interpreter for the pip fallback (default: py launcher, 3.12 / 3.11 / 3.10).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File .\setup_windows.ps1 -Extras "cv,presentation" -Recreate
#>
[CmdletBinding()]
param(
    [string]$Extras = "",
    [switch]$NoDev,
    [switch]$Recreate,
    [switch]$SkipTests,
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root
$Venv = Join-Path $Root ".venv"
$VenvPython = Join-Path $Venv "Scripts\python.exe"

function Test-PyLauncherVersion([string]$Version) {
    # Probe "py -3.x" without turning its stderr into a terminating error (PowerShell 5.1).
    if (-not (Get-Command py -ErrorAction SilentlyContinue)) { return $false }
    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & py "-$Version" -c "import sys" *> $null
        return ($LASTEXITCODE -eq 0)
    }
    catch { return $false }
    finally { $ErrorActionPreference = $previous }
}

# --- extras --------------------------------------------------------------------
$extraList = @()
if ($Extras) {
    $extraList = @($Extras.Split(",") | ForEach-Object { $_.Trim().ToLower() } | Where-Object { $_ })
}
if ($extraList -contains "aria") {
    Write-Warning "projectaria-tools has no Windows wheels: the 'aria' extra is skipped. Use Linux for VRS processing."
    $extraList = @($extraList | Where-Object { $_ -ne "aria" })
}
if (-not $NoDev) { $extraList += "dev" }
$extraList = @($extraList | Select-Object -Unique)

# --- a .venv copied from Linux (bin/ instead of Scripts/) is never reused ---------
if ((Test-Path $Venv) -and -not (Test-Path $VenvPython)) {
    Write-Warning ".venv exists but is not a Windows environment (copied from another OS?). It will be recreated."
    $Recreate = $true
}
if ($Recreate -and (Test-Path $Venv)) {
    Write-Host "Removing existing .venv"
    Remove-Item -Recurse -Force $Venv
}

# --- install -------------------------------------------------------------------------
$uv = Get-Command uv -ErrorAction SilentlyContinue
if ($uv) {
    $uvArgs = @("sync", "--frozen")
    foreach ($e in $extraList) { $uvArgs += @("--extra", $e) }
    Write-Host ("Running: uv " + ($uvArgs -join " "))
    & uv @uvArgs
    if ($LASTEXITCODE -ne 0) { Write-Error "uv sync failed"; exit $LASTEXITCODE }
}
else {
    Write-Warning "uv not found: falling back to venv + pip (versions NOT locked). Install uv for reproducible environments: https://docs.astral.sh/uv/"
    if (-not (Test-Path $VenvPython)) {
        $base = $null
        if ($Python) {
            $base = @($Python)
        }
        else {
            foreach ($v in @("3.12", "3.11", "3.10")) {
                if (Test-PyLauncherVersion $v) { $base = @("py", "-$v"); break }
            }
        }
        if (-not $base) { Write-Error "No Python 3.10-3.12 found. Install one (or uv) and retry, or pass -Python <path>."; exit 1 }
        Write-Host ("Creating .venv with: " + ($base -join " "))
        if ($base.Count -gt 1) { & $base[0] $base[1] -m venv $Venv } else { & $base[0] -m venv $Venv }
        if ($LASTEXITCODE -ne 0) { Write-Error "venv creation failed"; exit 1 }
    }
    & $VenvPython -m pip install --upgrade pip
    $spec = "."
    if ($extraList.Count -gt 0) { $spec = ".[" + ($extraList -join ",") + "]" }
    & $VenvPython -m pip install -e $spec
    if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed"; exit $LASTEXITCODE }
}

# --- verification ------------------------------------------------------------------------
Write-Host ""
Write-Host "=== Installation check ==="
& $VenvPython -m ariagen_escooter info
if ($LASTEXITCODE -ne 0) { Write-Error "installation check failed"; exit 1 }

if ((-not $SkipTests) -and ($extraList -contains "dev")) {
    Write-Host ""
    Write-Host "=== Test suite ==="
    & $VenvPython -m pytest -q
    if ($LASTEXITCODE -ne 0) { Write-Error "tests failed"; exit $LASTEXITCODE }
}

Write-Host ""
Write-Host "Environment ready. Activate it with:  .\.venv\Scripts\Activate.ps1"
Write-Host "Try the synthetic MVP:               python -m ariagen_escooter run data\synthetic\SYN001_S01"
