# IT Infrastructure Documentation Generator (InfraDoc)

Application web d'infrastructure IT permettant de constituer, vérifier, valider et générer le dossier technique final d'une installation complète (**HLD**, **LLD**, **Annexes de configuration** et **Dossier de mise en service**) en formats **Microsoft Word (.docx)** et **Adobe PDF (.pdf)**.

Développée pour fonctionner en environnement professionnel interne étanche (**air-gapped** / réseau d'administration) avec copilote d'IA 100% local (**Ollama**).

---

## 1. Vue d'Ensemble de la Réalisation par Lots (Lots 0 à 9)

L'intégralité du plan de réalisation exigé par le cahier des charges est terminée et validée par les tests :

| Lot | Intitulé | Description & Fonctionnalités Réalisées | Statut |
| :---: | :--- | :--- | :---: |
| **Lot 0** | **Inspection et Planification** | Cartographie du dépôt, dimensionnement des dépendances et plan directeur. |  Terminé |
| **Lot 1** | **Socle Applicatif** | FastAPI, Next.js 14, PostgreSQL 16, Auth JWT bcrypt, RBAC strict (4 rôles), i18n FR/EN. |  Terminé |
| **Lot 2** | **Projets et Multi-Sites** | Gestion multi-projets, multi-sites géographiques, cycle de vie, duplication et archivage. |  Terminé |
| **Lot 3** | **Inventaire & Modèle Technique** | 8 familles d'infrastructure, interfaces, SVI, LACP, VLANs, masquage des secrets. |  Terminé |
| **Lot 4** | **Imports & Adaptateurs CLI** | Ingestion Excel (`.xlsx`), CSV, parsers CLI Cisco IOS & Fortinet FortiOS, aperçu & conflits. |  Terminé |
| **Lot 5** | **Contrôles de Cohérence** | Moteur déterministe de validation d'infrastructure (doublons IP, CIDR, VLANs, dérogations). |  Terminé |
| **Lot 6** | **Schémas d'Architecture SVG** | Schémas vectoriels SVG (vue physique par baie, topologie logique, matrice des flux). |  Terminé |
| **Lot 7** | **IA Locale & Génération Doc** | Copilote Ollama conteneurisé, assainissement des secrets, moteurs DOCX & PDF (HLD, LLD, Recette). |  Terminé |
| **Lot 8** | **Workflow de Validation** | Circuit d'approbation (Ingénieur $\rightarrow$ Resp. Technique $\rightarrow$ Validateur Final), SoD, scellement. |  Terminé |
| **Lot 9** | **Stabilisation & Finalisation** | Moteur unifié de sauvegarde/restauration SHA256, tests sécurité E2E, documentation et démonstration. |  Terminé |

---

## 2. Rôles et Comptes de Démonstration

L'application applique un contrôle strict des accès par rôle (RBAC côté serveur) :

| Rôle | Identifiant | Mot de passe | Responsabilités Métier |
| :--- | :--- | :--- | :--- |
| **Administrateur** | `admin` | `AdminStrongPassword123!` | Gestion des comptes utilisateurs et paramètres globaux |
| **Ingénieur** | `engineer_demo` | `EngineerPass123!` | Saisie technique, imports, schémas, soumission du dossier |
| **Responsable Technique** | `lead_demo` | `LeadPass123!` | Revue d'architecture, dérogations de cohérence, pré-validation |
| **Validateur Final** | `validator_demo` | `ValPass123!` | Examen global, validation définitive, scellement et verrouillage |

---

## 3. Démarrage Rapide avec Docker Compose

### 3.1 Lancement des Services
```bash
# 1. Copier les variables d'environnement
cp .env.example .env

# 2. Démarrer l'ensemble des conteneurs
docker compose -f compose.yaml up -d --build

# 3. Télécharger le modèle IA local recommandé dans Ollama
docker compose exec ollama ollama pull qwen2.5-coder:7b

# 4. Initialiser le compte administrateur
docker compose exec backend python scripts/init_admin.py

# 5. (Optionnel) Peupler le jeu d'essai multi-sites entreprise
docker compose exec backend python scripts/seed_demo_data.py
```

### 3.2 Accès aux Interfaces
- **Application Web (Frontend) :** `http://localhost:3000`
- **Documentation API Interactive (OpenAPI / Swagger) :** `http://localhost:8000/api/docs`
- **Diagnostic de Santé (Health Check) :** `http://localhost:8000/api/health`

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

### 4.2 Frontend (Next.js 14)
```bash
cd frontend
npm install
npm run dev
```

---

## 5. Procédures de Sauvegarde et Restauration (Disaster Recovery)

L'application dispose d'outils unifiés créant une archive horodatée `.tar.gz` contenant la base de données sérialisée, les documents Word/PDF, et un manifeste cryptographique avec empreintes **SHA256**.

### 5.1 Sauvegarde
```bash
# Environnement Linux / Docker
./scripts/backup.sh

# Environnement Windows PowerShell
.\scripts\backup.ps1
```

### 5.2 Restauration
```bash
# Environnement Linux / Docker
./scripts/restore.sh ./backups/infradoc_backup_YYYYMMDD_HHMMSS.tar.gz

# Environnement Windows PowerShell
.\scripts\restore.ps1 -Archive .\backups\infradoc_backup_YYYYMMDD_HHMMSS.tar.gz
```

Consulter le guide complet : [docs/BACKUP_RESTORE.md](docs/BACKUP_RESTORE.md).

---

## 6. Exécution de la Suite de Tests Automatisés

### 6.1 Tests Backend Pytest (63 tests unitaires, intégration et sécurité)
```bash
.\backend\.venv\Scripts\pytest -v
```
Couverture des tests automatisés :
- `test_auth.py` : Hachage bcrypt, génération JWT, login, rejet inactif, refus 403 RBAC.
- `test_projects.py` : CRUD projets, multi-sites, emplacements, cycle de vie, duplication isolée.
- `test_inventory.py` : Équipements (8 familles), interfaces LACP/SVI, segments VLAN, détection doublons IP.
- `test_imports.py` : Imports CSV et Excel (`openpyxl`), parsers CLI Cisco IOS et Fortinet FortiOS, conflits.
- `test_consistency.py` : Moteur déterministe, chevauchement CIDR, VLANs orphelins, dérogations (waivers).
- `test_diagrams.py` : Génération des schémas vectoriels SVG (physique, logique, flux).
- `test_documents.py` : Génération DOCX et PDF (HLD, LLD, Recette), assainissement des prompts IA, fallback.
- `test_workflow.py` : Moteur d'approbation, séparation des tâches (SoD), verrouillage, branching v2.
- `test_backup_restore.py` : Cycle complet sauvegarde $\rightarrow$ destruction $\rightarrow$ restauration $\rightarrow$ intégrité SHA256.
- `test_security_e2e.py` : Matrice RBAC complète, injection / path traversal, masquage des secrets.

### 6.2 Compilation et Vérification Frontend
```bash
cd frontend
npm run build
```

---

## 7. Documentation Technique et Références

- [Guide de Déploiement Linux et Docker](docs/DEPLOYMENT.md)
- [Procédure de Sauvegarde et Restauration](docs/BACKUP_RESTORE.md)
- [Architecture de Sécurité, RBAC et Isolation IA](docs/SECURITY_AUDIT.md)
- [Manuel Utilisateur des 4 Rôles et Modules](docs/USER_GUIDE.md)
- [Matrice de Validation des 28 Critères de Réception](docs/ACCEPTANCE_CRITERIA.md)
- [Gabarit des Configurations et Exemples d'Import](examples/)
