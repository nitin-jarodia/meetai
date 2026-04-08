# Start the FastAPI server (SQLite by default). Run from repo root: .\backend\run-api.ps1
Set-Location $PSScriptRoot
if (-not (Test-Path .\.venv\pyvenv.cfg) -or -not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Host "Virtual env is missing or broken (e.g. no pyvenv.cfg)." -ForegroundColor Red
    Write-Host "1) Quit Cursor / stop uvicorn / end python.exe in Task Manager" -ForegroundColor Yellow
    Write-Host "2) Delete folder: $PSScriptRoot\.venv" -ForegroundColor Yellow
    Write-Host "3) Run: .\recreate-venv.ps1" -ForegroundColor Yellow
    exit 1
}
& .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
