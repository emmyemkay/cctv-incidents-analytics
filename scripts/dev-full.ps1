$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
}

docker compose `
    --profile edge `
    --profile scheduled `
    --profile storage `
    --profile mail `
    --profile db-tools `
    --profile monitoring `
    up -d --build

docker compose ps
Write-Host "Direct Daphne: http://127.0.0.1:8001" -ForegroundColor Green
Write-Host "Nginx proxy:    http://127.0.0.1:8080" -ForegroundColor Green
Write-Host "Mailpit:        http://127.0.0.1:8025" -ForegroundColor Green
Write-Host "Adminer:        http://127.0.0.1:8081" -ForegroundColor Green
Write-Host "Flower:         http://127.0.0.1:5555" -ForegroundColor Green
Write-Host "Prometheus:     http://127.0.0.1:9090" -ForegroundColor Green
Write-Host "Grafana:        http://127.0.0.1:3000" -ForegroundColor Green
Write-Host "MinIO console:  http://127.0.0.1:9001" -ForegroundColor Green

Write-Host "Use dev-mailpit.ps1 or dev-minio.ps1 when the application itself must switch to those backends." -ForegroundColor Yellow
