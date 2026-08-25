<#
.SYNOPSIS
    Build the standalone Windows executable.

.DESCRIPTION
    Produces `packaging/dist/NodelessSC.exe`: one file, for a machine with no
    Python, no Node, and no administrator rights.

    Builds the frontend first unless -SkipFrontend is given. `backend/static/`
    is not in the repository -- it is generated -- so a build that skipped it
    would silently ship whatever was left there from the last time, or an
    executable that serves no page at all.

.EXAMPLE
    .\packaging\build.ps1
    .\packaging\build.ps1 -SkipFrontend
#>
[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    # One folder rather than one file, zipped for sending. Slower to send,
    # far faster to start: one file unpacks itself into a temporary directory
    # on every launch, showing nothing while it does.
    [switch]$OneDir
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root 'backend\.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    Write-Error "Backend virtual environment not found at $python`nRun:  cd backend; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e `".[dev,package]`""
}
& $python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller is not installed.`nRun:  cd backend; .\.venv\Scripts\python.exe -m pip install -e `".[dev,package]`""
}

if (-not $SkipFrontend) {
    Write-Host 'Building the frontend...' -ForegroundColor Cyan
    Push-Location (Join-Path $root 'frontend')
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) { Write-Error 'Frontend build failed.' }
    } finally { Pop-Location }
}

$static = Join-Path $root 'backend\static\index.html'
if (-not (Test-Path $static)) {
    Write-Error "No built frontend at $static`nRun it without -SkipFrontend, or:  cd frontend; npm run build"
}

Write-Host 'Freezing...' -ForegroundColor Cyan
Push-Location $PSScriptRoot
try {
    if ($OneDir) { $env:NSC_ONEDIR = '1' } else { Remove-Item Env:\NSC_ONEDIR -ErrorAction SilentlyContinue }
    & $python -m PyInstaller --noconfirm --clean --distpath dist --workpath build NodelessSC.spec
    if ($LASTEXITCODE -ne 0) { Write-Error 'PyInstaller failed.' }
} finally {
    Remove-Item Env:\NSC_ONEDIR -ErrorAction SilentlyContinue
    Pop-Location
}

if ($OneDir) {
    $folder = Join-Path $PSScriptRoot 'dist\NodelessSC'
    $exe = Join-Path $folder 'NodelessSC.exe'
    if (-not (Test-Path $exe)) { Write-Error "Expected $exe, which is not there." }

    $zip = Join-Path $PSScriptRoot 'dist\NodelessSC-windows.zip'
    Write-Host 'Compressing...' -ForegroundColor Cyan
    Remove-Item $zip -ErrorAction SilentlyContinue
    Compress-Archive -Path $folder -DestinationPath $zip
    $mb = (Get-Item $zip).Length / 1MB
    Write-Host ''
    Write-Host ("  {0}" -f $zip) -ForegroundColor Green
    Write-Host ("  {0:N0} MB zipped. Unzip, then run NodelessSC\NodelessSC.exe" -f $mb) -ForegroundColor Green
} else {
    $exe = Join-Path $PSScriptRoot 'dist\NodelessSC.exe'
    if (-not (Test-Path $exe)) { Write-Error "Expected $exe, which is not there." }
    $mb = (Get-Item $exe).Length / 1MB
    Write-Host ''
    Write-Host ("  {0}" -f $exe) -ForegroundColor Green
    Write-Host ("  {0:N0} MB" -f $mb) -ForegroundColor Green
}
Write-Host ''
Write-Host '  Verified here only that it builds and runs on this machine, which' -ForegroundColor DarkGray
Write-Host '  has Python installed. Whether it runs where Python is absent is' -ForegroundColor DarkGray
Write-Host '  answered by copying it to such a machine and opening it.' -ForegroundColor DarkGray
