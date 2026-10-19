"""
Universal Backup Script for IT Infrastructure Documentation Generator (InfraDoc).
Exports database state (JSON/SQL), generated documents, storage uploads, and manifest with SHA256 checksums.
Compatible with Linux, Windows, Bare-Metal and Docker environments.
"""
import sys
import os
import json
import tarfile
import hashlib
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import select, text, create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.database import sync_engine, Base
import app.models  # Ensure all models are registered in Base.metadata


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def dump_database_to_dict(session: Session) -> Dict[str, List[Dict[str, Any]]]:
    """Export all tables into a structured dictionary."""
    data = {}
    for table_name, table in Base.metadata.tables.items():
        stmt = select(table)
        rows = session.execute(stmt).mappings().all()
        serialized_rows = []
        for row in rows:
            clean_row = {}
            for col_name, val in row.items():
                if isinstance(val, datetime):
                    clean_row[col_name] = val.isoformat()
                elif hasattr(val, "value"):  # Enums
                    clean_row[col_name] = val.value
                else:
                    clean_row[col_name] = val
            serialized_rows.append(clean_row)
        data[table_name] = serialized_rows
    return data


def create_backup(
    output_dir: Optional[str] = None,
    engine: Optional[Any] = None,
    database_url: Optional[str] = None
) -> str:
    """
    Creates a full backup archive (.tar.gz) containing:
    - database_dump.json
    - files in STORAGE_DIR
    - files in generated_docs
    - manifest.json
    """
    if not output_dir:
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
    os.makedirs(output_dir, exist_ok=True)

    timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    archive_filename = f"infradoc_backup_{timestamp_str}.tar.gz"
    archive_path = os.path.join(output_dir, archive_filename)

    # Temporary directory for staging
    staging_dir = os.path.join(output_dir, f"_staging_{timestamp_str}")
    os.makedirs(staging_dir, exist_ok=True)

    try:
        # Determine engine
        if engine is not None:
            active_engine = engine
        elif database_url:
            active_engine = create_engine(database_url)
        else:
            active_engine = sync_engine

        SessionMaker = sessionmaker(bind=active_engine)

        # 1. Export Database
        print("[-] Exporting database records...")
        with SessionMaker() as session:
            db_data = dump_database_to_dict(session)

        db_dump_path = os.path.join(staging_dir, "database_dump.json")
        with open(db_dump_path, "w", encoding="utf-8") as f:
            json.dump(db_data, f, indent=2, ensure_ascii=False)

        manifest: Dict[str, Any] = {
            "version": settings.VERSION,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "environment": settings.ENVIRONMENT,
            "database_records": {tbl: len(rows) for tbl, rows in db_data.items()},
            "files": {}
        }

        # 2. Collect Storage & Generated Documents
        storage_staging = os.path.join(staging_dir, "storage")
        os.makedirs(storage_staging, exist_ok=True)

        candidate_dirs = [
            ("storage", settings.STORAGE_DIR),
            ("generated_docs", os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "generated_docs")))
        ]

        file_count = 0
        for rel_target, src_dir in candidate_dirs:
            if os.path.exists(src_dir):
                target_subdir = os.path.join(storage_staging, rel_target)
                os.makedirs(target_subdir, exist_ok=True)
                for root, _, files in os.walk(src_dir):
                    for file in files:
                        if file.endswith((".docx", ".pdf", ".xlsx", ".csv", ".json", ".txt")):
                            src_file = os.path.join(root, file)
                            rel_file = os.path.relpath(src_file, src_dir)
                            dst_file = os.path.join(target_subdir, rel_file)
                            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                            
                            with open(src_file, "rb") as sf, open(dst_file, "wb") as df:
                                df.write(sf.read())
                            
                            checksum = calculate_sha256(dst_file)
                            manifest["files"][f"{rel_target}/{rel_file}"] = {
                                "size_bytes": os.path.getsize(dst_file),
                                "sha256": checksum
                            }
                            file_count += 1

        manifest["total_files_backed_up"] = file_count

        # Write manifest
        manifest_path = os.path.join(staging_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        # 3. Create .tar.gz archive
        print(f"[-] Compressing backup into {archive_filename}...")
        with tarfile.open(archive_path, "w:gz") as tar:
            for item in os.listdir(staging_dir):
                item_full = os.path.join(staging_dir, item)
                tar.add(item_full, arcname=item)

        archive_size_mb = os.path.getsize(archive_path) / (1024 * 1024)
        print(f"[OK] Backup completed successfully!")
        print(f"    Archive : {archive_path}")
        print(f"    Size    : {archive_size_mb:.2f} MB")
        print(f"    Tables  : {len(manifest['database_records'])} tables exported")
        print(f"    Files   : {file_count} documents/artifacts archived")

        return archive_path

    finally:
        # Clean up staging directory
        if os.path.exists(staging_dir):
            import shutil
            shutil.rmtree(staging_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create InfraDoc full system backup.")
    parser.add_argument("--output-dir", help="Directory where backup tar.gz will be saved", default=None)
    parser.add_argument("--db-url", help="Database connection URL", default=None)
    args = parser.parse_args()

    try:
        res_path = create_backup(args.output_dir, database_url=args.db_url)
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Backup failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
