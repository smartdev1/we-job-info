---
id: T-001
title: Project skeleton and folder structure
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: S
---

## Context
Initialize monorepo layout per ADR 0001. Already created via nuxi and uv.

## Acceptance criteria
- [ ] api/app modules created (core, sources, ingestion, extraction, offers, rendering, copywriting, publishing, api, jobs)
- [ ] web pages/components/composables/stores/api-client dirs present
- [ ] .env.example committed with all required vars
- [ ] README documents local setup

## Technical notes
No application code yet.

## Implementation log
- Created app modules with __init__.py: core, sources, ingestion, extraction, offers, rendering, copywriting, publishing, api, jobs.
- Added pydantic-settings config (app/core/config.py) and FastAPI app with /healthz and auth skeleton router.
- Added Alembic scaffolding (alembic.ini, migrations/env.py, script.py.mako). Schema deferred to T-002.
- Added .env.example (pre-existing) and README local setup.
- Web: ssr:false in nuxt.config.ts; pages login/dashboard/offers; api-client placeholder dir.
- Dependencies (fastapi, pydantic-settings, uvicorn, alembic, sqlalchemy) still need to be added to pyproject.toml — permission required.

## Review
Verdict: APPROUVÉ

### Bloquant
- Aucun.

### Important
- Aucun.

### Mineur / suggestion
- Le log indique que les dépendances "still need to be added", mais elles sont déjà présentes dans api/pyproject.toml (fastapi, pydantic-settings, uvicorn, alembic, sqlalchemy). Mettre à jour le log pour éviter la confusion. Non bloquant.

### Points positifs
- Structure des modules conforme à ADR 0001 et à la convention du projet.
- Type hints présents, config typée via pydantic-settings, pas de logique métier dans les routes.

Prochaine action : passer à fullstack-qa pour la recette (statut qa).
## QA report
### Avis de recette — T-001
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ

### Critères d'acceptation
- [x] api/app modules created (core, sources, ingestion, extraction, offers, rendering, copywriting, publishing, api, jobs) — verified: all present with __init__.py under app/.
- [x] web pages/components/composables/stores/api-client dirs present — verified: app/pages (login, dashboard, offers), app/components, app/composables, app/stores, app/api-client.
- [x] .env.example committed with all required vars — verified: all vars present.
- [x] README documents local setup — verified: api/README.md and web/README.md exist.

### Tests exécutés
- Automatisés : none (no test suite for skeleton).
- Manuels : launched uvicorn app.api.main:app on 127.0.0.1:8001; GET /healthz returned 200 {"status":"ok","env":"development"}. Confirmed ssr:false in web/nuxt.config.ts.

### Bugs
- none.

### Zones non couvertes / risques résiduels
- Implementation log mentions dependencies "still need to be added" but they are already in pyproject.toml (minor, noted in review). Non-blocking.

### Non-régression
- Zones vérifiées : n/a (skeleton).

Prochaine action : soumettre à l'utilisateur la validation de passage en done (status done).
