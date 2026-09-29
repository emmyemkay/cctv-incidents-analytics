$ErrorActionPreference = "Stop"

Write-Host "Importing bundled Fire, General Crime and Traffic datasets..." -ForegroundColor Cyan
docker compose exec web python manage.py import_bundled_datasets
Write-Host "Import complete. Open http://127.0.0.1:8001" -ForegroundColor Green
