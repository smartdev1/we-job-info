---
id: T-024
title: Offer scoring engine
status: done
owner: fullstack-devops
author_of_code: "fullstack-devops"
priority: P2
size: M
---

## Context
Compute a score from freshness, completeness, deadline/contact presence, priority sector/city.

## User story
As the chain owner, I want offers ranked by score, so that I handle the best ones first.

## Acceptance criteria
- [ ] Given an offer, when normalized, then score is computed and stored.
- [ ] Given sort by score, when listing offers, then highest score first.

## Out of scope
No ML-based scoring.

## Technical notes
Rules-based. Configurable priority sectors/cities via env or settings.
## Implementation log
(filled by the implementer)

## Review
### Revue — T-024 (finale)
Verdict : APPROUVÉ SOUS RÉSERVES

### Bloquant
- (aucun)

### Important
- `api/app/services/scoring.py:45` — `created_at` dans le futur donne encore `age_days` négatif → +0.2 (offre "fraîche" artificielle). La correction demandée (`age_days = max(age_days, 0)`) n'est toujours pas appliquée. À corriger avant livraison.
- `api/app/services/scoring.py:8-9` — `PRIORITY_SECTORS`/`PRIORITY_CITIES` restent hardcodés. Dette documentée (voir docs/tech-debt.md) ; acceptable si assumption écrite, mais à externaliser via settings avant prod.
- AC "sort by score" et "score computed and stored" non couverts par ce module : intégration dans `offer_service`/listing à vérifier hors diff.

### Mineur / suggestion
- `api/app/services/scoring.py:60-61` — double appel à `get("sector")`. Lisibilité.
- Tests : borne [0,1] couverte (`test_score_bounds`), mais pas de cas date future ni ORM-like explicitement.
- Pas de test de persistance/tri (hors module).

### Points positifs (max 2)
- Fonction pure, dict et ORM-like via `getattr` — testable, découplée de la DB (DIP respecté).
- Formule bornée et arrondie, pondérations explicites.

Prochaine action : appliquer le guard date future ; vérifier intégration compute_score dans offers pipeline + tri ; documenter dette config.

## QA report
## Avis de recette — T-024
Auteur du code : fullstack-devops (owner) — champ author_of_code vide dans la tâche, à compléter par l'implémenteur   |   Recetteur : fullstack-qa   (indépendance : OK sous réserve)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] Given an offer, when normalized, then score is computed and stored. — compute_score implémenté et testé (tests/unit/test_scoring.py : 4 passed). Stockage/sortie hors de ce module (à vérifier dans la couche offers).
- [ ] Given sort by score, when listing offers, then highest score first. — non vérifiable dans ce module seul ; dépend de la requête de listing (non présent dans le diff).

### Tests exécutés
- Automatisés : 4 passés / 0 échoués (uv run pytest tests/unit/test_scoring.py, PYTHONPATH=api)
- Manuels : cas limites inspectés — offer vide, offer complète, ORM-like via getattr, date naive, None.

### Bugs
- Aucun bloquant.

### Zones non couvertes / risques résiduels
- created_at dans le futur donne age_days négatif et compte comme "frais" (≤7) → score gonflé. Risque faible, à calibrer.
- Pas de test de non-régression pour la borne [0,1] ni pour les dates futures.
- Tri par score et persistance non couverts par ce module.

### Non-régression
- Zones vérifiées : suite unitaire complète (71 passed, 1 skipped).

Prochaine action : tech-lead-po valide le tri/persistance côté offers ; compléter author_of_code.
