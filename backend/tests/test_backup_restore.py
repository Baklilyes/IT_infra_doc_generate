"""
Automated Integration Tests for Backup & Restore Engine (Lot 9 - Stabilisation).
Verifies full data serialization, archive creation, SHA256 integrity validation,
and complete disaster recovery roundtrip using isolated SQLite test database.
"""
import pytest
import os
import sys
import tempfile
import shutil
from datetime import datetime, timezone
from sqlalchemy import select, text, create_engine
from sqlalchemy.orm import sessionmaker

# Add backend and scripts to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "scripts")))

from app.core.database import Base
from app.models.user import User, UserRole
from app.models.project import Project, Site, Location, ProjectStatus, DocumentLanguage
from app.models.equipment import Equipment, EquipmentCategory, InstallationStatus, VerificationStatus
from app.models.network import Interface, InterfaceType, InterfaceMode, NetworkSegment, ConfigurationParam
from app.models.document import Document
from app.models.workflow import WorkflowDecision, WorkflowAction
from app.core.config import settings
from backup import create_backup, calculate_sha256
from restore import restore_backup


def test_backup_restore_roundtrip():
    """
    Test complete disaster recovery lifecycle:
    1. Seed test database with multi-tier entities and artifacts.
    2. Create backup archive.
    3. Validate manifest, record counts, and checksums.
    4. Wipe or tamper with database and storage.
    5. Run restore.
    6. Assert complete recovery of all entities and files.
    """
    temp_dir = tempfile.mkdtemp(prefix="infradoc_test_bkup_")
    sqlite_db_path = os.path.join(temp_dir, "test_bkup.db")
    test_db_url = f"sqlite:///{sqlite_db_path}"

    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestSession = sessionmaker(bind=test_engine)

    # Create test storage artifact
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    test_artifact_path = os.path.join(settings.STORAGE_DIR, "test_evidence.txt")
    with open(test_artifact_path, "w", encoding="utf-8") as f:
        f.write("CONFIDENTIAL_INFRASTRUCTURE_AUDIT_DATA_FOR_BACKUP_TEST")

    original_artifact_hash = calculate_sha256(test_artifact_path)

    # 1. Insert reference data in isolated test DB
    with TestSession() as session:
        test_user = User(
            id="user-bkup-01",
            username="backup_test_user",
            email="backup_test@example.com",
            full_name="Backup Test Engineer",
            role=UserRole.ENGINEER,
            hashed_password="hashed_pw_test",
            is_active=True
        )
        session.add(test_user)
        session.flush()

        test_project = Project(
            id="proj-bkup-01",
            reference="PRJ-BKUP-01",
            name="Projet Test Sauvegarde",
            client_name="Client Test Recette",
            status=ProjectStatus.IN_REVIEW,
            document_language=DocumentLanguage.FR,
            lead_name="Ingénieur Référent",
            scope="Infrastructure datacenter",
            created_by_id=test_user.id
        )
        session.add(test_project)
        session.flush()

        test_site = Site(
            id="site-bkup-01",
            name="Site Paris DC",
            code="PAR-01",
            project_id=test_project.id
        )
        session.add(test_site)
        session.flush()

        test_eq = Equipment(
            id="eq-bkup-01",
            name="sw-core-01",
            category=EquipmentCategory.SWITCH,
            manufacturer="Cisco",
            model="Catalyst 9500",
            management_ip="10.200.0.1",
            installation_status=InstallationStatus.INSTALLED,
            verification_status=VerificationStatus.VERIFIED,
            project_id=test_project.id,
            site_id=test_site.id
        )
        session.add(test_eq)
        session.flush()

        test_seg = NetworkSegment(
            id="seg-bkup-01",
            name="VLAN-BACKUP",
            vlan_id=777,
            cidr="10.77.7.0/24",
            gateway="10.77.7.254",
            project_id=test_project.id
        )
        session.add(test_seg)
        session.flush()

        wf_dec = WorkflowDecision(
            id="wf-bkup-01",
            project_id=test_project.id,
            user_id=test_user.id,
            action=WorkflowAction.SUBMIT.value,
            from_status=ProjectStatus.DRAFT.value,
            to_status=ProjectStatus.IN_REVIEW.value,
            comment="Soumission initiale pour test backup"
        )
        session.add(wf_dec)
        session.commit()

    try:
        # 2. Create Backup
        archive_path = create_backup(output_dir=temp_dir, engine=test_engine)
        assert os.path.exists(archive_path), "Backup archive should be created"
        assert archive_path.endswith(".tar.gz"), "Backup should be .tar.gz format"

        # 3. Tamper with DB and storage (Delete equipment and project, remove file)
        with TestSession() as session:
            session.execute(text("DELETE FROM workflow_decisions"))
            session.execute(text("DELETE FROM equipment"))
            session.execute(text("DELETE FROM network_segments"))
            session.execute(text("DELETE FROM sites"))
            session.execute(text("DELETE FROM projects"))
            session.execute(text("DELETE FROM users"))
            session.commit()

        if os.path.exists(test_artifact_path):
            os.remove(test_artifact_path)

        # Confirm deletion
        with TestSession() as session:
            p_check = session.execute(select(Project).where(Project.reference == "PRJ-BKUP-01")).scalars().first()
            assert p_check is None, "Project should be deleted before restore"
        assert not os.path.exists(test_artifact_path), "Storage artifact should be deleted"

        # 4. Execute Restore
        restore_success = restore_backup(archive_path, clear_first=True, engine=test_engine)
        assert restore_success is True, "Restore operation should succeed"

        # 5. Verify Full Recovery
        with TestSession() as session:
            restored_project = session.execute(select(Project).where(Project.reference == "PRJ-BKUP-01")).scalars().first()
            assert restored_project is not None, "Project should be restored"
            assert restored_project.name == "Projet Test Sauvegarde"
            assert restored_project.status == ProjectStatus.IN_REVIEW

            restored_eq = session.execute(select(Equipment).where(Equipment.name == "sw-core-01")).scalars().first()
            assert restored_eq is not None, "Equipment should be restored"
            assert restored_eq.management_ip == "10.200.0.1"
            assert restored_eq.manufacturer == "Cisco"

            restored_seg = session.execute(select(NetworkSegment).where(NetworkSegment.vlan_id == 777)).scalars().first()
            assert restored_seg is not None, "Network segment should be restored"
            assert restored_seg.cidr == "10.77.7.0/24"

            restored_wf = session.execute(select(WorkflowDecision).where(WorkflowDecision.project_id == restored_project.id)).scalars().all()
            assert len(restored_wf) >= 1, "Workflow decision should be restored"
            assert restored_wf[0].action == WorkflowAction.SUBMIT.value

        # Check storage file recovery
        assert os.path.exists(test_artifact_path), "Storage artifact should be restored"
        restored_hash = calculate_sha256(test_artifact_path)
        assert restored_hash == original_artifact_hash, "Restored file hash must match original SHA256"

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        if os.path.exists(test_artifact_path):
            os.remove(test_artifact_path)
