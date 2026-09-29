$ErrorActionPreference = "Stop"
$env:USE_MAILPIT = "1"
docker compose --profile mail up -d mailpit
docker compose up -d --force-recreate web worker
Write-Host "Mailpit UI: http://127.0.0.1:8025" -ForegroundColor Green
