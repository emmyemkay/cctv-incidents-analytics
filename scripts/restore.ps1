param([Parameter(Mandatory=$true)][string]$BackupFile)
$ErrorActionPreference = "Stop"
if (-not (Test-Path $BackupFile)) { throw "Backup file not found: $BackupFile" }
$resolved = (Resolve-Path $BackupFile).Path
docker compose cp $resolved db:/tmp/restore.dump
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/restore.dump'
Write-Host "Restore command completed. Review database logs and application smoke tests." -ForegroundColor Yellow
