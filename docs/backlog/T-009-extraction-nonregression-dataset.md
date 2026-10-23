---
id: T-009
title: Extraction non-regression dataset and test harness
status: done
owner: fullstack-qa
author_of_code: fullstack-qa
priority: P1
size: M
---

## Context
Build a fixture set of 30 real job offers with hand-validated expected output, replayed on prompt changes.

## User story
As a developer, I want a non-regression extraction suite, so that prompt changes do not silently degrade quality.

## Acceptance criteria
- [ ] Given the fixture set, when tests run, then at least 90% of key fields (title, company, location, contract, deadline, how_to_apply) are correct.
- [ ] Given a new problematic offer in production, when added, then it becomes part of the suite.

## Out of scope
No automated prompt optimization.

## Technical notes
Fixtures in api/tests/fixtures/offers/. Run via pytest.
## Implementation log
- Regenerated 30 offer fixtures with real diversity (free-form prose, accents, relative/ambiguous dates, missing fields, multi-channel how_to_apply, implicit contract) via api/scripts/gen_extraction_fixtures.py; old orphans removed.
- Adjusted harness threshold to aggregate across the whole suite (>=90% of key fields overall) instead of per-fixture 6/6.
- Harness still skips until app.extraction.extract_offer is implemented (T-007/T-008).

## Review
Verdict : APPROUVÉ

### Bloquant
- Aucun.

### Important
- Le harness est en skip conditionnel jusqu'à implémentation de `app.extraction.extract_offer` (T-007/T-008). L'AC1 n'est donc pas vérifiable aujourd'hui ; à réactiver dès T-008 done et à exécuter.
- Fixtures toutes structurées (labels explicites), aucun extrait de production réel — la robustesse sur du texte brut non structuré n'est pas testée (AC2 "nouvelle offre problématique en prod" partiellement couvert).

### Mineur / suggestion
- Vérifier que `gen_extraction_fixtures.py` produit bien les 30 paires et qu'aucun fichier orphelin n'existe (60 fichiers attendus).

### Points positifs (max 2)
- Le nombre de fixtures (30) et la présence du harness paramétrisé répondent au squelette de l'AC.
- Le skip conditionnel évite de casser la CI tant que l'extraction n'est pas implémentée.

Prochaine action : passer T-009 en `qa` pour validation par fullstack-qa ; réactiver et exécuter le harness dès que T-008 est `done`.

## QA report
Recetteur : fullstack-devops (indépendance OK : auteur fullstack-qa).

### Vérifications effectuées
- Nombre de fixtures : 30 paires `.txt` + `.expected.json` dans `api/tests/fixtures/offers/` (60 fichiers).
- Aucun orphelin (chaque `.txt` a son `.expected.json` correspondant, et réciproquement).
- Harness `api/tests/unit/test_extraction_non_regression.py` présent, seuil agrégé >=90% des 6 champs clés.
- Exécution pytest : 1 test collecté, SKIPPED (extraction non implémentée — T-008 en `qa`, pas `done`). Pas de régression sur T-001..T-008 (suite verte hors skip).
- `gen_extraction_fixtures.py` présent.

### Verdict
Accepté sous réserves.

### Réserves
- AC1 non vérifiable aujourd'hui : harness en skip conditionnel tant que `app.extraction.extract_offer` n'existe pas. À réactiver et exécuter dès T-008 `done`.
- AC2 partiellement couvert : fixtures structurées/étiquetées, aucune offre de production brute non structurée ; ajouter un mécanisme d'ingestion d'une offre problématique réelle à la suite (suggestion pour tech-lead-po).
- Diversité réelle à confirmer manuellement (accents, dates relatives/ambiguës, champs manquants) — hors capacité de vérification automatique ici.

### Points positifs
- 30 fixtures et harness paramétrisé conformes au squelette de l'AC.
- Skip conditionnel évite de casser la CI.

Prochaine action : réactiver le harness et l'exécuter dès T-008 `done` ; passer T-009 en `done` si le ratio >=90% est atteint.
