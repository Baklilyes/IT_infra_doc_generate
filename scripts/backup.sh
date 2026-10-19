#!/usr/bin/env bash
# ==============================================================================
# InfraDoc - Production Backup Script for Linux / Docker Environment
# ==============================================================================
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "${BACKUP_DIR}"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
echo "======================================================"
echo " Starting InfraDoc Backup at $(date)"
echo " Output directory: ${BACKUP_DIR}"
echo "======================================================"

# If running inside Docker Compose setup
if docker compose ps -q backend > /dev/null 2>&1; then
    echo "[-] Executing backup inside backend container..."
    docker compose exec -T backend python /app/scripts/backup.py --output-dir /app/backups
    echo "[✓] Backup archive created in container volume /app/backups"
else
    # Direct execution with python
    python scripts/backup.py --output-dir "${BACKUP_DIR}"
fi

echo "======================================================"
echo " Backup finished successfully!"
echo "======================================================"
