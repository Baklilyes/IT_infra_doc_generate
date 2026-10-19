# Architecture de Sécurité, Matrice RBAC et Isolation de l'IA

## 1. Principes Directeurs de Sécurité

L'application **InfraDoc** a été développée selon les principes de sécurité par défaut (**Security by Design**) :
1. **Zéro dépendance Cloud externe :** Fonctionnement étanche en réseau local fermé (**air-gapped**).
2. **Contrôle d'accès strict côté serveur (RBAC) :** L'authentification par token JWT et la vérification des permissions sont appliquées systématiquement sur chaque route API du backend FastAPI.
3. **Séparation des tâches (Separation of Duties - SoD) :** Les créateurs de dossiers ne peuvent pas valider leurs propres travaux.
4. **Masquage systématique des secrets :** Mots de passe, clés pré-partagées IPsec et communautés SNMP sont masqués sous la forme `<SECRET_MASQUÉ>` dans les requêtes de consultation, les documents générés et les contextes transmis à l'IA.
5. **Isolation totale du modèle IA :** Le runtime IA Ollama est cantonné au réseau interne Docker, sans aucun accès SSH, API d'administration d'équipements ou shell d'exécution.

---

## 2. Matrice des Rôles et Permissions (RBAC)

L'application implémente exclusivement les 4 rôles métier requis par le cahier des charges :

| Domaine Fonctionnel | Administrateur (`administrator`) | Ingénieur (`engineer`) | Responsable Technique (`technical_lead`) | Validateur Final (`final_validator`) |
| :--- | :---: | :---: | :---: | :---: |
| **Gestion des comptes utilisateurs** (`/api/auth/users`) |  Lecture & Écriture | ❌ Refus 403 | ❌ Refus 403 | ❌ Refus 403 |
| **Consultation des projets et inventaires** |  Accès complet |  Accès complet |  Accès complet |  Accès complet |
| **Création / Modification Projets & Sites** |  Autorisé |  Autorisé | ❌ Lecture seule | ❌ Lecture seule |
| **Saisie et Imports (CSV, Excel, Cisco, Fortinet)** |  Autorisé |  Autorisé | ❌ Lecture seule | ❌ Lecture seule |
| **Lancement des contrôles de cohérence** |  Autorisé |  Autorisé |  Autorisé |  Autorisé |
| **Levée de dérogation technique (Waiver)** |  Autorisé | ❌ Non autorisé |  Autorisé |  Autorisé |
| **Génération des schémas et documents (HLD/LLD)** |  Autorisé |  Autorisé |  Autorisé |  Autorisé |
| **Soumission d'un projet pour validation** |  Autorisé |  Autorisé | ❌ | ❌ |
| **Revue technique (Approbation / Renvoi)** |  Autorisé (bypass) | ❌ Refus 403 |  Autorisé | ❌ Refus 403 |
| **Validation finale et scellement du dossier** |  Autorisé (bypass) | ❌ Refus 403 | ❌ Refus 403 |  Autorisé |
| **Création d'une nouvelle version de travail** |  Autorisé |  Autorisé |  Autorisé |  Autorisé |

---

## 3. Séparation des Responsabilités (Separation of Duties - SoD)

Pour satisfaire aux exigences d'audit et de conformité réglementaire :
- **Interdiction d'auto-approbation :** Si un utilisateur avec un rôle supérieur (ex. Administrateur ou Responsable Technique) est l'auteur créateur ou le soumissionnaire d'un projet, le moteur de workflow lui interdit d'effectuer sa propre revue technique.
- **Séparation Revue Technique / Validation Finale :** Le validateur final ne peut pas être la même personne physique ayant réalisé la revue technique pour la même version du projet.
- **Révocation automatique en cas de falsification :** Dès qu'un équipement, une interface, un segment ou une configuration est modifié sur un projet en cours d'approbation (`IN_REVIEW`), toutes les approbations partielles sont automatiquement révoquées et le projet repasse à l'état `DRAFT` avec une trace d'audit horodatée.

---

## 4. Politique de Masquage des Secrets

Conformément à la Section 6.13 du MASTER_PROMPT :
1. **En base de données :** Les paramètres marqués `is_secret=True` (ou dont la clé contient `password`, `secret`, `key`, `community`, `token`) sont identifiés.
2. **À l'affichage API :** Les valeurs sont systématiquement remplacées par la constante `<SECRET_MASQUÉ>`.
3. **Dans les exports Word (.docx) et PDF :** Les annexes de configuration et les tableaux d'équipements ne font jamais apparaître de mot de passe en clair.
4. **Dans les prompts envoyés à l'IA locale :** Une passe d'assainissement regex remplace toute chaîne sensible avant la constitution du prompt JSON. Les logs du serveur ne contiennent aucun secret.

---

## 5. Isolation Étanche de l'IA Locale (Ollama)

### 5.1 Architecture Air-Gapped
- Le service Ollama tourne dans un conteneur dédié relié au bridge interne Docker `infradoc_net`.
- Aucun port d'Ollama n'est exposé sur l'interface réseau de la machine hôte.
- Le backend FastAPI est le seul composant capable de communiquer en HTTP avec `http://ollama:11434`.

### 5.2 Absence Totale de Capacités d'Exécution
- L'application **ne dispose d'aucun client SSH, Telnet, SNMP d'écriture ou shell système** connecté aux équipements.
- Toutes les commandes ou configurations produites par le modèle IA local sont étiquetées comme **propositions indicatives** (`ai_proposed`).
- Elles sont destinées exclusivement à la relecture humaine par l'ingénieur et le responsable technique.
- L'IA n'a aucun pouvoir décisionnel dans le workflow d'approbation.

### 5.3 Dégradation Gracieuse
En cas d'arrêt ou d'indisponibilité du conteneur Ollama, le backend intercepte l'erreur et bascule immédiatement sur un mode déterministe de secours :
- Tous les documents DOCX et PDF restent générables à partir des données structurées exactes de la base.
- Un avertissement explicite signale l'absence du copilote IA sans bloquer le reste de l'application.
