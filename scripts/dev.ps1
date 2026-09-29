$ErrorActionPreference = "Stop"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Review the development passwords and tokens." -ForegroundColor Yellow
}

docker compose up -d --build
docker compose ps
Write-Host "Command overview: http://127.0.0.1:8001" -ForegroundColor Green
Write-Host "Logs: docker compose logs -f web worker" -ForegroundColor Cyan
