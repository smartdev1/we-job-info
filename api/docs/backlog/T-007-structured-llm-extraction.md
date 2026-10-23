---
id: T-007
title: Structured LLM extraction prompt
status: qa
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
Implement structured JSON extraction in core/llm.py per T-008 schema.

## Acceptance criteria
- [x] extraire() sends structured JSON prompt per OffreExtraite schema
- [x] Parse JSON and validate with Pydantic
- [x] Retry once on validation error
- [x] Return OffreExtraite or raise dedicated exception
- [x] Unit tests for parsing and validation

## Implementation log
Implemented in app/core/llm.py and tests/unit/test_llm_extraction.py.
Confidence improvement: prompt now explicitly requests a `confiance` object (high/medium/low per field); `_parse` fills missing entries via heuristic (`null`/empty -> low, present consistent -> high, present ambiguous e.g. malformed email/url -> medium). Tests added for filling, preservation of model-provided values, and ambiguous email case.

## Review
### Revue — T-007
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- app/core/llm.py:75 — `response_format={"type": "json_object"}` suppose un endpoint OpenAI-compatible ; à documenter comme dépendance provider (voir ADR si un second provider est ajouté).
- app/core/llm.py:52 — prompt non calibré ; à mesurer sur dataset réel en Sprint suivant.

### Mineur / suggestion
- Aucun timeout côté client ; à surveiller lors de l'intégration réseau.

### Points positifs (max 2)
- Exception dédiée `ExtractionError` et retry unique clair.
- Validation Pydantic via `model_validate`, erreurs propagées proprement.

Prochaine action : passer en QA (agent n'ayant pas écrit le code) ; exécuter pytest tests/unit/test_llm_extraction.py.

## QA report
## Avis de recette — T-007
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] extraire() sends structured JSON prompt per OffreExtraite schema — preuve : `_extraction_prompt` injecte `OffreExtraite.model_json_schema()` + response_format json_object
- [x] Parse JSON and validate with Pydantic — preuve : `_parse` utilise json.loads + model_validate
- [x] Retry once on validation error — preuve : boucle range(2), feedback de l'erreur au modèle ; test_extraire_retries_once_then_raises (2 appels)
- [x] Return OffreExtraite or raise dedicated exception — preuve : retour typé, raise ExtractionError ; test_extraire_success_first_attempt
- [x] Unit tests for parsing and validation — preuve : 5 tests passants

### Tests exécutés
- Automatisés : 5 passés / 0 échoués (pytest tests/unit/test_llm_extraction.py, 0.99s)
- Manuels : vérification de la sous-classe ValidationError < ValueError (retry couvre bien les erreurs de schéma), lecture du diff

### Bugs
- (aucun bloquant)

### Zones non couvertes / risques résiduels
- `response_format={"type": "json_object"}` suppose un endpoint OpenAI-compatible (couplage provider) — S3, à documenter/traiter si second provider ajouté
- Prompt non calibré, à mesurer sur dataset réel — S3
- Aucun timeout côté client HTTP — S2 potentiel lors de l'intégration réseau (à surveiller)

### Non-régression
- Zones vérifiées : app/extraction (schéma OffreExtraite), imports; pas de régression détectée

Prochaine action : statut peut passer à done après validation utilisateur ; corriger le timeout client avant intégration réseau.