$ErrorActionPreference = "Stop"
if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
& .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements/dev.txt
if (-not (Test-Path ".env")) { Copy-Item .env.example .env }
$env:DJANGO_SETTINGS_MODULE = "cctv_analytics.settings.development"
$env:USE_POSTGRES = "0"
$env:USE_REDIS = "0"
$env:ASYNC_DATASET_IMPORTS = "0"
python manage.py migrate
python manage.py check
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "Run the web app: python manage.py runserver" -ForegroundColor Cyan
Write-Host "For background jobs, also run: celery -A cctv_analytics worker -Q imports,analytics --loglevel=INFO" -ForegroundColor Cyan
