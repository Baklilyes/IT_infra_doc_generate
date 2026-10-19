# Guide de Déploiement et d'Exploitation (Serveur Linux Local)

## 1. Présentation Générale

L'application **IT Infrastructure Documentation Generator (InfraDoc)** est spécialement conçue pour être déployée sur un serveur Linux d'entreprise au sein d'un réseau local interne (**air-gapped** ou réseau d'administration sans dépendance vis-à-vis d'un cloud public).

L'architecture s'appuie sur des conteneurs Docker orchestrés via Docker Compose :
- **infradoc_frontend :** Serveur d'interface Next.js / React / Tailwind CSS (Port interne 3000).
- **infradoc_backend :** API FastAPI / Python 3.13 (Port interne 8000).
- **infradoc_postgres :** Base de données relationnelle PostgreSQL 16 Alpine avec volume persistant (Port 5432 interne, non exposé publiquement).
- **infradoc_ollama :** Runtime d'inférence d'IA locale Ollama (Port 11434 interne au réseau Docker).

---

## 2. Prérequis Système et Matériels

### 2.1 Système d'Exploitation Recommandé
- Ubuntu Server 22.04 LTS / 24.04 LTS
- Debian 12 (Bookworm)
- Red Hat Enterprise Linux (RHEL) 8 / 9 ou Rocky Linux 9

### 2.2 Dimensionnement Matériel

| Profil | CPU | RAM | Stockage Disque | Accélération GPU | Modèle IA Préconisé |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Standard (Inférence CPU)** | 8 vCPU | 16 Go | 100 Go SSD / NVMe | Aucune | `qwen2.5-coder:7b` ou `mistral:7b` (quantifié 4-bit) |
| **Performances Élevées (GPU)** | 8+ vCPU | 32 Go | 250 Go NVMe | 1x NVIDIA RTX (>= 12 Go VRAM) | `qwen2.5-coder:7b` / `llama3.1:8b` (inférence < 2s) |
| **Environnement Léger (Sans IA)** | 4 vCPU | 8 Go | 50 Go SSD | N/A | IA désactivable (`AI_ENABLED=false`) |

### 2.3 Paquets Requis
- **Docker Engine :** Version 24.0+ ou supérieure
- **Docker Compose Plugin :** Version 2.20+ ou supérieure
- **NVIDIA Container Toolkit :** Recommandé si un GPU NVIDIA est présent pour Ollama

---

## 3. Procédure d'Installation Pas-à-Pas

### 3.1 Clonage et Préparation du Répertoire
```bash
git clone <URL_DEPOT_INTERNE>/IT_tech.git /opt/infradoc
cd /opt/infradoc
```

### 3.2 Configuration des Variables d'Environnement
Copier le gabarit de configuration et renseigner les mots de passe forts :
```bash
cp .env.example .env
chmod 600 .env
```

Éditer le fichier `.env` :
```env
# Sécurité applicative
SECRET_KEY=cle_secrete_aleatoire_tres_longue_minimum_32_caracteres_prod!
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Compte administrateur initial
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@infradoc.internal.loc
ADMIN_PASSWORD=VotreMotDePasseAdminTresSecurise2026!

# Base de données PostgreSQL
POSTGRES_USER=infradoc
POSTGRES_PASSWORD=PostgresMotDePasseComplexe99!
POSTGRES_DB=infradoc_db

# Moteur IA Local (Ollama conteneurisé)
AI_ENABLED=true
OLLAMA_BASE_URL=http://ollama:11434
AI_MODEL_NAME=qwen2.5-coder:7b
AI_TIMEOUT_SECONDS=120

# Chemins de stockage
STORAGE_DIR=/app/storage
TEMPLATES_DIR=/app/templates
```

### 3.3 Construction et Démarrage des Conteneurs
```bash
docker compose -f compose.yaml up -d --build
```

Vérifier la bonne santé des conteneurs :
```bash
docker compose ps
```
Tous les conteneurs (`infradoc_postgres`, `infradoc_ollama`, `infradoc_backend`, `infradoc_frontend`) doivent être à l'état `healthy` ou `running`.

---

## 4. Configuration du Runtime IA Local (Ollama)

### 4.1 Téléchargement du Modèle Recommandé
Exécuter la commande de téléchargement du modèle validé en interne :
```bash
docker compose exec ollama ollama pull qwen2.5-coder:7b
```

*Modèles alternatifs testés :*
- `docker compose exec ollama ollama pull mistral:7b`
- `docker compose exec ollama ollama pull llama3.1:8b`

### 4.2 Test de Bon Fonctionnement de l'IA
```bash
curl -s http://localhost:8000/api/documents/ai-status | jq .
```
Réponse attendue :
```json
{
  "ai_status": {
    "available": true,
    "model": "qwen2.5-coder:7b",
    "base_url": "http://ollama:11434"
  },
  "total_generated": 0,
  "allowed_types": ["hld", "lld", "config_annexes", "commissioning"]
}
```

---

## 5. Initialisation des Comptes et Données

### 5.1 Création du Compte Administrateur Initial
```bash
docker compose exec backend python scripts/init_admin.py
```

### 5.2 (Optionnel) Chargement du Jeu de Démonstration Entreprise
Pour charger immédiatement une infrastructure multi-sites de démonstration (14 équipements, VLANs, pare-feu, serveurs, stockage, 4 comptes de test) :
```bash
docker compose exec backend python scripts/seed_demo_data.py
```

---

## 6. Exposition Réseau et Reverse Proxy

Par défaut, l'application écoute sur :
- **Frontend Web :** Port `3000` (ex: `http://192.168.10.50:3000`)
- **Backend API :** Port `8000` (ex: `http://192.168.10.50:8000/api/docs`)

### 6.1 Configuration Reverse Proxy Nginx Recommandée (HTTPS / TLS Interne)
Pour exposer l'application sous un port unique `443` avec certificat TLS d'autorité interne :

```nginx
server {
    listen 80;
    server_name infradoc.internal.loc;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name infradoc.internal.loc;

    ssl_certificate /etc/ssl/certs/infradoc.crt;
    ssl_certificate_key /etc/ssl/private/infradoc.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 50M;

    # Frontend
    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }
}
```

---

## 7. Procédure de Mise à Jour (Zero Data Loss)

Les volumes persistants (`infradoc_postgres_data`, `infradoc_storage_data`, `infradoc_ollama_models`) garantissent qu'aucune donnée, aucun document et aucun modèle téléchargé ne sont perdus lors des mises à jour.

```bash
cd /opt/infradoc

# 1. Sauvegarde préalable de précaution
./scripts/backup.sh

# 2. Récupération des dernières sources
git pull origin master

# 3. Rebuild et redémarrage des services
docker compose up -d --build

# 4. Exécution des migrations de schéma de base de données
docker compose exec backend alembic upgrade head

# 5. Contrôle de bon fonctionnement
curl -f http://localhost:8000/api/health
```
