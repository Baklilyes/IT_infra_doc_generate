#!/usr/bin/env bash
# ==============================================================================
# InfraDoc - Production Restore Script for Linux / Docker Environment
# ==============================================================================
set -euo pipefail

if [ $# -lt 1 ]; then
    echo "Usage: $0 <path_to_backup_archive.tar.gz>"
    exit 1
fi

ARCHIVE_PATH="$1"

if [ ! -f "${ARCHIVE_PATH}" ]; then
    echo "ERROR: Backup archive file not found: ${ARCHIVE_PATH}"
    exit 1
fi

echo "======================================================"
echo " Starting InfraDoc System Restore from ${ARCHIVE_PATH}"
echo " WARNING: Existing data will be synchronized/overwritten."
echo "======================================================"

if docker compose ps -q backend > /dev/null 2>&1; then
    echo "[-] Executing restore inside backend container..."
    ARCHIVE_NAME=$(basename "${ARCHIVE_PATH}")
    docker compose cp "${ARCHIVE_PATH}" backend:/tmp/"${ARCHIVE_NAME}"
    docker compose exec -T backend python /app/scripts/restore.py /tmp/"${ARCHIVE_NAME}"
    docker compose exec -T backend rm -f /tmp/"${ARCHIVE_NAME}"
else
    python scripts/restore.py "${ARCHIVE_PATH}"
fi

echo "======================================================"
echo " Restore completed successfully!"
echo "======================================================"
