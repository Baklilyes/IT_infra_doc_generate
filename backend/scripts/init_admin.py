"""
Script d'initialisation du premier compte administrateur.
Utilise les variables ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select
from app.core.config import settings
from app.core.database import SyncSessionLocal, sync_engine, Base
from app.core.security import hash_password
from app.models.user import User, UserRole

def init_admin():
    print("Vérification et initialisation de la base de données...")
    Base.metadata.create_all(bind=sync_engine)

    with SyncSessionLocal() as session:
        # Check if admin already exists
        stmt = select(User).where(User.username == settings.ADMIN_USERNAME)
        admin = session.execute(stmt).scalars().first()

        if admin:
            print(f"Le compte administrateur '{settings.ADMIN_USERNAME}' existe déjà.")
            return

        print(f"Création du compte administrateur initial '{settings.ADMIN_USERNAME}' ({settings.ADMIN_EMAIL})...")
        new_admin = User(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            full_name="Administrateur Système",
            role=UserRole.ADMINISTRATOR,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            is_active=True
        )
        session.add(new_admin)
        session.commit()
        print("Compte administrateur initial créé avec succès.")

if __name__ == "__main__":
    init_admin()
