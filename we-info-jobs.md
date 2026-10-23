Architecture et stack technique : Bot d'offres d'emploi vers chaîne WhatsApp
Document de référence de l'architecte logiciel. Version 1.0.
1. Contexte, faits et hypothèses
Faits (issus de la discussion)
• Utilisateur unique (le propriétaire de la chaîne), avec validation humaine avant publication.
• Deux entrées : collecte automatique sur plusieurs sites, et ajout manuel par URL, texte ou capture d'écran.
• Sorties : un visuel généré à partir d'un template, un texte adapté au style de la chaîne, puis publication sur une chaîne WhatsApp.
• Compétences : Vue.js (Nuxt) et Python niveau avancé. Choix retenu : Nuxt (front) + FastAPI (back).
Hypothèses (à confirmer)
• Volume faible : quelques dizaines d'offres par jour, une à quelques publications par jour.
• Budget serré, développeur solo.
• Cible principale : Côte d'Ivoire / Afrique francophone.
• Hypothèse critique non vérifiée : l'API officielle WhatsApp Business ne permet pas de publier automatiquement sur une Chaîne. À vérifier avant la V4. L'architecture est conçue pour que cette inconnue n'ait aucun impact sur le reste.
Conséquence architecturale : c'est un outil interne, pas une plateforme. Monolithe modulaire, un seul dépôt, un seul serveur. Pas de microservices, pas de Kubernetes, pas d'architecture événementielle lourde.
2. Principes directeurs
1. Simplicité d'abord : le moins de composants possible (Postgres sert aussi de file de jobs).
2. Les parties volatiles (sources, fournisseur LLM, canal de publication) sont isolées derrière des interfaces.
3. Un seul moteur d'extraction pour toutes les entrées (bot, URL, texte, image).
4. L'humain décide, la machine prépare : aucune publication sans validation en V1 à V3.
5. Toute donnée externe (page web, sortie du LLM) est traitée comme non fiable et validée.
6. Les décisions coûteuses à changer (modèle de données, contrats, hébergement) sont soignées ; les autres se décident vite.
3. Vue d'ensemble
 Sources (RSS, sites, alertes mail)      URL / texte / capture (manuel)
              |                                   |
              +----------> INGESTION <------------+
                              | contenu brut
                       EXTRACTION (LLM -> JSON validé Pydantic)
                              |
                NORMALISATION + DÉDOUBLONNAGE + SUSPICION + SCORE
                              |
                      POSTGRESQL (offres, statuts)
                              |
                   DASHBOARD NUXT (validation, édition)
                              | action : Générer
               +--------------+---------------+
        RENDU VISUEL (HTML->PNG)       RÉDACTION TEXTE (LLM)
               +--------------+---------------+
                              |
                PUBLICATION (interface + adaptateurs)
           export manuel | Telegram | futur automatique
Déploiement : Render (services web + worker), base de données sur Neon (PostgreSQL managé). L'API et le worker partagent le même code. Pas de Docker.
4. Stack technologique complète
Couche
Choix
Rôle
Alternative écartée et raison
Front
Nuxt 3 (Vue 3, TypeScript), mode SPA (ssr: false)
Dashboard
Next.js : tu maîtrises Vue
UI
Nuxt UI (ou PrimeVue) + Tailwind CSS
Tables, filtres, modales, formulaires
Composants faits main : perte de temps
État front
Pinia + TanStack Query (Vue)
État local, cache serveur, polling
Vuex : obsolète
Client API
openapi-typescript + openapi-fetch
Client typé généré depuis FastAPI
Client écrit à la main : dérive du contrat
API
FastAPI + Uvicorn
Routes REST, OpenAPI auto
Django : trop lourd pour ce besoin
Validation
Pydantic v2 + pydantic-settings
Schémas, config
Marshmallow : redondant
Base de données
Neon (PostgreSQL managé, serverless)
Données, file de jobs, recherche floue
PostgreSQL local / Docker : remplacé par Neon (décision : pas de conteneurisation)
ORM
SQLAlchemy 2.x (async) + Alembic
Accès et migrations
SQLModel : acceptable, moins mûr
Jobs
Procrastinate (file dans Postgres)
Tâches de fond, planification
Celery + Redis : un composant de plus
HTTP client
httpx
Requêtes sortantes
requests : pas d'async
Scraping dynamique
Playwright (Python)
Pages JavaScript, rendu d'images
Selenium : plus lent, moins fiable
Parsing HTML
selectolax ou BeautifulSoup + lxml, trafilatura
Extraction du contenu principal
Regex : fragile
RSS
feedparser
Flux RSS/Atom

Email (alertes)
IMAP via imap-tools
Lecture de boîte dédiée

LLM
SDK Python Anthropic
Extraction et rédaction
Cf. section 8
Templates
Jinja2
Rendu HTML des visuels

Similarité
pg_trgm (extension Postgres) + rapidfuzz
Dédoublonnage flou
Moteur de recherche dédié : inutile
Images
Pillow (post-traitement)
Redimensionnement, optimisation

Logs
structlog
Logs JSON structurés

Erreurs
Sentry (offre gratuite) ou GlitchTip auto-hébergé
Alertes d'exceptions

Tests back
pytest, pytest-asyncio, respx, testcontainers
Unitaires et intégration

Tests front
Vitest + Playwright Test (quelques parcours)


Qualité
ruff, mypy, pre-commit, ESLint, Prettier
Formatage, lint, typage

Gestion Python
uv
Dépendances et environnements
pip seul : non reproductible
Reverse proxy
Caddy
HTTPS auto, routage
Nginx : config plus lourde
Conteneurs
Docker + Docker Compose
Packaging

CI/CD
GitHub Actions
Tests, build, déploiement

Hébergement
Render (services web + worker)
VPS 2 vCPU / 4 Go RAM minimum (Hetzner, OVH, ou équivalent)

Serverless : incompatible avec navigateur headless
Sauvegardes
pg_dump quotidien chiffré vers un stockage objet (Cloudflare R2, Backblaze B2)


Note : les versions exactes sont figées dans les fichiers de verrouillage (uv.lock, package-lock). Choisir des versions stables, publiées depuis plus de deux semaines.
Écarté volontairement : microservices, Kafka, Redis, Kubernetes, base NoSQL dédiée, framework d'agents autonomes, WebSocket (polling suffisant), SSR Nuxt.
5. Structure du monorepo
/web                          Nuxt 3 SPA
  /pages  /components  /composables  /stores  /api-client (généré)
/api
  /app
    /core                     config, db, sécurité, logging, client LLM
    /sources                  connecteurs + registre
    /ingestion                fetch, garde SSRF, nettoyage HTML
    /extraction               prompts, schémas Pydantic, validation
    /offers                   modèles, dédoublonnage, scoring, machine à états
    /rendering                templates Jinja2, rendu PNG
    /copywriting              guide de style, variantes
    /publishing               interface Publisher + adaptateurs
    /api                      routes FastAPI (fines)
    /jobs                     tâches Procrastinate
  /migrations                 Alembic
  /tests                      unit, integration, fixtures d'offres réelles
/deploy                       docker-compose.yml, Caddyfile, scripts
/docs                         ADR (décisions d'architecture), runbook
Règles de dépendance
• Les routes et les jobs appellent les modules, jamais l'inverse.
• sources ignore extraction ; publishing ignore sources.
• Les routes sont fines : validation, appel d'un service, réponse. Aucune logique métier.
• Nuxt ne contient aucune logique métier ni route serveur (Nitro désactivé en production).
6. Modèle de données (PostgreSQL)
Conventions : clés primaires UUID, colonnes created_at et updated_at partout, horodatages en UTC (timestamptz), jamais de suppression physique des offres.
sources : id, nom, type (rss, html, email, manuel), config (JSONB), actif, derniere_reussite_at, echecs_consecutifs, derniere_erreur.
raw_documents : id, source_id (nullable pour le manuel), url, type_contenu (html, texte, image), contenu (texte) ou chemin_fichier (image), hash_contenu (unique), recupere_at.
offers
• Identité : id, titre, entreprise, lieu, ville, pays.
• Détail : type_contrat, niveau_etudes, experience, secteur, description, missions (tableau), profil (tableau), avantages, comment_postuler, email_contact, lien_candidature, date_limite.
• Traçabilité : url_origine, source_id, raw_document_id, fingerprint (indexé), extraction_modele, confiance (JSONB, par champ).
• Gestion : statut, score, suspecte (booléen), motifs_suspicion (tableau), doublon_de (id nullable), note_interne.
templates : id, nom, version, format (carre_1080, portrait_1080x1350), html (Jinja2), css, polices (liste), actif.
style_guides : id, nom, contenu (texte libre : ton, emojis, structure, hashtags), exemples (JSONB, messages réels que tu aimes), actif.
generated_assets : id, offer_id, template_id, style_guide_id, chemin_image, texte, variante (entier), modele_llm, tokens_entree, tokens_sortie.
publications : id, offer_id, asset_id, canal (export_manuel, telegram, ...), publie_at, statut.
jobs_log (facultatif) : dérivé de la table de Procrastinate pour l'affichage dans le dashboard.
users : id, email, mot_de_passe_hash (argon2), dernier_login. Une seule ligne attendue.
Index importants : fingerprint, statut + created_at, url_origine, hash_contenu (unique), index GIN trigramme sur titre et entreprise normalisés.
Fingerprint : hash de (entreprise + titre + ville), normalisés (minuscules, sans accents, sans ponctuation, sans mots parasites comme « h/f », « urgent », « recrute »). Les quasi-doublons sont détectés par similarité trigramme et signalés dans le dashboard, jamais supprimés silencieusement.
7. Modules backend et contrats
7.1 Sources (connecteurs)
Interface commune, quelle que soit la technique :
• lister() : renvoie les offres récentes (url, titre approximatif, date).
• recuperer(url) : renvoie le contenu brut (HTML, texte ou image).
• sante() : indique si la source répond normalement.
Règles :
• Un connecteur ne structure jamais l'offre ; il fournit du brut.
• Un échec est une donnée (compteur, dernière erreur), pas une exception avalée.
• Cadence, respect de robots.txt, User-Agent honnête et timeouts sont gérés par le noyau, pas par chaque connecteur.
• Ajouter une source = ajouter un fichier + une ligne dans le registre.
Ordre de préférence des techniques : RSS ou API officielle, puis alertes email, puis scraping HTTP simple, puis scraping Playwright. Vérifier les CGU de chaque site avant d'en faire une source régulière.
Sources candidates à évaluer (à confirmer par le propriétaire) : Emploi.ci, Educarriere, Novojob, pages carrières d'entreprises, alertes email de portails, pages LinkedIn publiques si les CGU le permettent. Commencer par 3 à 5 sources maximum.
7.2 Ingestion
• Récupération (httpx, Playwright si nécessaire), garde SSRF (section 12), limite de taille et de redirections.
• Nettoyage HTML : suppression des scripts, menus, pieds de page ; extraction du contenu principal avec trafilatura.
• Stockage du brut + hash de contenu. Si le hash existe déjà, on s'arrête (pas de nouvel appel LLM).
7.3 Extraction
Voir section 9.
7.4 Offers
• Normalisation (casse, villes connues, types de contrat standardisés : CDI, CDD, stage, alternance, freelance, intérim).
• Fingerprint et détection de doublons.
• Drapeaux de suspicion (règles simples, section 12).
• Score (V3) : fraîcheur, complétude, présence d'une date limite et d'un contact, secteur et ville prioritaires.
• Machine à états centralisée : un seul endroit du code autorise les transitions.
7.5 Rendering et copywriting
Voir sections 10 et 11.
7.6 Publishing
Interface Publisher avec une méthode publier(asset) et une méthode statut(publication). Adaptateurs : export manuel (V1), Telegram (V3/V4), automatique si une voie officielle existe (V4).
8. API (FastAPI)
Préfixe /api/v1. Authentification par cookie de session HttpOnly + SameSite=Strict.
Domaine
Endpoints
Auth
POST /auth/login, POST /auth/logout, GET /auth/me
Ajout manuel
POST /offers/from-url, POST /offers/from-text, POST /offers/from-image (créent un job, renvoient un job_id)
Jobs
GET /jobs/{id} (état : en attente, en cours, terminé, échoué)
Offres
GET /offers (filtres : statut, source, ville, contrat, secteur, date, suspecte ; tri ; pagination par curseur), GET /offers/{id}, PATCH /offers/{id}, POST /offers/{id}/status
Doublons
GET /offers/{id}/duplicates, POST /offers/{id}/merge
Génération
POST /offers/{id}/generate (template, style, nombre de variantes), GET /offers/{id}/assets
Publication
POST /assets/{id}/publish, GET /publications
Configuration
CRUD /templates, /style-guides, /sources
Santé
GET /sources/health, GET /healthz
Conventions
• Erreurs au format uniforme (code, message, détails). Codes HTTP corrects.
• Opérations longues : asynchrones via jobs, polling côté front (toutes les 2 s, backoff progressif). SSE seulement si un besoin réel apparaît.
• Idempotence : from-url sur une URL déjà connue renvoie l'offre existante.
• Versionnement par préfixe d'URL. Spécification OpenAPI générée et utilisée pour le client typé du front.
9. Extraction IA
Entrée : contenu nettoyé (texte) ou image. Sortie : JSON conforme au schéma Pydantic OffreExtraite.
Méthode
1. Prompt système stable : rôle, règles, schéma attendu, consigne de ne jamais inventer (champ absent = null).
2. Contenu de la page placé dans une section clairement délimitée et déclarée comme données non fiables (défense contre l'injection de prompt).
3. Sortie validée par Pydantic. En cas d'échec : un retry avec le message d'erreur, puis statut a_revoir.
4. Confiance par champ (haute, moyenne, basse) stockée en base et affichée dans le dashboard.
5. Classification préalable : la page est-elle réellement une offre d'emploi ? (évite de traiter des pages d'erreur ou de listing)
Contrôle des coûts
• Cache par hash de contenu.
• Pré-filtres sans LLM : page vide, URL déjà vue, contenu trop court.
• Modèle économique pour l'extraction ; modèle plus puissant seulement pour la rédaction si la qualité l'exige.
• Plafond mensuel configurable et compteur de tokens dans le dashboard.
Abstraction : un module core/llm expose extraire(contenu) et rediger(offre, style). Le fournisseur et le modèle sont configurables par variable d'environnement. Vérifier les identifiants de modèles et les tarifs actuels dans la documentation officielle au moment de l'implémentation.
Tests de non-régression : un jeu de 30 à 50 offres réelles (avec le résultat attendu validé à la main) est rejoué à chaque modification de prompt. Toute offre qui a posé problème en production y est ajoutée.
Critère de succès V1 : au moins 90 % des champs clés (titre, entreprise, lieu, contrat, date limite, comment postuler) corrects sur le jeu de test, avant de continuer vers la collecte automatique.
10. Rendu visuel
Pipeline : offre + template Jinja2 + données de marque → HTML → Playwright (screenshot) → PNG → optimisation Pillow.
Formats : portrait 1080×1350 (recommandé, plus de place à l'écran mobile) et carré 1080×1080.
Zones du template (à valider avec le propriétaire) : logo de la chaîne, bandeau « Offre d'emploi », titre du poste, entreprise, lieu, type de contrat, date limite, pied de page (nom de la chaîne, appel à suivre).
Règles de robustesse
• Titres longs : taille de police adaptative avec plancher, puis troncature propre avec points de suspension.
• Logo d'entreprise absent : repli sur initiales dans une pastille colorée (couleur déterministe selon le nom).
• Polices embarquées dans le template (fichiers woff2 locaux), jamais chargées depuis Internet.
• Contraste vérifié pour la lisibilité sur mobile.
• Rendu déterministe : même entrée, même image.
• Un seul navigateur Playwright réutilisé par le worker (pool limité) pour éviter la surconsommation mémoire.
Prévisualisation dans le dashboard avant génération finale, avec régénération en un clic et choix du template.
Versionnement : les templates sont stockés en base avec une version ; une image générée référence la version utilisée.
11. Rédaction du texte
• Le guide de style de la chaîne (ton, longueur, emojis, structure, hashtags, formules d'accroche et de clôture) est stocké en base, éditable depuis le dashboard, avec 3 à 5 exemples réels de messages que tu aimes (apprentissage par l'exemple).
• Génération de 2 à 3 variantes par offre ; régénération possible ; édition manuelle avant copie.
• Format WhatsApp respecté : gras *texte*, italique _texte_, listes simples, longueur raisonnable.
• Attribution obligatoire : le lien vers la source ou l'offre originale est toujours présent.
• Formats prévus : offre complète, version courte, récapitulatif hebdomadaire (V3).
• Le texte ne doit contenir que des informations présentes dans l'offre : aucune invention de salaire, de contact ou de date.
12. Publication
Fait à vérifier : à ma connaissance, l'API officielle WhatsApp Business ne permet pas de publier sur une Chaîne. À revérifier avant la V4.
Stratégie : interface Publisher à adaptateurs interchangeables.
• V1 : export manuel. Écran pensé pour mobile : prévisualisation de l'image, bouton Télécharger, bouton Copier le texte, bouton Marquer comme publié. Environ 10 secondes par offre.
• V3/V4 : adaptateur Telegram : un bot t'envoie l'image et le texte sur ton téléphone, prêts à être transférés vers WhatsApp.
• Futur : adaptateur automatique uniquement s'il existe une voie officielle. L'automatisation via WhatsApp Web non officielle est écartée (violation des conditions d'utilisation, risque de blocage du numéro).
Chaque publication est enregistrée (historique anti-republication, statistiques).
13. Frontend (Nuxt)
Mode : SPA statique (ssr: false), générée en fichiers servis par Caddy. Aucun runtime Node en production.
Pages
• /login
• / : tableau de bord (compteurs : nouvelles, à revoir, prêtes, publiées ; santé des sources ; coût LLM du mois)
• /offers : liste avec filtres, recherche, tri, actions groupées (rejeter, sélectionner)
• /offers/[id] : fiche éditable, indicateurs de confiance, drapeaux de suspicion, doublons, lien source, bouton Générer
• /offers/new : ajout par URL, texte collé ou capture (glisser-déposer)
• /generate/[offerId] : choix du template et du style, prévisualisation, variantes de texte, export
• /publications : historique
• /settings/templates, /settings/style, /settings/sources
Principes
• Client API généré, jamais d'appel fetch écrit à la main.
• TanStack Query pour le cache et le polling des jobs.
• Responsive : l'écran d'export est conçu mobile d'abord.
• Accessibilité de base (navigation clavier, contrastes, libellés).
• Raccourcis clavier pour la file de validation (sélectionner, rejeter, suivant).
14. Pipeline de jobs et cycle de vie
Jobs (tous idempotents et relançables)
1. collect_source(source_id) : planifié par source (toutes les 1 à 3 heures).
2. fetch(url) : récupération, hash, arrêt si déjà vu.
3. extract(raw_document_id) : appel LLM, validation.
4. normalize(offer_id) : normalisation, fingerprint, doublons, suspicion, score.
5. render_and_write(offer_id, options) : image et variantes de texte (à la demande).
6. expire_offers : quotidien, passe en expirée les offres dont la date limite est dépassée.
7. check_sources_health : quotidien, alerte si une source n'a rien produit depuis N jours.
8. backup : quotidien.
Machine à états de l'offre
nouvelle -> sélectionnée -> publiée
   |            |
   |            +-> rejetée
   +-> rejetée
   +-> à_revoir (extraction douteuse) -> nouvelle (après correction)
   +-> expirée (tâche planifiée)
Politique d'erreurs : retries avec backoff exponentiel (3 tentatives max), puis échec visible dans le dashboard. Jamais d'échec silencieux.
15. Sécurité
• SSRF (from-url) : résoudre le DNS, refuser les adresses privées, loopback, lien-local et métadonnées cloud (par exemple 169.254.169.254) ; revalider après chaque redirection ; limiter le nombre de redirections, la taille de réponse et la durée ; schémas http et https uniquement ; exécuter Playwright sans accès au réseau interne.
• Injection de prompt : le LLM n'a accès à aucun outil dans ces flux ; sa sortie est une donnée validée par schéma, jamais une commande. Le contenu externe est délimité et déclaré non fiable.
• Authentification : mot de passe haché avec argon2, limitation de tentatives, cookie HttpOnly + Secure + SameSite=Strict, protection CSRF pour les requêtes modifiantes. Optionnel : 2FA TOTP.
• Un seul domaine via Caddy (/ pour le front, /api pour l'API) : pas de CORS.
• Secrets : variables d'environnement ou fichier .env hors dépôt ; rotation possible ; jamais dans les logs.
• Uploads (captures) : types MIME autorisés, taille maximale, renommage, aucun exécutable.
• Sortie HTML des templates : échappement automatique Jinja2 pour éviter l'injection dans le rendu.
• Dépendances : Dependabot ou équivalent, audit régulier.
• Système : accès SSH par clé uniquement, pare-feu (ports 80 et 443), mises à jour automatiques de sécurité, conteneurs non-root.
• Conformité : données personnelles limitées (contacts de recruteurs publiés dans les offres). Ne conserver que le nécessaire ; prévoir une purge des brutes après une durée définie.
Détection d'offres suspectes (arnaques)
Règles qui lèvent un drapeau, la décision restant humaine : demande de paiement ou de frais de dossier, adresse email gratuite pour une grande entreprise, promesses irréalistes de salaire, absence d'entreprise identifiable, contact uniquement via messagerie privée, pression temporelle excessive. Les motifs sont affichés dans le dashboard.
16. Fiabilité et observabilité
• Alerte par source : si un connecteur ne remonte rien pendant N jours ou échoue X fois de suite, notification (email ou Telegram). C'est la protection contre la panne silencieuse, risque n°2 du projet.
• Logs structurés JSON avec identifiant de corrélation (offre, job).
• Métriques minimales : offres collectées par source, taux d'extraction réussie, taux de validation, durée des jobs, coût LLM, erreurs. Affichées dans le dashboard ; pas de Prometheus/Grafana en V1.
• Healthchecks : /healthz (API, DB), surveillance externe gratuite (UptimeRobot ou équivalent).
• Sauvegardes : dump Postgres quotidien chiffré vers un stockage objet, rétention 14 à 30 jours ; test de restauration trimestriel. Les images générées sont reconstructibles ; seuls les templates, styles et offres sont critiques.
• Dégradation gracieuse : si le LLM est indisponible, l'ajout est mis en file et retenté ; si le rendu échoue, l'offre reste utilisable en texte seul.
17. Déploiement et infrastructure
Déploiement sur Render
• Pas de conteneurisation : services Render natifs (Web Service pour l'API, Background Worker pour Procrastinate).
• caddy : remplacé par le reverse proxy HTTPS de Render (pas nécessaire).
• api : Web Service Render, FastAPI (Uvicorn).
• worker : Background Worker Render, même code, lance Procrastinate ; inclut Playwright et ses navigateurs.
• postgres : remplacé par Neon (PostgreSQL managé). Connexion via `DATABASE_URL` (variable d'environnement Render).
Environnements : local (docker-compose de dev), production. Un environnement de staging n'est pas nécessaire pour un solo à ce stade.
CI/CD (GitHub Actions) : lint (ruff, mypy, ESLint), tests, build des images, génération du client OpenAPI et vérification qu'il est à jour, déploiement par SSH ou registre d'images, migrations Alembic automatiques avec sauvegarde préalable.
Dimensionnement : 2 vCPU et 4 Go de RAM suffisent (Playwright est le principal consommateur de mémoire). Limiter la concurrence du worker à 2 jobs de rendu ou de scraping simultanés.
Configuration : toutes les valeurs d'environnement documentées dans .env.example (URL base de données, clé LLM, modèles, clés Telegram, identifiants IMAP, domaine, secret de session).
Stockage des images : disque du VPS en V1 (volume Docker) ; migration vers stockage objet (R2/S3) si le volume le justifie.
18. Stratégie de tests
• Unitaires : normalisation, fingerprint, machine à états, règles de suspicion, garde SSRF (cas limites : IP décimale, IPv6, redirections vers l'interne, DNS rebinding).
• Intégration : API contre une vraie base (testcontainers), jobs de bout en bout avec LLM simulé.
• Connecteurs : tests sur pages HTML enregistrées (fixtures) ; un test « canari » périodique contre le vrai site, séparé de la CI.
• Extraction : jeu de non-régression sur offres réelles (section 9).
• Rendu : tests visuels par comparaison d'image sur quelques cas limites (titre très long, logo absent, caractères accentués).
• Front : tests des composants clés et 2 à 3 parcours de bout en bout (ajout par texte, génération, export).
19. Coûts estimés (à mesurer dès la V1)
Poste
Ordre de grandeur
VPS
environ 5 à 15 EUR par mois
Domaine
environ 10 à 15 EUR par an
Stockage de sauvegardes
quelques centimes à 1 EUR par mois
LLM
dépend du volume ; à quelques dizaines d'offres par jour, de l'ordre de quelques euros par mois avec un modèle économique et du cache
Sentry / uptime
offres gratuites suffisantes
Ces chiffres sont des estimations : mesurer la consommation réelle (tokens par offre) pendant la V1 et fixer un plafond mensuel.
20. Aspects légaux et éditoriaux
• Toujours citer la source et renvoyer vers l'offre originale.
• Vérifier les conditions d'utilisation de chaque site avant de l'utiliser comme source régulière ; privilégier RSS, API et alertes email.
• Respect de robots.txt, cadence raisonnable, User-Agent identifiable.
• Ne pas republier le contenu de pages protégées par connexion.
• Retirer rapidement une offre à la demande d'un recruteur.
• Définir la ligne éditoriale (public, zone géographique, niveaux) : elle conditionne le scoring et le tri.
• Prévoir un statut « sponsorisée » si une monétisation est envisagée, avec mention claire dans la publication.
21. Feuille de route
Étape
Contenu
Critère de sortie
V0 : fondations
Dépôt, initialisation via commandes officielles (nuxi pour Nuxt, uv pour Python), config Render, DB Neon, migrations, auth, CI
Déploiement fonctionnel avec login
V1 : boucle manuelle
Ajout texte puis URL puis capture, extraction, dashboard (liste, fiche, statuts), 1 template, texte en 2-3 variantes, écran d'export
90 % d'extraction correcte sur 30 offres ; utilisé en réel pendant une semaine
V2 : le bot
3 à 5 connecteurs, jobs planifiés, dédoublonnage, expiration, alertes par source
Une journée sans intervention produit une file d'offres exploitable
V3 : qualité éditoriale
Scoring, filtres avancés, suspicion, multi-templates, récapitulatif hebdomadaire, adaptateur Telegram
Temps de traitement par offre inférieur à 1 minute
V4 : publication et mesure
Publication automatisée si voie officielle, statistiques d'audience
Selon la faisabilité vérifiée
Ordre de construction de la V1 : squelette, extraction depuis texte (validation de qualité), puis URL (avec garde SSRF), puis image, dashboard, rendu, rédaction, export.
22. Registre des risques
#
Risque
Probabilité
Impact
Mitigation
1
Pas d'API de publication sur les Chaînes
Élevée
Moyen
Export manuel, interface Publisher, Telegram
2
Connecteurs qui cassent silencieusement
Élevée
Élevé
Alerte par source, préférence RSS/API/email, tests canari
3
Qualité d'extraction insuffisante
Moyenne
Élevé
Schéma strict, confiance par champ, jeu de test, humain dans la boucle
4
Blocage ou plainte d'un site source
Moyenne
Moyen
Respect CGU et robots.txt, attribution, retrait rapide
5
Publication d'une arnaque
Moyenne
Élevé
Règles de suspicion, validation humaine, réputation de la chaîne
6
Dérive de périmètre
Élevée
Moyen
Roadmap par étapes, critères de sortie, V2 conditionnée à l'usage réel de la V1
7
Coût LLM qui dérape
Faible
Moyen
Cache, pré-filtres, plafond mensuel
8
Perte de données
Faible
Élevé
Sauvegardes testées
9
Dérive entre front et back
Moyenne
Faible
Client OpenAPI généré, vérifié en CI
23. Décisions d'architecture (ADR résumés)
1. Monolithe modulaire, deux processus (api, worker) : un solo n'a aucun avantage à gérer du réseau entre services. Réversible : les modules ont des frontières nettes.
2. Nuxt SPA + FastAPI : tire parti de la maîtrise de Vue et Python. Coût accepté : deux langages et un contrat d'API, atténué par OpenAPI et un monorepo.
3. PostgreSQL comme base et file de jobs (Procrastinate) : un composant de moins que Redis + Celery. Limite : débit modeste, largement suffisant ici.
4. Playwright pour le scraping et le rendu : un seul outil de navigateur. Coût : mémoire ; limité par la concurrence du worker.
5. Interface Publisher : isole la plus grande inconnue du projet.
6. Polling plutôt que WebSocket : suffisant pour des tâches de quelques secondes.
7. Un seul domaine via Caddy : supprime CORS et simplifie l'authentification.
8. LLM derrière une abstraction : fournisseur et modèle remplaçables.
9. Pas de suppression physique des offres : évite de re-proposer des offres rejetées et conserve l'historique.
24. Points ouverts à trancher avec le propriétaire
1. Liste précise des 3 à 5 sources initiales et leur méthode d'accès (RSS, alerte email, scraping).
2. Charte graphique : couleurs, logo, polices, exemple de visuel apprécié.
3. Ligne éditoriale : public, zone géographique, niveaux d'expérience.
4. Exemples réels de messages de la chaîne pour construire le guide de style.
5. Canal de réception souhaité pour les alertes (email ou Telegram).
6. Budget mensuel maximal pour l'hébergement et le LLM.
7. Vérification de l'état actuel des possibilités de publication sur les Chaînes WhatsApp.