# Procédure Opérationnelle de Sauvegarde et Restauration (Disaster Recovery)

## 1. Vue d'Ensemble

L'application **InfraDoc** intègre un mécanisme unifié et déterministe de sauvegarde et de restauration couvrant :
1. **L'intégralité des données en base :** Utilisateurs, projets, multi-sites, inventaires, interfaces réseau, segments VLAN, configurations, dérogations de cohérence, décisions de workflow et métadonnées documentaires.
2. **L'ensemble des artefacts physiques :** Fichiers d'imports (CSV, XLSX, configurations CLI Cisco / Fortinet) et documents générés (fichiers Microsoft Word `.docx` et rapports PDF `.pdf`).
3. **Un manifeste d'intégrité cryptographique (`manifest.json`) :** Horodatage UTC, version logicielle, nombre de lignes exportées par table, et empreintes **SHA256** de chaque fichier archivé.

Les sauvegardes sont compressées au format standard Linux `tar.gz` (`infradoc_backup_YYYYMMDD_HHMMSS.tar.gz`).

---

## 2. Procédure de Sauvegarde

### 2.1 Sauvegarde Manuelle (Environnement Docker Linux)
Depuis le serveur hébergeant l'application :
```bash
cd /opt/infradoc
./scripts/backup.sh
```

Ou directement avec Python dans le conteneur backend :
```bash
docker compose exec backend python /app/scripts/backup.py --output-dir /app/backups
```

Sur système Windows (développement / test local) :
```powershell
.\scripts\backup.ps1
```

### 2.2 Structure de l'Archive de Sauvegarde
Chaque archive `.tar.gz` contient l'arborescence suivante :
```
infradoc_backup_20261019_083000.tar.gz
├── database_dump.json       # Export sérialisé complet des tables relationnelles
├── manifest.json            # Métadonnées, comptages et empreintes SHA256
└── storage/                 # Documents Word/PDF et fichiers d'imports
    ├── storage/
    │   └── test_evidence.txt
    └── generated_docs/
        ├── PRJ-DOC-HLD_HLD_v1.0.docx
        └── PRJ-DOC-LLD_LLD_v1.0.pdf
```

Exemple d'extrait de `manifest.json` :
```json
{
  "version": "1.0.0",
  "created_at": "2026-10-19T08:30:00.123456+00:00",
  "environment": "production",
  "database_records": {
    "users": 4,
    "projects": 3,
    "sites": 6,
    "equipment": 28,
    "network_segments": 14,
    "interfaces": 42,
    "configurations": 18,
    "workflow_decisions": 12,
    "documents": 8
  },
  "files": {
    "generated_docs/PRJ-DOC-HLD_HLD_v1.0.docx": {
      "size_bytes": 48210,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    }
  },
  "total_files_backed_up": 8
}
```

### 2.3 Automatisation par Tâche Planifiée (Cron Linux)
Pour planifier une sauvegarde automatique chaque nuit à 02h00 avec rétention sur 30 jours :

Éditer la table cron de l'utilisateur système :
```bash
crontab -e
```

Ajouter la ligne suivante :
```cron
0 2 * * * /opt/infradoc/scripts/backup.sh >> /var/log/infradoc_backup.log 2>&1
# Nettoyage automatique des sauvegardes de plus de 30 jours
0 3 * * * find /opt/infradoc/backups -name "infradoc_backup_*.tar.gz" -mtime +30 -delete
```

---

## 3. Procédure de Restauration (Disaster Recovery)

La restauration s'exécute à partir de n'importe quelle archive `.tar.gz` valide produite par le script de sauvegarde.

> [!CAUTION]
> L'opération de restauration écrase les données actuelles en base pour réinjecter fidèlement les enregistrements archivés. En cas de doute, lancez d'abord une sauvegarde de sécurité de l'état présent.

### 3.1 Restauration sur Serveur Docker Linux
```bash
cd /opt/infradoc
./scripts/restore.sh ./backups/infradoc_backup_20261019_083000.tar.gz
```

### 3.2 Restauration sur Système Windows
```powershell
.\scripts\restore.ps1 -Archive .\backups\infradoc_backup_20261019_083000.tar.gz
```

### 3.3 Contrôles Automatiques d'Intégrité lors de la Restauration
Le moteur de restauration exécute les vérifications obligatoires suivantes :
1. **Extraction sécurisée :** Utilisation du filtre d'extraction sécurisé (`filter="data"`) prévenant tout risque de traversée de répertoire.
2. **Contrôle cryptographique SHA256 :** Chaque fichier restauré est recalculé et confronté à l'empreinte stockée dans `manifest.json`. Si le moindre bit est corrompu ou altéré, la restauration s'interrompt immédiatement avec une alerte explicite.
3. **Réinsertion relationnelle ordonnée :** Insertion respectant scrupuleusement les contraintes de clés étrangères (Utilisateurs $\rightarrow$ Projets $\rightarrow$ Sites $\rightarrow$ Emplacements $\rightarrow$ Équipements $\rightarrow$ Interfaces/Configurations $\rightarrow$ Documents $\rightarrow$ Workflow).

---

## 4. Test d'Intégration Automatisé

La fiabilité de la sauvegarde et de la restauration est couverte par un test d'intégration automatisé (`backend/tests/test_backup_restore.py`).

Pour lancer ce test à tout moment :
```bash
pytest backend/tests/test_backup_restore.py -v
```
Ce test valide :
- L'exportation de projets, équipements et fichiers réels.
- La génération d'une archive `.tar.gz`.
- La destruction simulée des données en base et des fichiers physiques.
- La restauration complète et la vérification bit-à-bit des données et empreintes SHA256.
