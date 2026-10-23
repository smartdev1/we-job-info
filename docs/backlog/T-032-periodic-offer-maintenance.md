---
id: T-032
title: Periodic offer maintenance job (2x/day)
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
The chain owner wants a background pass twice a day that: collects from all registered sources, expires offers whose deadline passed, and checks source health. Jobs already exist (`collect_source_task`, `expire_offers_task`, `check_sources_health_task`) but nothing schedules them. Procrastinate supports periodic tasks via `@app.periodic(cron=..., periodic_id=...)` + a worker run with `--periodic`.

## User story
As the chain owner, I want a twice-daily maintenance pass, so that the offer catalogue stays fresh and stale offers/sources are flagged without manual intervention.

## Acceptance criteria
- [ ] Given the periodic deferrer running, when the cron fires (0 8,20 * * *), then `run_maintenance_task` is enqueued once per slot (idempotent via Procrastinate periodic defer).
- [ ] Given the task runs, then it enqueues `collect_source_task` for every source returned by `list_sources()`, then runs `expire_offers_task` and `check_sources_health_task`.
- [ ] Given a partial failure (one source down), then the pass continues for the others and logs the error; the task does not crash the worker.
- [ ] Given the worker is started without `--periodic`, then no duplicate/missed scheduling occurs (documented in runbook).

## Out of scope
No external scheduler (cron/systemd) — use Procrastinate periodic to stay in-stack (ADR 0003). No new alert channels (reuse `_send_alert`).

## Technical notes
- Add `run_maintenance_task(timestamp: int)` in `api/app/jobs/tasks.py` decorated with `@app.periodic(cron="0 8,20 * * *", periodic_id="offer-maintenance")`. Task signature must accept `timestamp` (Procrastinate injects it).
- Enqueue child tasks via `.defer()`; wrap each in try/except to isolate failures.
- Document worker startup with `--periodic` in `docs/runbooks/` (new or existing).
- Update `docs/tech-debt.md` if backoff/dashboard reserves from T-020 remain.

## Dependencies
- T-020 (done): jobs exist.
- T-019 (done): source connectors registered.
- T-022, T-023: expire/health implementations (done or in progress).

Prochaine action : fullstack-devops implements; brief below.
---

## Brief de passation — T-032
Tâche : T-032
Pour : fullstack-devops
Objectif : planifier une passe de maintenance 2x/jour via Procrastinate periodic.
Fichiers / zones concernés : api/app/jobs/tasks.py (nouvelle tâche + décorateur periodic), docs/runbooks/ (worker --periodic), tests unit.
Décisions déjà prises (ADR) : ADR 0003 (Procrastinate), section 2 (pas de Redis/Celery).
Pièges connus : la tâche periodic doit accepter `timestamp`; le worker doit être lancé avec `--periodic` pour que le deferrer tourne; isoler les échecs par source.
Attendu en sortie : tâche enregistrée, test unit sur l'orchestration (mock des jobs enfants), runbook mis à jour.
Permissions à demander à l'utilisateur : ajout de dépendance ? non (croniter déjà transitif de procrastinate). Modification config ? documenter seulement.

## Review
### Revue — T-032
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- (aucun) — corrections précédentes appliquées : expire/health via `.defer()`, snapshot `sources`, test d'orchestration présent.

### Mineur / suggestion
- (aucun)

### Points positifs (max 2)
- Isolation des échecs par source et par tâche enfant correctement implémentée ; le run ne crashe pas le worker.
- Runbook `docs/runbooks/worker-periodic.md` documente `--periodic`, l'unicité d'instance et le rollback.

### Critères d'acceptation
- AC1 (cron 0 8,20, enqueue once via periodic defer) : satisfait par le décorateur `@app.periodic`.
- AC2 (collect pour chaque source puis expire et health) : satisfait, tous en `.defer()`, snapshot sources.
- AC3 (échec partiel isolé, log, pas de crash) : satisfait, couvert par `test_run_maintenance_partial_failure_continues`.
- AC4 (worker sans --periodic documenté) : satisfait par le runbook.

### Cohérence ADR 0003
- Procrastinate réutilisé, aucune nouvelle dépendance, retries/locks cohérents. Conforme.

### Sécurité
- SQL statique (pas d'injection). `_send_alert` n'expose pas la clé API. Aucun path traversal. Conforme.

Prochaine action : passage à fullstack-qa pour recette (statut qa).

## Implementation log
- Changed `expire_offers_task` and `check_sources_health_task` to be enqueued via `.defer()` instead of direct synchronous calls, matching `collect_source_task.defer`. Snapshot `list_sources()` into `sources` before loop.
- Added `api/tests/unit/test_maintenance_orchestration.py` covering full orchestration and partial failure.
- Author of code: fullstack-devops.

## QA report
### Avis de recette — T-032
Auteur du code : fullstack-devops | Recetteur : fullstack-qa (indépendance : OK)
Verdict : ACCEPTÉ

### Critères d'acceptation
- [x] AC1 — cron 0 8,20 + periodic_id "offer-maintenance" via `@app.periodic`; signature accepte `timestamp` — preuve : tasks.py:121-123.
- [x] AC2 — enqueue collect_source_task pour chaque source de `list_sources()`, puis expire_offers_task et check_sources_health_task via `.defer()` — preuve : tasks.py:131-153, test 1.
- [x] AC3 — échec partiel isolé (try/except par source et par enfant), log, pas de crash — preuve : test_run_maintenance_partial_failure_continues.
- [x] AC4 — worker sans --periodic documenté (runbook worker-periodic.md : une instance avec --periodic, autres sans).

### Tests exécutés
- Automatisés : 2/2 passés (pytest tests/unit/test_maintenance_orchestration.py, venv).
- Manuels : relecture du runbook, vérification isolation.

### Bugs
- (aucun)

### Zones non couvertes / risques résiduels
- Pas de test d'intégration avec Procrastinate réel (periodic defer) — dépend de l'infra; couvert par le framework.
- `_send_alert` fait un appel réseau sans timeout global sur webhook? timeout=10 présent.

### Non-régression
- Zones vérifiées : tasks.py imports, jobs app; tests collection OK.

Prochaine action : go pour done (validation utilisateur).
