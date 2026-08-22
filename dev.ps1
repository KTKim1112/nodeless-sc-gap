<#
.SYNOPSIS
    Start the backend and the frontend together for development.

.DESCRIPTION
    Runs the FastAPI server on port 8000 and the Vite dev server on port 5173,
    waits until both answer, and opens the page. Ctrl+C stops both.

    A script rather than a dependency such as `concurrently`: it is a dozen
    lines, it needs nothing installed, and it can say something useful when a
    prerequisite is missing.

.EXAMPLE
    .\dev.ps1
    .\dev.ps1 -NoBrowser
#>
[CmdletBinding()]
param(
    [switch]$NoBrowser,
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

$python = Join-Path $root 'backend\.venv\Scripts\python.exe'
$vite = Join-Path $root 'frontend\node_modules\vite\bin\vite.js'
$node = 'C:\nvm4w\nodejs\node.exe'
if (-not (Test-Path $node)) { $node = (Get-Command node -ErrorAction SilentlyContinue).Source }

if (-not (Test-Path $python)) {
    Write-Error "Backend virtual environment not found at $python`nRun:  cd backend; python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e `".[dev]`""
}
if (-not (Test-Path $vite)) {
    Write-Error "Frontend dependencies not installed.`nRun:  cd frontend; npm install"
}
if (-not $node) {
    Write-Error "Node.js not found. Install it with:  nvm install 24.19.0; nvm use 24.19.0"
}

$processes = @()

function Wait-ForPort([int]$Port, [string]$Name, [int]$TimeoutSeconds = 40) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $client = [Net.Sockets.TcpClient]::new()
            $client.Connect('127.0.0.1', $Port)
            $client.Close()
            return $true
        } catch { Start-Sleep -Milliseconds 400 }
    }
    Write-Warning "$Name did not start listening on port $Port within $TimeoutSeconds s."
    return $false
}

try {
    Write-Host "backend  -> http://127.0.0.1:$ApiPort" -ForegroundColor Cyan
    $processes += Start-Process -FilePath $python `
        -ArgumentList '-m', 'uvicorn', 'app.main:app', '--reload', '--port', "$ApiPort" `
        -WorkingDirectory (Join-Path $root 'backend') -PassThru -NoNewWindow

    Write-Host "frontend -> http://127.0.0.1:$WebPort" -ForegroundColor Cyan
    $processes += Start-Process -FilePath $node `
        -ArgumentList "`"$vite`"" `
        -WorkingDirectory (Join-Path $root 'frontend') -PassThru -NoNewWindow

    $apiUp = Wait-ForPort $ApiPort 'Backend'
    $webUp = Wait-ForPort $WebPort 'Frontend'

    if ($apiUp -and $webUp) {
        Write-Host ''
        Write-Host "  page      http://127.0.0.1:$WebPort" -ForegroundColor Green
        Write-Host "  API docs  http://127.0.0.1:$ApiPort/docs" -ForegroundColor Green
        Write-Host ''
        Write-Host '  Ctrl+C to stop both.' -ForegroundColor DarkGray
        if (-not $NoBrowser) { Start-Process "http://127.0.0.1:$WebPort" }
    }

    while ($true) {
        Start-Sleep -Seconds 1
        foreach ($p in $processes) {
            if ($p.HasExited) {
                Write-Warning "A server exited (pid $($p.Id), code $($p.ExitCode)). Stopping."
                return
            }
        }
    }
}
finally {
    foreach ($p in $processes) {
        if ($p -and -not $p.HasExited) {
            Get-CimInstance Win32_Process -Filter "ParentProcessId=$($p.Id)" -ErrorAction SilentlyContinue |
                ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host 'Stopped.' -ForegroundColor DarkGray
}
