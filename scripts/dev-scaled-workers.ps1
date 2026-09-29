$ErrorActionPreference = "Stop"

docker compose stop worker
docker compose --profile workers up -d --build worker-imports worker-analytics
docker compose ps
Write-Host "Dedicated import and analytics workers are active. The combined worker is stopped." -ForegroundColor Green
