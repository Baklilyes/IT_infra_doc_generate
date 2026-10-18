# IT Infrastructure Documentation Generator (InfraDoc)

Application web d'infrastructure IT permettant de constituer, vérifier, valider et générer le dossier technique final d'une installation complète (HLD, LLD, Annexes de configuration et Dossier de mise en service) en formats DOCX et PDF.

---

## 1. Architecture et Composants

L'application est conçue pour fonctionner de manière étanche sur serveur Linux local (réseau d'entreprise sans dépendance cloud externe) :

- **Frontend :** Next.js 14, TypeScript, Tailwind CSS, Lucide Icons. Interface bilingue (Français / Anglais).
- **Backend :** FastAPI, Python 3.13, Pydantic v2, SQLAlchemy 2 (asyncpg + psycopg 3).
- **Base de données :** PostgreSQL 16 Alpine avec migrations versionnées (Alembic).
- **Moteur IA Local :** Ollama conteneurisé sur le réseau interne (sans accès externe ni télémétrie).
- **Sécurité :** Authentification JWT, hachage bcrypt, contrôle d'accès strict par rôle (RBAC) côté serveur.
- **Conteneurisation :** Docker Compose avec volumes persistants pour PostgreSQL, Ollama et le stockage documentaire.

---

## 2. Rôles et Permissions

L'application implémente uniquement les 4 rôles métier exigés par le cahier des charges :

| Rôle | Responsabilités | Identifiants Démo par défaut |
| :--- | :--- | :--- |
| **Administrateur** | Gestion des comptes utilisateurs et paramètres | `admin` / `AdminStrongPassword123!` |
| **Ingénieur** | Saisie des données, imports, schémas, soumission du dossier | `engineer_demo` / `EngineerPass123!` |
| **Responsable technique** | Revue technique, demande de correction, approbation technique | `lead_demo` / `LeadPass123!` |
| **Validateur final** | Examen final, validation définitive ou renvoi pour correction | `validator_demo` / `ValPass123!` |

---

## 3. Déploiement Rapide avec Docker Compose

### 3.1 Lancement des services
```bash
# Copier et ajuster les variables d'environnement
cp .env.example .env

# Démarrer l'ensemble des conteneurs
docker compose -f compose.yaml up -d --build

# Vérifier la santé des services
docker compose ps
```

### 3.2 Téléchargement du modèle IA local dans Ollama
```bash
docker compose exec ollama ollama pull qwen2.5-coder:7b
```

### 3.3 Initialisation du compte administrateur
```bash
docker compose exec backend python scripts/init_admin.py
```

L'application est immédiatement accessible :
- **Frontend :** http://localhost:3000
- **Documentation API (OpenAPI) :** http://localhost:8000/api/docs
- **Health Check :** http://localhost:8000/api/health

---

## 4. Développement Local (Hors Docker)

### 4.1 Backend (Python 3.13)
```bash
cd backend
python -m venv .venv
.\.venv\Scripts\activate      # Sur Windows
# source .venv/bin/activate   # Sur Linux/macOS

pip install -r requirements.txt
python scripts/init_admin.py
uvicorn app.main:app --reload --port 8000
```

### 4.2 Frontend (Next.js)
```bash
cd frontend
npm install
npm run dev
```

---

## 5. Exécution des Tests Automatisés

### Tests Unitaires et Sécurité Backend (pytest)
```bash
# Depuis la racine du projet
.\backend\.venv\Scripts\pytest -v
```
Les tests couvrent :
- Hachage de mot de passe bcrypt et vérification
- Émission et validation de tokens JWT
- Connexion avec identifiants valides et invalides
- Rejet des comptes désactivés
- Contrôle d'accès strict (RBAC) vérifiant le refus 403 pour les utilisateurs non autorisés
- Diagnostic de santé modulaire (`/api/health`)

### Compilation et Vérification Frontend
```bash
cd frontend
npm run build
```

---

## 6. Procédures de Sauvegarde et Restauration

### Sauvegarde
```bash
# Sauvegarde de la base de données PostgreSQL
docker compose exec -T db pg_dump -U infradoc infradoc_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Sauvegarde des fichiers et documents générés
tar -czvf storage_backup_$(date +%Y%m%d_%H%M%S).tar.gz storage/
```

### Restauration
```bash
# Restauration de la base de données
docker compose exec -T db psql -U infradoc -d infradoc_db < backup_file.sql

# Restauration du stockage
tar -xzvf storage_backup_file.tar.gz
```
