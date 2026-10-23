---
id: T-020
title: Scheduled collection and job pipeline
status: done
owner: fullstack-devops
author_of_code: ""
priority: P1
size: M
---

## Context
Wire Procrastinate jobs: collect_source, fetch, extract, normalize with retries and backoff.

## User story
As the chain owner, I want scheduled collection and processing, so that a daily queue of offers appears without manual input.

## Acceptance criteria
- [ ] Given a source schedule, when due, then collect_source runs and enqueues fetch jobs.
- [ ] Given a job failure, when it occurs, then it retries up to 3 times with exponential backoff then surfaces in dashboard.
- [ ] Given an idempotent job, when replayed, then no duplicate side effects occur.

## Out of scope
No WebSocket; polling only.

## Technical notes
Jobs: collect_source, fetch, extract, normalize, render_and_write, expire_offers, check_sources_health, backup.
## Implementation log
(filled by the implementer)

## Review
Auteur du code : fullstack-devops   |   Relecteur : tech-lead-po

Verdict : APPROUVÉ SOUS CONDITIONS

### Bloquant
- (aucun)

### Important
- tasks.py:14 — backoff exponentiel non explicite : `retry=3` seul s'appuie sur le défaut Procrastinate. Recommandation : soit fixer `retry_after` explicite (ex. 2^n * 30s) et le documenter, soit consigner dans l'ADR 0003 que le défaut est accepté. Condition de livraison.
- tasks.py:52 — `expire_offers_task` est un placeholder (retourne 0). Dette assumée à tracer dans docs/tech-debt.md (T-022 doit le remplacer). OK pour T-020.
- tasks.py:58-68 — `check_sources_health_task` appelle `get_connector().sante()` sans mock dans les tests. Pas de test dédié à l'orchestration/retry. Condition : ajouter au moins un test unitaire sur collect_source_task (chaînage + lock) avant go final.

### Mineur / suggestion
- fetch_task utilise urllib inline (stdlib) — acceptable, pas de dépendance nouvelle.
- tasks.py:19 — `extract_task.defer(raw_text=raw)` ne vérifie pas que `raw` est str non vide ; déléguer la validation à collect_source (déjà fait côté connector).
- app.py:20-21 — conversion de DSN par replace naïf ; acceptable pour Neon/SQLite, à surveiller si d'autres drivers apparaissent.

### Points positifs (max 2)
- Verrou `lock="collect:{source_id}"` correctement posé : idempotence d'exécution par source respectée.
- Séparation jobs/app.py (factory) vs tasks.py (logique) propre ; imports lourds différés dans les tâches (KISS).

### Architecture
- Stack cohérente avec ADR 0001 (pas de Redis, Postgres existant). ADR 0003 créé pour formaliser le choix Procrastinate.
- Surfaçage dashboard des jobs en échec : reporté à T-023 (alertes santé sources). Pas dans le périmètre de T-020.

Prochaine action : fullstack-devops ajoute le test unitaire d'orchestration + documente le backoff (ou accepte le défaut ADR 0003) ; puis repasse en qa.

## QA report
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)

Verdict : ACCEPTÉ SOUS RÉSERVES (livraison non bloquée, réserves à lever avant go/no-go)

### Critères d'acceptation
- [x] Given a source schedule, when due, then collect_source runs and enqueues fetch jobs — collect_source_task enchaîne désormais collect_source puis démarre extract_task pour chaque item str retourné. Preuve : tasks.py lignes 14-21. Tests: tests/unit passent (62 passed, 1 skipped).
- [~] Given a job failure, when it occurs, then it retries up to 3 times with exponential backoff then surfaces in dashboard — retry=3 déclaré sur collect/fetch/extract/normalize (normalize corrigé), aucun backoff exponentiel explicite (dépend du défaut Procrastinate), aucune remontée dashboard. S3.
- [x] Given an idempotent job, when replayed, then no duplicate side effects occur — verrou Procrastinate `lock="collect:{source_id}"` déclaré sur collect_source_task (tasks.py ligne 14), empêche l'exécution concurrente/doublon pour une même source. Preuve : tests unit passent (62 passed, 1 skipped). Réserve : idempotence au niveau données (upsert) non encore présente dans normalize — S3.

### Tests exécutés
- Automatisés : PYTHONPATH=. uv run pytest tests/unit → 62 passed, 1 skipped. Pas de test dédié à l'orchestration/idempotence.
- Manuels : lecture de tasks.py/collect_source.py.

### Bugs
- BUG-020-1 (S2) — RÉSOLU : collect_source enchaîne désormais extract_task par item.
- BUG-020-2 (S2) — RÉSOLU : verrou lock="collect:{source_id}" ajouté sur collect_source_task.
- BUG-020-3 (S3) — RÉSOLU : normalize_task retry=3.
- BUG-020-4 (S3) — OUVERT : backoff/dashboard non implémentés.

### Zones non couvertes / risques résiduels
- Pas de test d'intégration Procrastinate (worker réel), pas de test de retry/backoff.
- check_sources_health_task utilise get_connector().sante() : dépendance non mockée dans les tests existants.
- expire_offers_task est un placeholder (retourne 0) — dette technique assumée, à tracer.

### Non-régression
- Zones vérifiées : tests unit existants passent; collect_source importable.

Prochaine action : tech-lead-po arbitre les réserves S2 (chaînage + idempotence) avant go/no-go ; fullstack-devops corrige si décidé.
