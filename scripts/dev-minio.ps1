$ErrorActionPreference = "Stop"
$env:USE_S3_STORAGE = "1"
docker compose --profile storage up -d minio minio-init
docker compose up -d --force-recreate web worker
Write-Host "MinIO console: http://127.0.0.1:9001" -ForegroundColor Green
