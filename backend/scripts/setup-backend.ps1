# End-to-end backend setup: venv, dependencies, .env from example, optional Groq key.
# Run from repo root: .\backend\scripts\setup-backend.ps1
# With Groq: .\backend\scripts\setup-backend.ps1 -GroqApiKey "gsk_..."

param(
    [string] $GroqApiKey = ""
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
Set-Location $backendRoot

Write-Host "== MeetAI backend setup ==" -ForegroundColor Cyan

if (-not (Test-Path .\.venv\Scripts\python.exe)) {
    Write-Host "Creating virtual env..." -ForegroundColor Yellow
    python -m venv .venv
}
& .\.venv\Scripts\pip.exe install -r requirements.txt -q

if (-not (Test-Path .\.env)) {
    Copy-Item .\.env.example .\.env
    Write-Host "Created .env — edit JWT_SECRET_KEY for production." -ForegroundColor Yellow
}

if ($GroqApiKey) {
    & "$PSScriptRoot\set-groq-key.ps1" -ApiKey $GroqApiKey
} else {
    Write-Host "Groq: optional. Set a key with: .\backend\scripts\set-groq-key.ps1 -ApiKey `"gsk_...`"" -ForegroundColor DarkGray
}

Write-Host "Done. Start API: cd backend; .\run-api.ps1" -ForegroundColor Green
