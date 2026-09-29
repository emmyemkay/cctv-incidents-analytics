$ErrorActionPreference = "Stop"
if (-not (Test-Path "backups")) { New-Item -ItemType Directory -Path "backups" | Out-Null }
docker compose --profile ops run --rm backup
Write-Host "Backup completed in .\backups" -ForegroundColor Green
