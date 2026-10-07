$ErrorActionPreference = "Stop"

$Port = 8001
$HostAddress = "127.0.0.1"
$ServerDirectory = Join-Path $PSScriptRoot "server"

if (-not (Test-Path (Join-Path $ServerDirectory "main.py"))) {
    throw "Backend main.py was not found at $ServerDirectory"
}

Set-Location $ServerDirectory

Write-Host ""
Write-Host "=== Vehicle Communication Backend Startup ==="
Write-Host "Backend directory: $ServerDirectory"
Write-Host "Checking port $Port..."

$listeners = Get-NetTCPConnection `
    -LocalAddress $HostAddress `
    -LocalPort $Port `
    -State Listen `
    -ErrorAction SilentlyContinue

if ($listeners) {
    foreach ($listener in $listeners) {
        $processId = $listener.OwningProcess

        $process = Get-Process -Id $processId -ErrorAction Stop

        if ($process.ProcessName -eq "python" -or
            $process.ProcessName -eq "python3") {

            Write-Host "Stopping existing Python process $processId using port $Port..."
            Stop-Process -Id $processId -Force
        }
        else {
            throw "Port $Port is occupied by unexpected process '$($process.ProcessName)' (PID $processId). Startup stopped for safety."
        }
    }

    Start-Sleep -Milliseconds 500
}

$remaining = Get-NetTCPConnection `
    -LocalAddress $HostAddress `
    -LocalPort $Port `
    -State Listen `
    -ErrorAction SilentlyContinue

if ($remaining) {
    throw "Port $Port is still occupied. Backend startup cancelled."
}

Write-Host "Port $Port is available."
Write-Host "Starting backend..."
Write-Host ""

& (Join-Path $ServerDirectory ".venv\Scripts\python.exe") -m uvicorn main:app --host $HostAddress --port $Port
