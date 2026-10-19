"""
Seed Script: Initialise realistic demonstration infrastructure dataset.
Creates 4 role accounts, 1 multi-site enterprise project, 14 equipment across 8 infrastructure families,
network segments, interfaces, and masked configuration parameters.
Compatible with SQLite and PostgreSQL.
"""
import sys
import os
import argparse
from datetime import datetime, timezone
from sqlalchemy import select, create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.core.config import settings
from app.core.database import sync_engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.project import Project, Site, Location, ProjectStatus, DocumentLanguage
from app.models.equipment import Equipment, EquipmentCategory, InstallationStatus, VerificationStatus
from app.models.network import Interface, InterfaceType, InterfaceMode, NetworkSegment, ConfigurationParam
from app.models.workflow import WorkflowDecision, WorkflowAction


def seed_demo_data(engine=None, database_url=None):
    if engine is not None:
        active_engine = engine
    elif database_url:
        active_engine = create_engine(database_url)
    else:
        active_engine = sync_engine

    Base.metadata.create_all(bind=active_engine)
    Session = sessionmaker(bind=active_engine)

    with Session() as session:
        print("[-] Seeding default accounts (4 mandatory roles)...")
        demo_accounts = [
            ("admin", "admin@infra-doc.local", "Administrateur Système", UserRole.ADMINISTRATOR, "AdminStrongPassword123!"),
            ("engineer_demo", "engineer@infra-doc.local", "Alexandre Martin (Ingénieur)", UserRole.ENGINEER, "EngineerPass123!"),
            ("lead_demo", "lead@infra-doc.local", "Sophie Laurent (Resp. Technique)", UserRole.TECHNICAL_LEAD, "LeadPass123!"),
            ("validator_demo", "validator@infra-doc.local", "Marc Delorme (Validateur Final)", UserRole.FINAL_VALIDATOR, "ValPass123!"),
        ]

        users_map = {}
        for uname, email, fname, role, pwd in demo_accounts:
            u = session.execute(select(User).where(User.username == uname)).scalars().first()
            if not u:
                u = User(
                    username=uname,
                    email=email,
                    full_name=fname,
                    role=role,
                    hashed_password=hash_password(pwd),
                    is_active=True
                )
                session.add(u)
                session.flush()
            users_map[uname] = u

        # Create Project
        print("[-] Creating demonstration enterprise project...")
        proj_ref = "PRJ-2026-HYBRID-DC"
        project = session.execute(select(Project).where(Project.reference == proj_ref)).scalars().first()
        if not project:
            project = Project(
                reference=proj_ref,
                name="Refonte Infrastructure Hybride Datacenter & Cloud",
                client_name="Banque & Mutuelle Alliance (BMA)",
                description="Modernisation du socle d'infrastructure IT : résilience multi-sites, segmentation réseau Zero-Trust, virtualisation haute disponibilité et extension Cloud Azure.",
                scope="Périmètre Datacenter Principal Paris (DC1), Datacenter Secours Lyon (DC2) et interconnexion ExpressRoute.",
                lead_name="Alexandre Martin",
                contributors="Alexandre Martin (Ingénieur Réseau), David Moreau (Architecte Cloud), Sarah Cohen (Systèmes & Stockage)",
                status=ProjectStatus.IN_PREPARATION,
                document_language=DocumentLanguage.FR,
                created_by_id=users_map["engineer_demo"].id
            )
            session.add(project)
            session.flush()

        # Create Sites
        print("[-] Creating physical sites and datacenter locations...")
        site_dc1 = session.execute(select(Site).where(Site.name == "Datacenter Principal Paris (DC1)", Site.project_id == project.id)).scalars().first()
        if not site_dc1:
            site_dc1 = Site(
                project_id=project.id,
                name="Datacenter Principal Paris (DC1)",
                code="DC1-PARIS",
                address="45 Boulevard Haussmann, 75009 Paris",
                city="Paris",
                country="France"
            )
            session.add(site_dc1)
            session.flush()

        site_dc2 = session.execute(select(Site).where(Site.name == "Datacenter Secours Lyon (DC2)", Site.project_id == project.id)).scalars().first()
        if not site_dc2:
            site_dc2 = Site(
                project_id=project.id,
                name="Datacenter Secours Lyon (DC2)",
                code="DC2-LYON",
                address="12 Rue de la République, 69002 Lyon",
                city="Lyon",
                country="France"
            )
            session.add(site_dc2)
            session.flush()

        # Create Locations
        loc_rack1 = session.execute(select(Location).where(Location.name == "Baie RACK-01 (Coeur Réseau & Sécurité)", Location.site_id == site_dc1.id)).scalars().first()
        if not loc_rack1:
            loc_rack1 = Location(
                site_id=site_dc1.id,
                name="Baie RACK-01 (Coeur Réseau & Sécurité)",
                room="Salle Serveurs Alpha",
                rack="RACK-01",
                notes="Bâtiment A"
            )
            session.add(loc_rack1)
            session.flush()

        loc_rack2 = session.execute(select(Location).where(Location.name == "Baie RACK-02 (Compute & Storage)", Location.site_id == site_dc1.id)).scalars().first()
        if not loc_rack2:
            loc_rack2 = Location(
                site_id=site_dc1.id,
                name="Baie RACK-02 (Compute & Storage)",
                room="Salle Serveurs Alpha",
                rack="RACK-02",
                notes="Bâtiment A"
            )
            session.add(loc_rack2)
            session.flush()

        # Create Network Segments (VLANs & Subnets)
        print("[-] Creating network segments and VLAN segmentation plan...")
        segments_def = [
            (10, "VLAN-MGMT-ADMIN", "10.10.10.0/24", "10.10.10.254", "LAN", "Réseau d'administration out-of-band"),
            (20, "VLAN-PRODUCTION-APPS", "10.10.20.0/24", "10.10.20.254", "Production", "Zone applicative métiers et microservices"),
            (30, "VLAN-DATABASE-ORACLE", "10.10.30.0/24", "10.10.30.254", "Production", "Bases de données relationnelles Oracle et PostgreSQL"),
            (40, "VLAN-STORAGE-ISCSI", "10.10.40.0/24", "10.10.40.254", "Storage", "Réseau dédié stockage SAN iSCSI multipathing Jumbo Frames"),
            (50, "VLAN-BACKUP-VEEAM", "10.10.50.0/24", "10.10.50.254", "Backup", "Flux de sauvegarde Veeam et réplication inter-sites"),
            (99, "VLAN-DMZ-EXTERNE", "10.10.99.0/24", "10.10.99.254", "DMZ", "Zone démilitarisée pour services web et reverse proxy"),
        ]
        for vid, vname, cidr, gw, zone, desc in segments_def:
            seg = session.execute(select(NetworkSegment).where(NetworkSegment.vlan_id == vid, NetworkSegment.project_id == project.id)).scalars().first()
            if not seg:
                seg = NetworkSegment(
                    project_id=project.id,
                    site_id=site_dc1.id,
                    vlan_id=vid,
                    name=vname,
                    cidr=cidr,
                    gateway=gw,
                    zone=zone,
                    description=desc,
                    dns_servers="10.10.10.1, 10.10.10.2",
                    ntp_servers="10.10.10.10"
                )
                session.add(seg)

        # Create 14 Equipment items across 8 families
        print("[-] Creating equipment items (8 infrastructure families covered)...")
        equipment_data = [
            # 1. Réseau
            ("sw-core-01", EquipmentCategory.SWITCH, "Core Switch", "Cisco", "Catalyst 9500-48Y4C", "10.10.10.254", loc_rack1.id, site_dc1.id, "Commutateur de coeur DC1"),
            ("sw-core-02", EquipmentCategory.SWITCH, "Core Switch", "Cisco", "Catalyst 9500-48Y4C", "10.10.10.253", loc_rack1.id, site_dc1.id, "Commutateur de coeur redondant DC1"),
            ("rtr-wan-01", EquipmentCategory.ROUTER, "Edge Router", "Cisco", "ISR 4451-X", "10.10.10.250", loc_rack1.id, site_dc1.id, "Routeur de bordure WAN & interconnexions"),
            # 2. Sécurité
            ("fw-edge-01", EquipmentCategory.FIREWALL, "Perimeter Firewall", "Fortinet", "FortiGate 200F", "10.10.10.1", loc_rack1.id, site_dc1.id, "Pare-feu primaire HA Active-Passive"),
            ("fw-edge-02", EquipmentCategory.FIREWALL, "Perimeter Firewall", "Fortinet", "FortiGate 200F", "10.10.10.2", loc_rack1.id, site_dc1.id, "Pare-feu secondaire HA Active-Passive"),
            # 3. Serveurs physiques
            ("srv-hyp-01", EquipmentCategory.PHYSICAL_SERVER, "Hypervisor Node", "Dell", "PowerEdge R750xs", "10.10.10.101", loc_rack2.id, site_dc1.id, "Serveur hyperviseur ESXi 8.0 Nœud 1"),
            ("srv-hyp-02", EquipmentCategory.PHYSICAL_SERVER, "Hypervisor Node", "Dell", "PowerEdge R750xs", "10.10.10.102", loc_rack2.id, site_dc1.id, "Serveur hyperviseur ESXi 8.0 Nœud 2"),
            ("srv-dc-01", EquipmentCategory.PHYSICAL_SERVER, "Domain Controller", "HPE", "ProLiant DL360 Gen10", "10.10.20.10", loc_rack2.id, site_dc1.id, "Contrôleur de domaine Windows Server 2022 / DNS"),
            # 4. Virtualisation
            ("vm-vcenter", EquipmentCategory.VIRTUAL_MACHINE, "Virtual Appliance", "VMware", "vCenter Server Appliance 8.0", "10.10.10.50", loc_rack2.id, site_dc1.id, "Gestion centralisée du cluster VMware"),
            # 5. Stockage
            ("san-powerstore-01", EquipmentCategory.STORAGE, "SAN Storage Array", "Dell", "PowerStore 1000T", "10.10.40.10", loc_rack2.id, site_dc1.id, "Baie SAN NVMe-oF et iSCSI unifiée"),
            # 6. Sauvegarde et continuité
            ("srv-veeam-01", EquipmentCategory.PHYSICAL_SERVER, "Backup Server", "Dell", "PowerEdge R450", "10.10.50.10", loc_rack2.id, site_dc1.id, "Serveur d'orchestration Veeam Backup & Replication"),
            ("nas-backup-target", EquipmentCategory.STORAGE, "Backup Storage Repository", "Synology", "RackStation RS3621xs+", "10.10.50.20", loc_rack2.id, site_dc1.id, "Dépôt de sauvegarde immuable NAS"),
            # 7. Services d'infrastructure
            ("srv-zabbix-mon", EquipmentCategory.VIRTUAL_MACHINE, "Monitoring Server", "Linux RHEL", "RHEL 9.3 LTS", "10.10.10.60", loc_rack2.id, site_dc1.id, "Supervision des flux et métrologie système"),
            # 8. Cloud et interconnexion
            ("gw-azure-expressroute", EquipmentCategory.GENERIC, "Hybrid Cloud Gateway", "Microsoft Azure", "ExpressRoute Gateway", "10.10.99.10", loc_rack1.id, site_dc1.id, "Passerelle hybride d'interconnexion Azure"),
        ]

        eq_map = {}
        for name, cat, subcat, vendor, model, ip, loc_id, site_id, role in equipment_data:
            eq = session.execute(select(Equipment).where(Equipment.name == name, Equipment.project_id == project.id)).scalars().first()
            if not eq:
                eq = Equipment(
                    project_id=project.id,
                    site_id=site_id,
                    location_id=loc_id,
                    name=name,
                    category=cat,
                    subcategory=subcat,
                    manufacturer=vendor,
                    model=model,
                    management_ip=ip,
                    installation_status=InstallationStatus.IN_SERVICE,
                    verification_status=VerificationStatus.VERIFIED,
                    role=role
                )
                session.add(eq)
                session.flush()
            eq_map[name] = eq

        # Create Network Interfaces
        print("[-] Configuring interfaces and logical links...")
        if "sw-core-01" in eq_map and "sw-core-02" in eq_map:
            sw1 = eq_map["sw-core-01"]
            sw2 = eq_map["sw-core-02"]
            if not session.execute(select(Interface).where(Interface.equipment_id == sw1.id, Interface.name == "Port-channel1")).scalars().first():
                session.add(Interface(
                    equipment_id=sw1.id,
                    name="Port-channel1",
                    interface_type=InterfaceType.PORT_CHANNEL,
                    mode=InterfaceMode.TRUNK,
                    allowed_vlans="10,20,30,40,50,99",
                    admin_status="up",
                    operational_status="up",
                    description="Inter-Core Switch Trunk Lag 2x10G",
                    connected_equipment_id=sw2.id,
                    connected_interface_name="Port-channel1"
                ))

        # Create Masked Configuration Parameters
        print("[-] Inserting structured configuration parameters (with masked secrets)...")
        configs_to_seed = [
            ("system", "ntp_servers", "10.10.10.10, 10.10.10.11", False),
            ("system", "dns_domain", "corp.bma-finance.loc", False),
            ("system", "syslog_server", "10.10.10.60:514", False),
            ("security", "snmp_v2c_community", "SecretSnmpCommunity99!", True),
            ("security", "ipsec_pre_shared_key", "SuperSecretPskKey2026@BMA!", True),
            ("security", "tacacs_key", "TacacsSecretAuthKey88!", True),
        ]
        for cat, key, val, is_sec in configs_to_seed:
            param = session.execute(select(ConfigurationParam).where(ConfigurationParam.project_id == project.id, ConfigurationParam.key == key)).scalars().first()
            if not param:
                param = ConfigurationParam(
                    project_id=project.id,
                    category=cat,
                    key=key,
                    value=val,
                    is_secret=is_sec,
                    description=f"Paramètre système {key}"
                )
                session.add(param)

        session.commit()
        print("\n[OK] DEMO DATASET SEEDED SUCCESSFULLY!")
        print("=================================================================")
        print(f"  Project Reference : {project.reference}")
        print(f"  Project Name      : {project.name}")
        print(f"  Client            : {project.client_name}")
        print(f"  Sites Created     : 2 (Paris DC1, Lyon DC2)")
        print(f"  Equipment Count   : 14 items across 8 families")
        print(f"  VLAN Segments     : 6 segments (VLAN 10, 20, 30, 40, 50, 99)")
        print("=================================================================")
        print("  Demo Credentials Available:")
        print("  1. Administrator  : admin / AdminStrongPassword123!")
        print("  2. Engineer       : engineer_demo / EngineerPass123!")
        print("  3. Technical Lead : lead_demo / LeadPass123!")
        print("  4. Final Validator: validator_demo / ValPass123!")
        print("=================================================================\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed InfraDoc demonstration infrastructure dataset.")
    parser.add_argument("--db-url", help="Database connection URL", default=None)
    args = parser.parse_args()

    seed_demo_data(database_url=args.db_url)
