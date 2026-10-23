---
id: T-004
title: Render deployment and GitHub Actions CI
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
Configure Render Web Service (API) + Background Worker, Neon DB, CI pipeline.

## Acceptance criteria
- [ ] render.yaml or service config documented
- [ ] GitHub Actions: ruff, mypy, pytest, eslint, typecheck
- [ ] Auto-deploy on main with Alembic migration step
- [ ] /healthz endpoint returns OK

## Technical notes
No Docker. Migrations run before deploy.

## Implementation log

- `/healthz` already present in `app/api/main.py` returning `{"status":"ok","env":...}`.
- `render.yaml` (repo root): Web Service `we-info-jobs-api` + Background Worker `we-info-jobs-worker`, Python runtime, uv build, Alembic migration in build step, env vars documented (secrets via `sync: false` / generated).
- `.github/workflows/api-ci.yml`: ruff lint+format, mypy, pytest (with test env), deploy trigger on main via Render deploy hook secret.
- No Docker, no code-heavy changes. Deployment not executed (preparation only).
## Review

### Verdict : APPROUVÉ

### Bloquant
- (aucun) — les deux points bloquants de la revue précédente sont résolus : le service worker inexistant a été retiré de `render.yaml` (commentaire référençant V2+/T-020+), et la stratégie DB CI est confirmée (SQLite local `sqlite+aiosqlite:///tmp/ci.db`, aucun Postgres externe).

### Important
- `.github/workflows/api-ci.yml` — l'AC mentionne eslint/typecheck ; ces étapes vivent dans `web/.github/workflows/ci.yml`. Acceptable pour un workflow api-only, mais réconcilier le libellé de l'AC ou référencer le workflow web dans les notes de tâche.
- `render.yaml` — le build exécute `alembic upgrade head` contre Neon au build time. Si la migration échoue, le déploiement avorte (comportement souhaité), mais aucune note de rollback n'est documentée. Ajouter une note dans un runbook (`docs/runbooks/`).

### Mineur / suggestion
- `render.yaml:1` — Render peut auto-déployer sur push vers `main` en plus du hook GitHub Actions, provoquant des déploiements doubles. Désactiver l'auto-deploy dans le dashboard Render ou documenter le déclencheur choisi.
- L'intégration `alembic upgrade head` au build suppose que `DATABASE_URL` est défini au build time sur Render ; vérifier que la variable est bien disponible au build (elle l'est via envVars, OK).

### Points positifs (max 2)
- Secrets correctement marqués `sync: false` / `generateValue: true` ; aucun secret en dur dans `render.yaml` ni dans le workflow.
- `/healthz` présent dans `app/api/main.py` et référencé comme `healthCheckPath`.

Prochaine action : passage en QA (statut `qa`) pour validation de la config Render/CI par un agent qui n'a pas écrit le code.

### Review follow-up (fullstack-devops)
- Removed the `we-info-jobs-worker` service from `render.yaml`: `app/jobs/worker` does not exist yet (V0). Worker will be re-added in V2+ (T-020+) with a comment documenting it.
- CI DB strategy confirmed: `.github/workflows/api-ci.yml` now uses a local SQLite database (`sqlite+aiosqlite:///tmp/ci.db`); no connection to Neon or any external Postgres. DB-touching integration tests are skipped in CI unless a Postgres service container is provided. Documented inline.

## QA report

### Avis de recette — T-004
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ

### Critères d'acceptation
- [x] render.yaml or service config documented — `render.yaml` at repo root, valid YAML (parsed with PyYAML); web service `we-info-jobs-api`, python runtime, uv build, healthCheckPath /healthz.
- [x] GitHub Actions: ruff, mypy, pytest, eslint, typecheck — `api-ci.yml` runs ruff (lint+format), mypy, pytest (SQLite local); eslint + typecheck live in `web/.github/workflows/ci.yml` (pnpm lint/typecheck). AC wording covers both scopes.
- [x] Auto-deploy on main with Alembic migration step — buildCommand `uv sync --frozen && uv run alembic upgrade head`; deploy job triggers Render hook on push to main.
- [x] /healthz endpoint returns OK — `app/api/main.py` returns `{"status":"ok","env":...}`; referenced as healthCheckPath.

### Tests exécutés
- Automatisés : YAML syntax validated (render.yaml + api-ci.yml) — 2/2 pass.
- Manuels : secret audit (no hardcoded secrets), envVar sync:false check.

### Bugs
- (aucun bloquant)

### Zones non couvertes / risques résiduels
- Double deploy risk: Render auto-deploy on push could duplicate GitHub Actions hook trigger (review note).
- No rollback note for failed Alembic migration at build time (review note).
- Worker service intentionally omitted (V2+).

### Non-régression
- Zones vérifiées : /healthz route, CI env (SQLite local, no external Postgres).

Prochaine action : passage en done sous validation utilisateur.
