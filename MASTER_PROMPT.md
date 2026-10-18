# MASTER_PROMPT.md
# IT Infrastructure Documentation Generator

**Version :** 1.0  
**Langues :** Français / English  
**Déploiement :** Serveur Linux local, réseau interne  
**Objectif :** Développer une application web permettant de constituer, vérifier, valider et générer le dossier technique final d'une installation d'infrastructure IT complète, en PDF et Word modifiable.

---

## 1. Rôle et consignes générales

Tu es un ingénieur logiciel senior, architecte applicatif et développeur full-stack chargé de construire une application de documentation d'infrastructure IT exploitable en environnement professionnel.

Tu dois développer l'application à partir des exigences de ce document. Avant de modifier le dépôt :

1. Inspecte le dépôt, les fichiers existants, les technologies déjà utilisées et les fonctionnalités déjà réalisées.
2. Conserve les éléments existants qui sont corrects et compatibles avec ce cahier des charges.
3. Identifie les écarts entre l'existant et les exigences.
4. Présente un plan de réalisation par lots, puis implémente les fonctionnalités de manière incrémentale.
5. Ne remplace pas une application existante par un nouveau projet sans nécessité démontrée.
6. Ne prétends jamais qu'une fonctionnalité est terminée si elle n'est pas implémentée et testée.

### Règle de périmètre impérative

**N'ajoute aucune fonctionnalité métier non définie dans ce document.** N'invente pas de workflow, d'intégration, de rôle, de constructeur pris en charge ou de méthode de collecte. Si une décision indispensable manque, utilise une valeur par défaut prudente et documente-la, ou demande une clarification avant d'implémenter la fonctionnalité concernée.

Les données inconnues doivent rester inconnues. Ne présente jamais une valeur estimée, proposée ou extraite partiellement comme une configuration réellement appliquée et vérifiée.

---

## 2. Objectif de l'application

Créer une application web simple et professionnelle qui permet de :

- créer un projet d'installation d'infrastructure IT ;
- gérer un ou plusieurs sites dans un projet ;
- saisir manuellement le matériel et ses paramètres ;
- importer des inventaires et fichiers de configuration ;
- prévisualiser, corriger et valider les données importées ;
- documenter l'architecture physique et logique ;
- vérifier la cohérence des informations ;
- générer un HLD, un LLD, les annexes de configuration et le dossier de mise en service ;
- exporter les documents en PDF et en DOCX modifiable ;
- faire valider le dossier selon le workflow ingénieur, responsable technique, validation finale ;
- conserver l'historique des modifications et les versions générées.

### Familles d'infrastructure couvertes

1. Réseau : switches, routeurs, VLAN, adressage IP, routage, interfaces, liens et agrégation.
2. Sécurité : firewalls, interfaces, zones, règles de filtrage, NAT, VPN et haute disponibilité.
3. Serveurs : Windows Server, Linux, rôles et services.
4. Virtualisation : VMware, Hyper-V et autres plateformes lorsque les données sont disponibles dans un format pris en charge.
5. Stockage : SAN, NAS, volumes, LUN, protocoles et multipathing.
6. Sauvegarde et continuité : solutions, dépôts, politiques, rétention, réplication et résultats de tests.
7. Services d'infrastructure : DNS, DHCP, NTP, annuaire, supervision et certificats.
8. Cloud et interconnexion : connexions et composants cloud/hybrides documentés par l'utilisateur ou via un format pris en charge.

La prise en charge multi-constructeurs doit être progressive. Ne prétends pas analyser toutes les marques ou tous les formats. Chaque format pris en charge doit être explicitement documenté et testé.

---

## 3. Décisions d'architecture obligatoires

### 3.1 Stack technique

- **Frontend :** Next.js, TypeScript.
- **Interface :** Tailwind CSS et une bibliothèque de composants maintenue et accessible.
- **Backend :** Python avec FastAPI.
- **Base de données :** PostgreSQL.
- **ORM et migrations :** SQLAlchemy et Alembic.
- **Génération Word :** `python-docx`, avec modèles DOCX contrôlés.
- **Génération PDF :** génération à partir de modèles HTML/CSS avec un moteur PDF adapté, ou ReportLab si plus approprié. La méthode retenue doit être documentée et testée.
- **Import Excel :** `openpyxl`.
- **Import CSV :** bibliothèque standard Python ou pandas si justifié.
- **Schémas :** SVG généré à partir des données structurées ; schémas lisibles et intégrables dans DOCX/PDF.
- **Conteneurisation :** Docker Compose.
- **Tests :** pytest côté backend et tests adaptés au frontend.
- **Documentation technique :** Markdown dans le dépôt.

Ne substitue pas la stack sans raison technique documentée et validée.

### 3.2 Architecture applicative

Utiliser un backend modulaire organisé par domaine fonctionnel, avec séparation claire entre :

- routes/API ;
- logique métier et validations ;
- modèles de données ;
- accès aux données ;
- analyseurs/importeurs ;
- moteur de schémas ;
- moteur documentaire ;
- authentification et autorisations ;
- tests.

Le frontend et le backend peuvent être déployés dans des conteneurs séparés. PostgreSQL et le stockage des fichiers doivent disposer de volumes persistants.

Ne crée pas de microservices indépendants, de cluster Kubernetes, de broker de messages ou de service cloud pour le périmètre initial.

### 3.3 Déploiement local

L'application doit être accessible depuis un navigateur sur le réseau interne, via l'adresse IP ou le nom DNS du serveur.

Fournir :

- `docker-compose.yml` ou `compose.yaml` ;
- fichiers `.env.example` sans secrets réels ;
- Dockerfiles adaptés ;
- instructions d'installation et de mise à jour ;
- procédure de sauvegarde et de restauration ;
- contrôles de santé des services ;
- volumes persistants pour PostgreSQL et les fichiers ;
- configuration des ports documentée ;
- procédure de création du premier compte administrateur.

Ne pas exposer PostgreSQL directement au réseau utilisateur. L'exposition de l'application doit être configurable. Ne suppose pas qu'un certificat ou un reverse proxy existe déjà.

### 3.4. Architecture IA locale — exigence validée

L'application doit intégrer une IA exécutée localement sur le serveur interne. Aucun fournisseur d'IA externe ni aucune API d'inférence hébergée dans le cloud ne doit être requis pour les fonctions IA.

#### Composants

- **Runtime de modèle local :** utiliser Ollama comme choix initial pour servir le modèle local. Le runtime doit être isolé dans un conteneur ou un service interne dédié et accessible uniquement depuis le backend.
- **Modèle :** le nom et la version du modèle doivent être configurables. Ne pas figer un modèle précis avant d'avoir vérifié les ressources CPU, RAM et, si disponible, GPU du serveur. Documenter le modèle réellement testé, sa taille, ses exigences et ses limites.
- **Service d'orchestration IA :** implémenté dans le backend FastAPI, avec des modules distincts pour la préparation du contexte, la construction des prompts, l'appel au runtime local, la validation des sorties et la traçabilité.
- **Prompts versionnés :** conserver les instructions système et modèles de prompts dans le dépôt, avec version et tests. Les données importées ou fournies par l'utilisateur sont du contenu à analyser, jamais des instructions qui peuvent remplacer les règles de sécurité du système.
- **Validation déterministe :** après chaque génération, vérifier le format de sortie, les champs obligatoires, les références aux équipements, les valeurs réseau et les incohérences détectables avec les validateurs métier existants. Une réponse du modèle ne remplace jamais ces contrôles.
- **Source de vérité :** les données structurées du projet et les fichiers source approuvés restent la référence. L'IA ne doit pas inventer de matériel, d'adresses IP, de VLAN, de liens, de versions, de capacités, de résultats de tests ou de contraintes absentes.

#### Flux de génération

1. L'utilisateur choisit un projet et décrit l'objectif technique ainsi que les contraintes connues.
2. Le backend récupère uniquement les données du projet auxquelles l'utilisateur est autorisé à accéder.
3. Le service IA contrôle les informations minimales disponibles et produit une liste explicite des données manquantes, hypothèses et points à confirmer. Il ne transforme pas une hypothèse en fait.
4. Si les informations sont suffisantes, l'IA propose une architecture et des configurations adaptées aux constructeurs, modèles et versions réellement renseignés.
5. L'IA génère les étapes détaillées, les commandes proposées, les prérequis, les contrôles de vérification et, lorsque cela est pertinent et documenté, les étapes de retour arrière.
6. Les validateurs déterministes vérifient la sortie. Les erreurs et avertissements sont affichés avec le contenu généré.
7. L'utilisateur examine, corrige si nécessaire, puis choisit de conserver la proposition comme version de travail.
8. Les éléments retenus peuvent alimenter le HLD, le LLD, les annexes de configuration et le dossier de mise en service, en identifiant explicitement le contenu comme généré/proposé par IA jusqu'à vérification humaine.

#### Contraintes d'exécution et de sécurité

- Les appels d'inférence se font exclusivement vers le runtime local configuré.
- Le service IA n'a aucun accès direct aux équipements, à SSH, aux API d'administration d'équipements ou à un shell permettant d'exécuter les commandes générées.
- Les commandes produites sont du texte destiné à être relu et appliqué manuellement par une personne autorisée. L'application ne les exécute pas.
- Le service IA ne peut ni approuver un document ni modifier les décisions du workflow de validation.
- Masquer les secrets avant d'envoyer un contexte au modèle, sauf si une valeur secrète est indispensable à la génération ; dans ce cas, ne pas la transmettre au modèle et utiliser un marqueur explicite tel que `<SECRET_MASQUÉ>`.
- Ne pas enregistrer les secrets dans les prompts, traces, journaux ou résultats générés.
- Ne pas envoyer de données à des services externes de télémétrie ou d'analytique par l'intégration IA.
- Le déploiement doit pouvoir fonctionner sans accès Internet une fois les images de conteneurs et le modèle téléchargés. Documenter séparément la procédure contrôlée de chargement ou de mise à jour du modèle.
- Prévoir des délais d'attente, une gestion d'erreur claire si le runtime ou le modèle est indisponible, et une limite configurable de taille du contexte et de la sortie.
- Ne pas ajouter de base vectorielle, de RAG, de fine-tuning, d'agent autonome, d'accès Internet, de recherche web ou d'exécution automatique : ces fonctions ne sont pas validées dans le périmètre actuel.

#### Configuration et exploitation

Documenter au minimum les variables d'environnement suivantes, avec des noms adaptés à la convention du projet :
- activation de l'IA locale ;
- URL interne du runtime Ollama ;
- nom/version du modèle ;
- délai d'attente ;
- limites de taille d'entrée et de sortie.

Fournir un health check qui distingue l'état du backend, l'accessibilité du runtime et la disponibilité du modèle configuré. Ne pas déclarer l'IA opérationnelle si le modèle demandé n'est pas disponible.

---

## 4. Langues et internationalisation

L'interface doit prendre en charge :

- Français ;
- Anglais.

Exigences :

- bouton ou menu de changement de langue ;
- traductions centralisées, sans textes d'interface dispersés en dur ;
- mêmes fonctions disponibles dans les deux langues ;
- formats de date et nombres adaptés à la langue ;
- choix de la langue du document lors de la génération ;
- traduction des titres, sections, légendes, statuts et libellés du dossier ;
- conservation des noms techniques réels : hostname, commandes CLI, noms d'interfaces, VLAN, IP, versions logicielles et valeurs importées ne doivent pas être traduits ;
- absence de mélange accidentel de langues dans un même document.

Ne pas traduire automatiquement les données techniques importées. Les champs descriptifs saisis par l'utilisateur restent tels qu'ils ont été saisis.

---

## 5. Utilisateurs, rôles et autorisations

Implémenter uniquement les rôles suivants :

1. **Administrateur** : gère les comptes et les paramètres nécessaires au fonctionnement de l'application.
2. **Ingénieur** : crée et modifie les projets, saisit les données, importe les fichiers, prépare les schémas et soumet le dossier à validation.
3. **Responsable technique** : examine le dossier soumis, demande des corrections ou donne son approbation technique.
4. **Validateur final** : effectue la validation finale du dossier.

Les droits doivent être contrôlés côté backend, pas uniquement dans l'interface.

Règles :

- les utilisateurs non authentifiés ne peuvent pas accéder aux projets ou aux documents ;
- l'ingénieur peut préparer et soumettre un dossier ;
- le responsable technique peut approuver l'étape technique ou renvoyer le dossier pour correction ;
- le validateur final peut valider définitivement ou renvoyer le dossier pour correction ;
- un dossier validé ne doit pas être modifié silencieusement ;
- toute modification d'un dossier validé doit entraîner une nouvelle version de travail et une nouvelle validation avant publication de cette version ;
- les actions de validation doivent être enregistrées avec l'utilisateur, la date, l'action et un commentaire lorsqu'il est fourni.

Ne crée pas d'autres rôles métier sans validation préalable. Les permissions exactes doivent être centralisées et testées.

---

## 6. Modules fonctionnels

### 6.1. Tableau de bord

Afficher uniquement les informations utiles au travail documentaire :

- nombre de projets et répartition par statut ;
- projets récemment modifiés ;
- dossiers en attente de validation ;
- projets avec des données manquantes ou des erreurs de cohérence ;
- dernières versions documentaires générées.

Les chiffres doivent être calculés à partir des données réelles. Ne pas afficher de données de démonstration comme si elles étaient réelles en production.

### 6.2. Gestion des projets

Un projet contient :

- référence unique ;
- nom du projet ;
- client/entreprise ;
- description et périmètre ;
- un ou plusieurs sites ;
- responsable et intervenants ;
- dates prévues ou réelles disponibles ;
- statut ;
- langue documentaire ;
- historique et versions.

Fonctions : créer, consulter, modifier, rechercher, filtrer, archiver et dupliquer un projet lorsque cela est compatible avec la cohérence des références. La duplication doit créer de nouveaux identifiants et ne pas mélanger l'historique des deux projets.

Statuts de projet proposés pour le périmètre :
- Brouillon ;
- En préparation ;
- En validation ;
- Validé ;
- Clôturé.

Ne pas confondre le statut général du projet et le statut du workflow de validation documentaire.

### 6.3. Gestion des sites et emplacements

Permettre de définir les sites et, si renseigné, les salles techniques, baies et emplacements associés aux équipements.

Un site appartient à un projet. Un équipement appartient à un projet et peut être associé à un site et à un emplacement. Empêcher les liens incohérents entre projets différents.

### 6.4. Inventaire des équipements

Champs communs, lorsque disponibles :

- identifiant interne ;
- catégorie et sous-catégorie ;
- constructeur ;
- modèle ;
- nom d'hôte ;
- numéro de série ;
- adresse de gestion ;
- version logicielle/firmware ;
- rôle ;
- site et emplacement ;
- état d'installation ;
- source des données ;
- notes ;
- date de dernière mise à jour.

Créer des champs spécifiques selon la famille de l'équipement, sans imposer des champs de serveur à un switch ou des champs de firewall à une baie de stockage.

Familles initiales :
- switch ;
- routeur ;
- firewall ;
- serveur physique ;
- hyperviseur ;
- machine virtuelle ;
- stockage ;
- équipement Wi-Fi ;
- équipement ou service d'infrastructure générique.

Le modèle doit être extensible par des champs spécifiques contrôlés. Ne construis pas un catalogue exhaustif de tous les modèles du marché.

Fonctions :
- ajouter, consulter, modifier et supprimer avec confirmation ;
- recherche et filtres ;
- détection de doublons potentiels ;
- relations entre équipements ;
- association des interfaces et configurations ;
- import CSV/Excel avec correspondance des colonnes ;
- affichage des données manquantes.

### 6.5. Interfaces et connexions

Documenter les interfaces physiques et logiques avec les champs disponibles :

- équipement parent ;
- nom d'interface ;
- type ;
- adresse MAC si connue ;
- adresse IP et masque si applicable ;
- VLAN access ou trunk ;
- VLAN autorisés ;
- vitesse/duplex si connu ;
- état administratif/opérationnel si connu ;
- description ;
- équipement et interface distants ;
- type de lien ;
- agrégation ou redondance, si applicable ;
- source et statut de vérification.

Ne pas supposer qu'une interface est active si son état n'a pas été collecté ou confirmé.

### 6.6. Réseau et adressage

Documenter :

- VLAN ID et nom ;
- sous-réseau CIDR ;
- passerelle ;
- plages DHCP lorsqu'elles sont connues ;
- DNS/NTP et autres services associés ;
- zone ou usage ;
- équipements/interfaces concernés ;
- routes statiques ou protocoles de routage, lorsque documentés ;
- liens et dépendances.

Contrôler les erreurs manifestes : IP invalide, CIDR incorrect, VLAN hors plage, doublon exact, référence à un équipement inexistant et incohérences détectables. Signaler les chevauchements de sous-réseaux comme conflits potentiels, en tenant compte du contexte fourni.

### 6.7. Configuration technique

Permettre de saisir et documenter les paramètres des catégories couvertes :

- réseau et switching ;
- routage ;
- firewall et sécurité ;
- serveurs et systèmes ;
- virtualisation ;
- stockage ;
- sauvegarde ;
- services d'infrastructure ;
- cloud/interconnexion.

Chaque donnée structurée doit conserver autant que possible :
- valeur ;
- description ;
- équipement concerné ;
- source ;
- date de collecte/import/saisie ;
- statut de vérification ;
- utilisateur ayant effectué la dernière modification ;
- commentaire ou référence de preuve.

Les configurations CLI complètes peuvent être attachées comme fichiers de configuration source et référencées dans les annexes. Les secrets doivent être masqués dans les vues et les exports standards.

### 6.8. Import de fichiers

Formats prioritaires :
- CSV ;
- Excel `.xlsx` ;
- fichiers texte de configuration CLI pour les adaptateurs effectivement disponibles ;
- documents PDF/DOCX comme pièces de référence ;
- archives, uniquement si le traitement est sécurisé et les types de fichiers sont contrôlés.

Workflow d'import obligatoire :
1. choisir un fichier ;
2. vérifier le format et la taille ;
3. analyser sans exécuter le contenu ;
4. afficher un aperçu des données reconnues ;
5. signaler les champs inconnus, erreurs et doublons ;
6. laisser l'utilisateur corriger le mapping ou les données ;
7. demander confirmation ;
8. importer dans une transaction cohérente ;
9. enregistrer le résultat et la source ;
10. conserver un rapport d'import avec succès, avertissements et erreurs.

Ne pas écraser automatiquement une donnée existante. Pour les conflits, présenter les valeurs existantes et importées, puis demander une décision explicite.

Les fichiers importés sont des données non fiables. Prévenir les traversées de répertoires, les archives malveillantes, les fichiers trop volumineux et les formats inattendus. Ne jamais exécuter une configuration importée.

### 6.9. Adaptateurs multi-constructeurs

Créer une interface commune pour les analyseurs, par exemple :
- identification du format ;
- constructeur/famille reconnue ;
- version de l'adaptateur ;
- extraction des données structurées ;
- avertissements ;
- erreurs ;
- limites connues.

Commencer par un nombre limité d'adaptateurs déterminés par des exemples de fichiers disponibles et testables. Les formats non reconnus doivent être conservés comme pièces jointes et signalés comme non analysés.

Ne pas annoncer la prise en charge d'un constructeur sans test représentatif. Ajouter un nouvel adaptateur sans modifier le cœur du modèle de données autant que possible.

### 6.10. Architecture et schémas

Générer des schémas SVG à partir des données validées :
- architecture physique ;
- architecture logique ;
- VLAN et sous-réseaux ;
- connexions principales ;
- architecture de virtualisation lorsque les données sont présentes ;
- architecture de sauvegarde lorsque les données sont présentes.

Chaque schéma doit avoir un titre, une légende, une date/version et des références aux équipements représentés. Les schémas ne doivent pas inventer des liens, des flux ou une redondance.

Permettre la prévisualisation et la régénération des schémas après modification des données. Toute édition manuelle de disposition, si implémentée, ne doit pas modifier les faits techniques sous-jacents.

### 6.11. Contrôles de cohérence

Avant la génération, effectuer les contrôles possibles :
- équipement sans nom ou identifiant essentiel ;
- doublons potentiels ;
- adresse IP invalide ;
- sous-réseau/CIDR incorrect ;
- interfaces liées à un équipement inexistant ;
- VLAN ou sous-réseau référencé mais non défini ;
- liens incomplets ;
- données obligatoires manquantes ;
- divergences entre les informations importées et saisies ;
- contradictions entre HLD, LLD et inventaire.

Classer les résultats en erreur bloquante, avertissement ou information. Les règles doivent être explicites, testées et expliquées à l'utilisateur. Ne pas déclarer une configuration conforme à une norme ou une bonne pratique si aucun contrôle précis et documenté ne le justifie.

### 6.12. Génération documentaire

Produire les éléments suivants selon les données présentes et les sections sélectionnées :

#### A. Dossier de synthèse
- page de garde ;
- client, projet, site et responsables ;
- périmètre ;
- résumé de l'installation ;
- inventaire synthétique ;
- statut et version documentaire ;
- table des matières ;
- historique des versions.

#### B. HLD — High-Level Design
- objectifs et périmètre ;
- architecture générale ;
- composants principaux ;
- architecture physique/logique à haut niveau ;
- segmentation et zones ;
- interconnexions et dépendances ;
- redondance et sécurité lorsqu'elles sont documentées ;
- hypothèses, limites et éléments non renseignés.

#### C. LLD — Low-Level Design
- inventaire détaillé ;
- noms, modèles, versions et rôles ;
- plan d'adressage IP ;
- VLAN et sous-réseaux ;
- interfaces et connexions ;
- routage ;
- paramètres par équipement ;
- virtualisation et stockage lorsque documentés ;
- services d'infrastructure ;
- configuration de sécurité documentée ;
- tableaux et schémas détaillés.

#### D. Annexes de configuration
- références et extraits des configurations sources ;
- fichiers de configuration en annexe lorsque leur inclusion est autorisée ;
- avertissements sur les formats non analysés ;
- date et provenance ;
- secrets masqués par défaut.

#### E. Dossier de mise en service
- étapes d'installation renseignées ;
- tests et résultats ;
- anomalies et réserves ;
- validations ;
- sauvegarde des configurations, si renseignée ;
- références des preuves fournies.

Exigences documentaires :
- export PDF ;
- export DOCX modifiable ;
- choix de langue français ou anglais ;
- titres hiérarchisés ;
- sommaire ;
- numéros de page ;
- en-tête/pied de page avec projet et version ;
- tableaux lisibles ;
- schémas intégrés ;
- date de génération ;
- distinction claire entre données collectées, saisies, proposées et vérifiées ;
- sections absentes ou inconnues signalées proprement, jamais remplies par des valeurs fictives.

Le PDF et le DOCX d'une même génération doivent provenir du même instantané de données validées. Conserver les fichiers générés et leurs métadonnées.

### 6.13. Génération assistée par IA locale

Ajouter un espace de génération IA dans le projet. Cette fonction utilise exclusivement le runtime local défini à la section 3.4.

#### Capacités demandées

Pour les familles d'infrastructure déjà couvertes par l'application, l'utilisateur peut demander à l'IA de générer :
- une proposition d'architecture physique et/ou logique à partir des données fournies ;
- les choix de conception et leur justification ;
- des configurations techniques adaptées au constructeur, modèle et version lorsqu'ils sont connus ;
- des commandes de configuration sous forme de texte, clairement identifiées comme proposées et non exécutées ;
- une procédure d'installation ou de configuration détaillée, étape par étape ;
- les prérequis et dépendances ;
- les commandes ou méthodes de contrôle après mise en œuvre ;
- les tests attendus, les résultats attendus et les champs permettant à un technicien de consigner les résultats réels ;
- les risques, avertissements, hypothèses et données manquantes ;
- les étapes de retour arrière lorsque la procédure et la plateforme permettent de les décrire de manière fiable.

#### Règles de génération

- Le contexte doit provenir du projet sélectionné, des données saisies/importées et de la demande de l'utilisateur. Ne pas utiliser les données d'un autre projet.
- Si le constructeur, le modèle, la version, la topologie, les adresses ou une autre information nécessaire manque, l'IA doit le signaler et demander une précision ou fournir une proposition explicitement conditionnelle. Elle ne doit pas présenter des commandes génériques comme garanties compatibles.
- Les exemples de VLAN, d'adressage, de noms, de règles de sécurité, de routes ou de capacités doivent être identifiés comme exemples tant qu'ils ne sont pas validés par l'utilisateur.
- Pour les commandes générées, préciser l'équipement cible, le contexte d'exécution, les prérequis, les impacts/risques connus, la méthode de vérification et le retour arrière si applicable.
- Ne jamais prétendre qu'une commande a été exécutée, qu'une configuration a été appliquée ou qu'un test a réussi sans preuve saisie ou importée par l'utilisateur.
- Distinguer visuellement et dans les données les états : `Généré par IA`, `À vérifier`, `Vérifié par un utilisateur`. Ne pas ajouter d'état `Appliqué` automatique.
- Le contenu IA n'est pas automatiquement fusionné dans les données de référence du projet. Toute reprise de valeur structurée nécessite une action explicite de l'utilisateur et les contrôles de cohérence habituels.
- Une génération est enregistrée avec le projet, l'utilisateur demandeur, la date, le modèle/version utilisé, la version du prompt, les entrées de référence, le contenu généré et les avertissements. Ne pas y conserver de secrets.
- Les résultats retenus peuvent être insérés dans les documents HLD/LLD, les annexes de configuration et le dossier de mise en service, en conservant leur provenance.
- Les générations et leur revue restent soumises au workflow de validation documentaire existant. L'IA ne valide jamais à la place du responsable technique ou du validateur final.

#### Interface minimale

L'écran de génération comporte uniquement :
- sélection du projet et des équipements concernés, limités au projet courant ;
- champ de demande/instructions techniques ;
- affichage des données utilisées et des informations manquantes détectées ;
- action de génération ;
- résultat structuré en architecture, configuration, étapes, commandes, tests, risques et hypothèses, selon les sections disponibles ;
- affichage des avertissements de validation ;
- actions pour conserver la proposition comme version de travail ou l'écarter.

Ne pas ajouter de chat généraliste, de recherche Internet, de collecte automatique sur les équipements, d'application distante de configuration ou d'agent autonome.

### 6.14. Workflow de validation documentaire

Implémenter ce workflow strict :

1. **Préparation — Ingénieur**
   - complète le projet ;
   - résout les erreurs bloquantes ;
   - génère un aperçu ;
   - soumet le dossier à la validation technique.

2. **Validation technique — Responsable technique**
   - consulte le dossier et les contrôles ;
   - approuve l'étape technique, ou renvoie pour correction ;
   - enregistre la décision, la date et le commentaire éventuel.

3. **Validation finale — Validateur final**
   - consulte la version approuvée techniquement ;
   - valide définitivement, ou renvoie pour correction ;
   - enregistre la décision, la date et le commentaire éventuel.

Règles :
- aucune étape ne peut être sautée ;
- un dossier retourné revient à l'ingénieur pour correction ;
- toute modification après soumission invalide les approbations précédentes de cette version ;
- chaque soumission et décision est historisée ;
- la validation porte sur une version précise du dossier ;
- la version publiée ne doit pas changer après validation ;
- les corrections ultérieures créent une nouvelle version de travail soumise à nouveau au workflow.

Les trois étapes sont des responsabilités distinctes. Si une même personne possède plusieurs permissions, empêcher qu'elle approuve deux étapes consécutives sur le même dossier, sauf décision explicite de l'organisation. Ne pas inventer une signature électronique réglementaire ; la validation applicative enregistrée n'est pas présentée comme une signature qualifiée.

---

## 7. Modèle de données initial

Créer des migrations PostgreSQL versionnées. Les noms ci-dessous sont indicatifs mais les relations et l'intégrité sont obligatoires.

Entités minimales :
- `users`
- `roles`
- `user_roles` si nécessaire pour la mise en œuvre des permissions définies
- `projects`
- `sites`
- `locations` si utile pour salles/baies
- `equipment`
- `interfaces`
- `connections`
- `network_segments`
- `routes` lorsque documentées
- `configurations`
- `configuration_files`
- `import_jobs`
- `import_findings`
- `diagrams`
- `test_results`
- `ai_generations` pour l'historique des générations IA, sans secrets
- `document_versions`
- `approval_steps` ou structure équivalente
- `audit_logs`

Exigences de données :
- clés primaires stables ;
- clés étrangères ;
- index pour les recherches courantes ;
- contraintes de validation adaptées ;
- dates en UTC côté stockage et présentation locale côté interface ;
- transactions pour les imports ;
- suppression contrôlée des données référencées ;
- distinction entre valeurs nulles, valeurs inconnues et valeurs réellement vides ;
- conservation des versions approuvées ;
- liens explicites entre projet, équipement, fichier source et document généré ;
- pour chaque génération IA : projet, utilisateur, date, modèle/version, version du prompt, références aux données de contexte, contenu de sortie, avertissements et statut de revue ;
- aucune valeur secrète dans les entrées ou sorties persistées de l'historique IA.

Les données structurées sont la source de vérité. Les fichiers et documents générés sont des artefacts liés à cette source, avec provenance et version.

---

## 8. Sécurité et confidentialité

Exigences minimales :
- authentification requise ;
- mots de passe stockés avec un mécanisme de hachage moderne ;
- autorisation côté backend pour chaque opération sensible ;
- protection contre CSRF si applicable, XSS, injections SQL et accès non autorisés ;
- validation stricte des entrées ;
- limitation et contrôle des fichiers importés ;
- noms de fichiers générés par le serveur, sans utiliser directement les chemins fournis par l'utilisateur ;
- secrets exclus des logs ;
- masquage des mots de passe, clés privées, jetons, chaînes de connexion et secrets API dans les vues et exports standards ;
- sauvegarde protégée de la base et des fichiers ;
- configuration par variables d'environnement ;
- absence de secrets réels dans Git ;
- journal d'audit pour les changements, imports, générations et validations.

L'application est prévue pour un réseau interne, mais cela ne dispense pas d'authentification, de contrôles d'accès ni de sécurisation du serveur.

Ne pas ajouter de connexion SSH active ou d'exécution de commandes sur les équipements dans le périmètre initial. L'import de configuration est une fonction de lecture et d'analyse de fichiers.

Pour l'IA : les appels doivent rester sur le réseau interne et viser uniquement le runtime local. Aucun envoi à une API externe. Traiter les fichiers importés et les sorties du modèle comme des données non fiables ; valider toute sortie avant de l'utiliser. Les commandes générées ne doivent jamais être exécutées par le backend ou le runtime IA.

---

## 9. API et conventions

Créer une API REST documentée avec OpenAPI via FastAPI.

Organiser les endpoints par domaine :
- authentification et utilisateurs ;
- projets et sites ;
- équipements, interfaces et connexions ;
- réseau et configurations ;
- imports et résultats d'analyse ;
- schémas ;
- contrôles de cohérence ;
- générations IA locales et historique des résultats ;
- générations documentaires ;
- workflow de validation ;
- audit.

Règles :
- modèles de requête et réponse explicites ;
- validation des données ;
- codes HTTP cohérents ;
- pagination des listes ;
- filtres et recherche sur les listes utiles ;
- gestion d'erreurs uniforme, sans divulguer de secrets ;
- vérification des permissions ;
- tests d'intégration des routes importantes.

Ne pas construire une API générique qui contourne les règles métier pour écrire arbitrairement dans toutes les tables.

---

## 10. Interface utilisateur

Créer une interface sobre, professionnelle, accessible et simple à prendre en main.

Navigation principale :
1. Tableau de bord
2. Projets
3. Inventaire
4. Imports
5. Configurations
6. Architecture
7. Génération documentaire
8. Validations
9. Administration

Écrans principaux :
- liste et fiche projet ;
- assistant de création de projet ;
- liste d'équipements avec recherche/filtres ;
- fiche équipement adaptée à la catégorie ;
- interfaces et connexions ;
- réseau et adressage ;
- import avec aperçu, mapping et comparaison ;
- vue des anomalies de cohérence ;
- prévisualisation des schémas ;
- prévisualisation du dossier ;
- historique des versions et décisions.

Exigences UI :
- états de chargement, erreurs et confirmations explicites ;
- formulaires avec validation côté client et serveur ;
- conservation des saisies en cas d'erreur lorsque possible ;
- aucune action destructive sans confirmation ;
- affichage visible des statuts de données et de validation ;
- pas de boutons factices ;
- pas de liens de navigation non fonctionnels ;
- pas de chiffres ou équipements fictifs en production.

---

## 11. Tests obligatoires

### Tests unitaires backend
- validation des projets, équipements et interfaces ;
- validation IP/CIDR/VLAN ;
- détection des doublons potentiels ;
- analyseurs de formats pris en charge ;
- masquage des secrets ;
- règles de cohérence ;
- génération de schémas ;
- règles de transition du workflow ;
- validation des réponses IA structurées ;
- masquage des secrets avant préparation du contexte IA ;
- détection des données manquantes et distinction hypothèse/fait ;
- tests des limites et erreurs du client Ollama.

### Tests d'intégration
- création d'un projet et de plusieurs sites ;
- ajout de différents types d'équipements ;
- import CSV/Excel ;
- import d'un fichier pris en charge avec aperçu et confirmation ;
- conflit d'import sans écrasement silencieux ;
- génération DOCX et PDF ;
- génération IA via le runtime local, avec modèle disponible ;
- comportement explicite lorsque le runtime ou le modèle est indisponible ;
- vérification qu'aucun appel IA externe ni aucune commande d'équipement n'est exécuté ;
- conservation de l'historique d'une génération IA sans secrets ;
- vérification des droits ;
- approbation technique puis validation finale ;
- retour pour correction ;
- modification après soumission ;
- conservation d'une version validée ;
- sauvegarde et restauration selon la procédure documentée.

### Tests frontend
- navigation principale ;
- formulaires ;
- changement FR/EN ;
- écrans d'import ;
- états d'erreur ;
- génération et téléchargement de documents ;
- écrans de validation.

Ne considère pas une suite de tests comme réussie si les tests n'ont pas réellement été exécutés. Documente les tests impossibles à exécuter et leur raison.

---

## 12. Déploiement et exploitation

Fournir au minimum :
- `compose.yaml` ;
- Dockerfiles frontend et backend ;
- `.env.example` ;
- migrations ;
- commandes de démarrage, arrêt et mise à jour ;
- initialisation sécurisée du premier administrateur ;
- procédure de sauvegarde PostgreSQL et du stockage documentaire ;
- procédure de restauration testable ;
- health checks ;
- logs utiles sans secrets ;
- documentation d'installation Linux ;
- procédure de mise à niveau de version ;
- service/runtime Ollama local dans Compose ou procédure documentée équivalente ;
- volume persistant pour les modèles locaux ;
- procédure de téléchargement contrôlé et de chargement du modèle ;
- procédure de vérification du runtime et du modèle après installation ;
- configuration de l'IA locale dans `.env.example`, sans secrets réels.

Les données doivent survivre à la recréation des conteneurs. Ne jamais utiliser un stockage éphémère pour les données métier ou les documents à conserver.

---

## 13. Structure de dépôt proposée

Adapter cette structure si le dépôt existant impose une organisation raisonnable.

```text
infra-doc-generator/
├── frontend/
│   ├── app/
│   ├── components/
│   ├── features/
│   ├── i18n/
│   ├── lib/
│   └── tests/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── imports/
│   │   ├── adapters/
│   │   ├── diagrams/
│   │   ├── documents/
│   │   ├── ai/
│   │   │   ├── client.py
│   │   │   ├── prompts/
│   │   │   ├── schemas.py
│   │   │   ├── validators.py
│   │   │   └── service.py
│   │   ├── workflow/
│   │   └── audit/
│   ├── migrations/
│   └── tests/
├── templates/
│   ├── docx/
│   ├── html/
│   └── translations/
├── storage/
│   └── .gitkeep
├── deployment/
├── docs/
├── scripts/
├── compose.yaml
├── .env.example
├── README.md
└── MASTER_PROMPT.md
```

Ne pas versionner les fichiers importés, les documents confidentiels, les mots de passe ou les données réelles des clients.

---

## 14. Plan de réalisation obligatoire

Développer dans l'ordre suivant. À la fin de chaque lot, lancer les tests appropriés, corriger les erreurs et mettre à jour la documentation.

### Lot 0 — Inspection et planification
- inspecter le dépôt ;
- relever les versions des outils ;
- identifier les éléments existants ;
- établir un plan et les risques ;
- confirmer les commandes de test et de lancement.

### Lot 1 — Socle applicatif
- initialiser ou adapter frontend/backend ;
- configurer PostgreSQL et migrations ;
- implémenter authentification, rôles et permissions ;
- ajouter l'internationalisation FR/EN ;
- créer le déploiement Docker Compose ;
- construire le layout et la navigation.

### Lot 2 — Projets et sites
- CRUD projets et sites ;
- statuts de projet ;
- validations ;
- tests API et interface.

### Lot 3 — Inventaire et modèle technique
- équipements ;
- interfaces ;
- connexions ;
- VLAN et sous-réseaux ;
- configurations structurées ;
- fiches adaptées aux familles d'équipements.

### Lot 4 — Imports et adaptateurs
- CSV/Excel ;
- mapping des colonnes ;
- aperçu et validation ;
- rapport d'import ;
- premier adaptateur de configuration choisi à partir de fichiers exemples disponibles ;
- gestion des erreurs et conflits.

Ne choisis pas arbitrairement une marque prioritaire si aucun exemple ni besoin n'est fourni. Documente ce qui est pris en charge et demande des fichiers d'exemple si nécessaire.

### Lot 5 — Contrôles de cohérence
- règles déterministes ;
- erreurs, avertissements et informations ;
- écran de résultats ;
- blocage de génération uniquement pour les erreurs définies comme bloquantes.

### Lot 6 — Schémas
- modèle de données de topologie ;
- génération SVG ;
- vues physiques et logiques ;
- légendes et références ;
- tests de cohérence entre schémas et inventaire.

### Lot 7 — IA locale et génération documentaire
- déployer et documenter le runtime local Ollama ;
- vérifier les ressources serveur avant de sélectionner le modèle ;
- configurer le modèle et le health check ;
- implémenter le service IA FastAPI, les prompts versionnés et les sorties structurées ;
- implémenter les contrôles de sortie, le masquage des secrets et l'historique des générations ;
- générer des architectures, configurations, étapes détaillées, commandes et tests proposés ;
- s'assurer qu'aucune commande n'est exécutée et qu'aucun équipement n'est contacté ;
- modèles DOCX FR/EN ;
- PDF FR/EN ;
- HLD ;
- LLD ;
- annexes de configuration ;
- dossier de mise en service ;
- versionnement et conservation des artefacts.

### Lot 8 — Workflow de validation
- soumission par l'ingénieur ;
- revue technique ;
- validation finale ;
- retour pour correction ;
- historique des décisions ;
- verrouillage logique des versions approuvées.

### Lot 9 — Stabilisation
- tests fonctionnels et de sécurité ;
- contrôle des droits ;
- test de sauvegarde/restauration ;
- correction des défauts ;
- documentation de déploiement ;
- vérification complète des critères de réception.

---

## 15. Critères de réception

Le produit n'est accepté que si les points suivants fonctionnent réellement :

1. L'application est déployable sur un serveur Linux local avec Docker Compose.
2. Les utilisateurs peuvent se connecter et leurs permissions sont appliquées côté serveur.
3. L'interface est disponible en français et en anglais.
4. Un projet peut contenir plusieurs sites et équipements.
5. Plusieurs familles d'infrastructure peuvent être documentées.
6. L'inventaire peut être saisi et importé depuis CSV/Excel.
7. Un format de configuration pris en charge peut être analysé avec aperçu avant import.
8. Les conflits ne sont jamais écrasés silencieusement.
9. Les sources et états de vérification sont conservés.
10. Les contrôles de cohérence identifient les erreurs prévues par les règles implémentées.
11. Les schémas reflètent uniquement les données documentées.
12. HLD, LLD, annexes et dossier de mise en service sont générables.
13. PDF et DOCX sont produits et peuvent être ouverts.
14. Les documents sont bilingues sans traduire les valeurs techniques.
15. Le workflow complet ingénieur → responsable technique → validateur final fonctionne.
16. Les retours pour correction et les versions sont historisés.
17. Les secrets sont masqués dans les exports standards.
18. Les données et fichiers persistent après redémarrage des conteneurs.
19. La sauvegarde et la restauration sont documentées et testées.
20. Les tests pertinents passent, et les limitations restantes sont explicitement documentées.
21. Le runtime IA local fonctionne sur le serveur interne sans dépendance à une API externe.
22. Le modèle réellement configuré et ses exigences matérielles sont documentés et testés.
23. L'IA peut produire une proposition d'architecture, des configurations, des étapes, des commandes et des tests à partir du contexte du projet.
24. Les informations manquantes, hypothèses, risques et avertissements sont clairement affichés.
25. Les sorties IA passent par les validations déterministes et sont étiquetées comme propositions tant qu'elles ne sont pas vérifiées par un utilisateur.
26. Les secrets sont masqués avant l'appel IA et absents de l'historique et des logs.
27. Aucun appel à une API IA externe, aucune connexion directe aux équipements et aucune exécution des commandes générées ne sont possibles dans le périmètre livré.
28. L'indisponibilité du runtime ou du modèle produit un message explicite et n'empêche pas l'utilisation des fonctions non IA de l'application.

---

## 16. Livrables attendus du développement

Le dépôt final doit inclure :
- code source frontend et backend ;
- migrations de base de données ;
- tests automatisés ;
- adaptateurs réellement implémentés et leur documentation ;
- modèles documentaires français et anglais ;
- exemples de données de démonstration clairement identifiés comme fictifs, si nécessaires aux tests ;
- Docker Compose et Dockerfiles ;
- `.env.example` sans secret ;
- documentation d'installation et d'exploitation ;
- procédure de sauvegarde/restauration ;
- README avec commandes exactes ;
- liste des fonctionnalités réalisées, limitations et tests exécutés.

### Format du compte rendu après chaque lot

À la fin de chaque lot, fournir :
1. fonctionnalités implémentées ;
2. principaux fichiers créés ou modifiés ;
3. migrations effectuées ;
4. tests exécutés et résultats réels ;
5. instructions pour lancer et vérifier ;
6. limitations connues ;
7. prochaine étape.

Ne marque pas un lot comme terminé si ses critères ne sont pas remplis.

---

## 17. Instruction finale à l'agent de développement

Commence par inspecter le dépôt et établir un plan d'implémentation. Ensuite, construis l'application par lots dans l'ordre indiqué.

Priorise une application réellement fonctionnelle, sécurisée, testable et simple à maintenir. Les données structurées du projet doivent être la source de vérité des documents générés. Tous les contenus techniques doivent être traçables et toute information inconnue doit être signalée, jamais inventée.

**N'ajoute pas de fonctions non demandées. Ne simule pas une intégration matérielle qui n'existe pas. Ne génère pas une configuration comme si elle avait été appliquée à un équipement sans preuve. Ne déclare pas de tests réussis sans les avoir exécutés. L'IA doit rester locale, proposer des configurations et des procédures, et ne jamais exécuter les commandes ni appliquer une configuration aux équipements.**
