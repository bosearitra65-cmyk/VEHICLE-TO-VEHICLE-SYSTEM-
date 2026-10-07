Set-Location "C:\vehicle_communication_web\server"

Write-Output "============================================================"
Write-Output "V2V BACKEND COMPREHENSIVE AUDIT"
Write-Output "============================================================"

Write-Output "`n=== PROJECT LOCATION ==="
Get-Location

Write-Output "`n=== PROJECT FILE TREE ==="
Get-ChildItem -Recurse -File |
    Where-Object {
        $_.FullName -notmatch "\\.venv\\" -and
        $_.FullName -notmatch "__pycache__" -and
        $_.FullName -notmatch "\\.git\\" -and
        $_.FullName -notmatch "\\secrets\\"
    } |
    ForEach-Object {
        $_.FullName.Replace((Get-Location).Path + "\", "")
    } |
    Sort-Object

Write-Output "`n=== PYTHON / ENVIRONMENT ==="
if (Test-Path ".\.venv\Scripts\python.exe") {
    .\.venv\Scripts\python.exe --version
    .\.venv\Scripts\python.exe -c "import sys; print('Python executable:', sys.executable)"
    .\.venv\Scripts\python.exe -c "import fastapi,uvicorn,sqlalchemy,alembic,pydantic; print('FastAPI:',fastapi.__version__); print('Uvicorn:',uvicorn.__version__); print('SQLAlchemy:',sqlalchemy.__version__); print('Alembic:',alembic.__version__); print('Pydantic:',pydantic.__version__)"
} else {
    Write-Output "ERROR: .venv Python not found"
}

Write-Output "`n=== ALEMBIC ==="
if (Test-Path ".\alembic.ini") {
    .\.venv\Scripts\python.exe -m alembic current
    Write-Output "--- HISTORY ---"
    .\.venv\Scripts\python.exe -m alembic history
} else {
    Write-Output "ERROR: alembic.ini not found"
}

Write-Output "`n=== DATABASE ==="
if (Test-Path ".\vehicle_communication.db") {
    Get-Item ".\vehicle_communication.db" |
        Select-Object FullName,Length,LastWriteTime
} else {
    Write-Output "WARNING: database not found"
}

Write-Output "`n=== PYTHON COMPILE ==="
$pyFiles = Get-ChildItem -Recurse -Filter *.py |
    Where-Object {
        $_.FullName -notmatch "\\.venv\\" -and
        $_.FullName -notmatch "__pycache__"
    }

$failed = @()

foreach ($file in $pyFiles) {
    $result = & .\.venv\Scripts\python.exe -m py_compile $file.FullName 2>&1
    if ($LASTEXITCODE -ne 0) {
        $failed += $file.FullName
        Write-Output "FAIL: $($file.FullName)"
        Write-Output $result
    }
}

if ($failed.Count -eq 0) {
    Write-Output "PASS: All Python files compile successfully."
} else {
    Write-Output "FAILED FILE COUNT: $($failed.Count)"
}

Write-Output "`n=== TEST DISCOVERY ==="
if (Test-Path ".\tests") {
    .\.venv\Scripts\python.exe -m pytest --collect-only -q
} else {
    Write-Output "WARNING: tests directory not found"
}

Write-Output "`n=== API ROUTERS ==="
Get-ChildItem ".\app\api" -Recurse -Filter *.py -ErrorAction SilentlyContinue |
    Select-Object FullName |
    Sort-Object FullName

Write-Output "`n=== MODELS ==="
Get-ChildItem ".\app\models" -Recurse -Filter *.py -ErrorAction SilentlyContinue |
    Select-Object FullName |
    Sort-Object FullName

Write-Output "`n=== SERVICES ==="
Get-ChildItem ".\app\services" -Recurse -Filter *.py -ErrorAction SilentlyContinue |
    Select-Object FullName |
    Sort-Object FullName

Write-Output "`n=== REPOSITORIES ==="
Get-ChildItem ".\app\database\repositories" -Recurse -Filter *.py -ErrorAction SilentlyContinue |
    Select-Object FullName |
    Sort-Object FullName

Write-Output "`n=== AUTH / SECURITY ==="
Get-ChildItem ".\app\auth" -Recurse -File -ErrorAction SilentlyContinue |
    Select-Object FullName |
    Sort-Object FullName

Write-Output "`n=== UNFINISHED / PLACEHOLDERS ==="
Get-ChildItem ".\app" -Recurse -Filter *.py |
    Select-String -Pattern "TODO|FIXME|NotImplemented|not implemented|pass$|return None|return \{\}|501|placeholder|stub" |
    Select-Object Path,LineNumber,Line |
    Format-Table -AutoSize

Write-Output "`n=== LOCATION / ROUTING / TRAFFIC / ETA ==="
Get-ChildItem ".\app" -Recurse -Filter *.py |
    Select-String -Pattern "geocod|reverse.?geocod|routing|route|matrix|distance|traffic|ETA|eta|travel.?time|deviation|waypoint" |
    Select-Object Path,LineNumber,Line |
    Format-Table -AutoSize

Write-Output "`n=== DEVICE / REALTIME / SYNCHRONIZATION ==="
Get-ChildItem ".\app" -Recurse -Filter *.py |
    Select-String -Pattern "device|device_id|API.?key|token|websocket|WebSocket|realtime|real.?time|sync|synchron|reconnect|connection" |
    Select-Object Path,LineNumber,Line |
    Format-Table -AutoSize

Write-Output "`n=== MONITORING / AUDIT / RELIABILITY ==="
Get-ChildItem ".\app" -Recurse -Filter *.py |
    Select-String -Pattern "monitor|health|audit|rate.?limit|idempot|request.?id|correlation|logging|log" |
    Select-Object Path,LineNumber,Line |
    Format-Table -AutoSize

Write-Output "`n=== RESEARCH FRAMEWORK ==="
Get-ChildItem ".\app" -Recurse -Filter *.py |
    Select-String -Pattern "research|experiment|baseline|candidate|fault|observation|metric|evidence|comparison" |
    Select-Object Path,LineNumber,Line |
    Format-Table -AutoSize

Write-Output "`n=== MAIN APPLICATION ==="
if (Test-Path ".\main.py") {
    Get-Content ".\main.py"
} else {
    Write-Output "ERROR: main.py not found"
}

Write-Output "`n=== STARTUP SCRIPT ==="
$startup = "C:\vehicle_communication_web\start_server.ps1"
if (Test-Path $startup) {
    Get-Content $startup
} else {
    Write-Output "WARNING: start_server.ps1 not found"
}

Write-Output "`n=== CONFIG FILE NAMES ONLY ==="
Get-ChildItem -Force |
    Where-Object {
        $_.Name -match "^\.env" -or
        $_.Name -match "requirements|pyproject|Pipfile"
    } |
    Select-Object Name,Length,LastWriteTime

Write-Output "`n============================================================"
Write-Output "AUDIT COMPLETE"
Write-Output "============================================================"
