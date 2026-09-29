$ErrorActionPreference = "Stop"

docker compose --profile workers stop worker-imports worker-analytics
docker compose up -d worker
docker compose ps
Write-Host "The single combined development worker is active." -ForegroundColor Green
