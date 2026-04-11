# Writes GROQ_API_KEY into backend/.env (creates from .env.example if missing).
# Usage (from repo root):
#   .\backend\scripts\set-groq-key.ps1 -ApiKey "gsk_..."
# Get a key: https://console.groq.com/keys

param(
    [Parameter(Mandatory = $true)]
    [string] $ApiKey
)

$ErrorActionPreference = "Stop"
$backendRoot = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $backendRoot ".env"
$example = Join-Path $backendRoot ".env.example"

if (-not (Test-Path $envFile)) {
    if (-not (Test-Path $example)) {
        Write-Host "Missing $example" -ForegroundColor Red
        exit 1
    }
    Copy-Item $example $envFile
    Write-Host "Created $envFile from .env.example"
}

$content = Get-Content -Raw $envFile
$line = "GROQ_API_KEY=$ApiKey"
if ($content -match "(?m)^GROQ_API_KEY=") {
    $content = $content -replace "(?m)^GROQ_API_KEY=.*$", $line
} else {
    if ($content -and -not $content.EndsWith("`n")) { $content += "`n" }
    $content += "$line`n"
}
Set-Content -Path $envFile -Value $content -Encoding utf8
Write-Host "GROQ_API_KEY saved to $envFile — restart the API (uvicorn) to load it." -ForegroundColor Green
