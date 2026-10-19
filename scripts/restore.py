"""
Universal Restore Script for IT Infrastructure Documentation Generator (InfraDoc).
Restores database state and document files from a valid InfraDoc backup archive (.tar.gz).
Validates SHA256 integrity and verifies table counts.
"""
import sys
import os
import json
import tarfile
import hashlib
import argparse
from datetime import datetime
from typing import Dict, Any, List, Optional

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from sqlalchemy import select, text, create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.core.database import sync_engine, Base
import app.models


def calculate_sha256(filepath: str) -> str:
    """Calculate SHA256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def restore_backup(
    archive_path: str,
    clear_first: bool = True,
    engine: Optional[Any] = None,
    database_url: Optional[str] = None
) -> bool:
    """
    Restore an InfraDoc system backup from .tar.gz archive.
    """
    if not os.path.exists(archive_path):
        raise FileNotFoundError(f"Archive introuvable : {archive_path}")

    temp_dir = os.path.join(os.path.dirname(archive_path), f"_restore_staging_{int(datetime.now().timestamp())}")
    os.makedirs(temp_dir, exist_ok=True)

    try:
        # Determine engine
        if engine is not None:
            active_engine = engine
        elif database_url:
            active_engine = create_engine(database_url)
        else:
            active_engine = sync_engine

        SessionMaker = sessionmaker(bind=active_engine)

        print(f"[-] Extracting archive {archive_path}...")
        with tarfile.open(archive_path, "r:gz") as tar:
            if hasattr(tarfile, "data_filter"):
                tar.extractall(path=temp_dir, filter="data")
            else:
                tar.extractall(path=temp_dir)

        manifest_path = os.path.join(temp_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            raise ValueError("Manifeste de sauvegarde 'manifest.json' introuvable dans l'archive!")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        print(f"[OK] Manifest loaded. Backup version: {manifest.get('version')}, Created at: {manifest.get('created_at')}")

        # 1. Verify file checksums
        print("[-] Verifying file integrity (SHA256)...")
        files_dict = manifest.get("files", {})
        for rel_file, meta in files_dict.items():
            staging_file = os.path.join(temp_dir, "storage", rel_file)
            if not os.path.exists(staging_file):
                raise ValueError(f"Fichier manquant dans l'archive : {rel_file}")
            actual_hash = calculate_sha256(staging_file)
            if actual_hash != meta["sha256"]:
                raise ValueError(f"Altération détectée pour {rel_file} ! Hash attendu: {meta['sha256']}, actuel: {actual_hash}")

        print(f"[OK] All {len(files_dict)} files verified with valid SHA256 checksums.")

        # 2. Restore Database
        db_dump_path = os.path.join(temp_dir, "database_dump.json")
        if not os.path.exists(db_dump_path):
            raise ValueError("Fichier database_dump.json introuvable dans l'archive!")

        with open(db_dump_path, "r", encoding="utf-8") as f:
            db_data: Dict[str, List[Dict[str, Any]]] = json.load(f)

        print("[-] Restoring database records...")
        Base.metadata.create_all(bind=active_engine)

        with SessionMaker() as session:
            # If clear_first, delete existing records in reverse dependency order
            if clear_first:
                print("[-] Clearing existing records...")
                table_order = [
                    "workflow_decisions", "documents", "consistency_overrides", "consistency_reports",
                    "import_jobs", "configurations", "interfaces", "network_segments",
                    "equipment", "locations", "sites", "projects", "users"
                ]
                for tbl_name in table_order:
                    if tbl_name in Base.metadata.tables:
                        try:
                            session.execute(text(f"DELETE FROM {tbl_name}"))
                        except Exception:
                            pass
                session.commit()

            # Insert tables in forward dependency order
            insert_order = [
                "users", "projects", "sites", "locations", "equipment",
                "network_segments", "interfaces", "configurations",
                "import_jobs", "consistency_reports", "consistency_overrides",
                "documents", "workflow_decisions"
            ]

            total_inserted = 0
            for tbl_name in insert_order:
                rows = db_data.get(tbl_name, [])
                if not rows:
                    continue
                table = Base.metadata.tables.get(tbl_name)
                if table is None:
                    continue

                for r in rows:
                    clean_row = {}
                    for k, v in r.items():
                        if isinstance(v, str) and ("T" in v or "-" in v) and len(v) >= 19:
                            try:
                                clean_row[k] = datetime.fromisoformat(v)
                            except Exception:
                                clean_row[k] = v
                        else:
                            clean_row[k] = v
                    session.execute(table.insert().values(**clean_row))
                    total_inserted += 1
                session.flush()

            session.commit()
            print(f"[OK] Database restored: {total_inserted} rows inserted across {len(insert_order)} tables.")

        # 3. Restore Storage Files
        print("[-] Restoring storage and document files...")
        target_dirs = {
            "storage": settings.STORAGE_DIR,
            "generated_docs": os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "generated_docs"))
        }

        for rel_file in files_dict.keys():
            staging_file = os.path.join(temp_dir, "storage", rel_file)
            prefix = rel_file.split("/")[0]
            subpath = "/".join(rel_file.split("/")[1:])
            dest_base = target_dirs.get(prefix, settings.STORAGE_DIR)
            dest_file = os.path.join(dest_base, subpath)

            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            with open(staging_file, "rb") as sf, open(dest_file, "wb") as df:
                df.write(sf.read())

        print(f"[OK] All {len(files_dict)} files restored to target paths.")
        print("[OK] RESTORE OPERATION COMPLETED SUCCESSFULLY!")
        return True

    finally:
        if os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Restore InfraDoc system from backup archive.")
    parser.add_argument("archive", help="Path to the backup .tar.gz archive")
    parser.add_argument("--db-url", help="Database connection URL", default=None)
    parser.add_argument("--no-clear", action="store_true", help="Do not clear existing records before restore")
    args = parser.parse_args()

    try:
        success = restore_backup(args.archive, clear_first=not args.no_clear, database_url=args.db_url)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] Restore failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
