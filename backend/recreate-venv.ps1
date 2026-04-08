# Recreate .venv after a broken/partial delete (missing pyvenv.cfg, access denied, etc.)
# BEFORE RUNNING: Quit Cursor (or close ALL terminals), stop uvicorn, end "Python" in Task Manager.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = @(
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $py) {
    Write-Host "No python.exe found under Local\Programs\Python. Install Python 3.11+ from python.org or: winget install Python.Python.3.12" -ForegroundColor Red
    exit 1
}

Write-Host "Using: $py" -ForegroundColor Cyan
if (-not (Test-Path .\.venv\pyvenv.cfg)) {
    Write-Host "pyvenv.cfg missing — venv is broken. Delete .venv after unlocking files (close Cursor, kill python.exe)." -ForegroundColor Yellow
}

if (Test-Path .\.venv) {
    Write-Host "Removing .\.venv ... (if this fails, close Cursor and kill python.exe in Task Manager, then run again)" -ForegroundColor Yellow
    Remove-Item -Recurse -Force .\.venv
}

& $py -m venv .venv
if (-not (Test-Path .\.venv\pyvenv.cfg)) {
    Write-Error "venv creation failed — pyvenv.cfg still missing."
    exit 1
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
Write-Host "Done. Start API with: .\run-api.ps1" -ForegroundColor Green
