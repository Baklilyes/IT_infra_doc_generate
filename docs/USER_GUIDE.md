# Manuel Utilisateur - InfraDoc

## 1. Connexion et Gestion des Rôles

L'application est accessible depuis n'importe quel navigateur sur le réseau d'entreprise à l'adresse configurée (ex: `http://<IP_SERVEUR>:3001`).

### 1.1 Comptes de Démonstration Disponibles
| Rôle | Identifiant | Mot de passe | Usage principal |
| :--- | :--- | :--- | :--- |
| **Administrateur** | `admin` | `AdminStrongPassword123!` | Administration des comptes et paramètres système |
| **Ingénieur** | `engineer_demo` | `EngineerPass123!` | Saisie technique, imports, schémas, soumission |
| **Responsable Technique** | `lead_demo` | `LeadPass123!` | Revue d'architecture, dérogations, pré-approbation |
| **Validateur Final** | `validator_demo` | `ValPass123!` | Examen global, validation définitive, scellement |

---

## 2. Parcours Fonctionnel par Module

### 2.1 Projets et Multi-Sites (`/projects`)
- **Création de projet :** Définir une référence unique (ex: `PRJ-2026-001`), le nom, le client, la langue documentaire (Français ou Anglais) et le responsable technique.
- **Gestion des sites :** Un projet peut comporter plusieurs sites géographiques (ex: Datacenter Principal, Site de Secours, Agences régionales).
- **Emplacements et Baies :** Pour chaque site, vous pouvez définir des salles informatiques et des baies/racks d'accueil.
- **Duplication & Archivage :** Duplication isolée en un clic pour créer un projet modèle sans collision de références.

### 2.2 Inventaire Technique (`/inventory`)
- Couvre les **8 familles d'infrastructure** :
  1. *Réseau :* Commutateurs, routeurs, interfaces physiques, Port-Channels LACP, SVI.
  2. *Sécurité :* Pare-feu, clusters HA, tunnels VPN IPsec, zones LAN/DMZ/WAN.
  3. *Serveurs :* Hyperviseurs, serveurs bare-metal Linux/Windows Server, rôles AD DS/DNS.
  4. *Virtualisation :* Clusters VMware vSphere, vCenter, machines virtuelles.
  5. *Stockage :* Baies SAN NVMe-oF / iSCSI, volumes, multipathing.
  6. *Sauvegarde :* Serveurs Veeam Backup & Replication, dépôts de stockage NAS immuables.
  7. *Services d'infrastructure :* Serveurs NTP, serveurs DNS Anycast, supervision Zabbix.
  8. *Cloud et Hybridation :* Passerelles ExpressRoute, VPN multi-cloud.
- Traçabilité des états : Statut d'installation (*Planifié, Installé, En service*) et état de vérification (*À vérifier, Proposé par IA, Vérifié*).

### 2.3 Ingestion et Imports de Données (`/imports`)
- **Fichiers tabulaires (Excel `.xlsx` / CSV `.csv`) :**
  - Téléchargement du fichier avec détection automatique des colonnes et suggestions de mapping.
  - Aperçu avant import avec contrôle des doublons de noms d'hôtes ou d'adresses IP.
  - Validation interactive ligne à ligne avant injection en base.
- **Configurations CLI (Cisco IOS `.cfg` / Fortinet FortiOS `.conf`) :**
  - Extraction automatisée du hostname, des interfaces, adresses IP, masques, descriptions et VLANs associés.
  - Détection et masquage automatique des secrets (`<SECRET_MASQUÉ>`).

### 2.4 Schémas d'Architecture Vectoriels SVG (`/architecture`)
- **Vue Physique :** Visualisation des baies, serveurs, routeurs et commutateurs avec indication des statuts de service.
- **Topologie Logique :** Arborescence hiérarchique Coeur $\rightarrow$ Distribution $\rightarrow$ Accès et segmentation par VLAN.
- **Matrice des Flux :** Cartographie des interconnexions et règles de communication entre zones réseau.
- Tous les schémas sont exportables en SVG haute résolution et intégrés automatiquement dans les rapports HLD et LLD.

### 2.5 Moteur de Cohérence et Dérogations (`/validations`)
- Analyse déterministe en continu de l'infrastructure :
  - Détection des adresses IP en doublon.
  - Détection des conflits CIDR et chevauchements de sous-réseaux.
  - Passerelles par défaut situées hors de la plage du sous-réseau.
  - VLANs appliqués sur une interface mais non définis dans le plan d'adressage.
  - Détection de mots de passe ou secrets stockés en clair.
- **Levée de dérogation (Waivers) :** Le Responsable Technique peut autoriser une exception justifiée avec horodatage et motif obligatoire, levant le blocage de publication.

### 2.6 Copilote IA Local et Génération Documentaire (`/documents`)
- **Copilote IA Ollama (100% Local) :** Génération de synthèses d'architecture, argumentaires techniques et procédures de recette sans transfert externe.
- **Livrables générés :**
  1. **HLD (High-Level Design) :** Dossier d'architecture globale, matrice des zones et schémas directeurs.
  2. **LLD (Low-Level Design) :** Dossier technique détaillé, plans d'adressage IP, configurations d'interfaces et paramètres systèmes.
  3. **Annexes de Configuration :** Synthèse exhaustive des scripts et paramètres avec secrets masqués.
  4. **Dossier de Mise en Service (Commissioning) :** Fiches de tests de recette et PV de validation.
- Disponibles au format Microsoft Word (`.docx`) et Adobe PDF (`.pdf`).

### 2.7 Workflow d'Approbation (`/validations`)
1. **Soumission Ingénieur :** L'ingénieur termine la saisie et soumet le dossier pour revue technique.
2. **Revue Technique :** Le responsable technique examine le dossier, vérifie les contrôles de cohérence, et accorde l'approbation technique ou renvoie pour correction avec motif obligatoire.
3. **Validation Finale :** Le validateur final examine l'ensemble et accorde la validation définitive.
4. **Verrouillage (Locking) :** Le projet et les documents associés sont verrouillés en lecture seule.
5. **Nouvelle Version (Branching) :** En cas d'évolution ultérieure de l'infrastructure, l'utilisateur peut brancher une nouvelle version de travail (ex: v1.1 ou v2.0) en conservant intacte l'archive historique v1.0.
