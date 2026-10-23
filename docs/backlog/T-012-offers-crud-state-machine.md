---
id: T-012
title: Offers CRUD and state transition endpoints
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: M
---

## Context
Implement offer listing with filters/sort/cursor pagination and centralized state machine.

## User story
As the chain owner, I want to list, filter, and transition offers, so that I can manage the review queue.

## Acceptance criteria
- [ ] Given filters (status, source, city, contract, sector, date, suspecte), when GET /offers, then matching offers are returned with cursor pagination.
- [ ] Given a valid transition (nouvelle->selectionnee, selectionnee->publiee, etc.), when POST /offers/{id}/status, then status updates.
- [ ] Given an invalid transition, when requested, then 409 is returned.
- [ ] Given PATCH /offers/{id}, when called, then editable fields update and updated_at changes.

## Out of scope
No scoring-based sorting (V3).

## Technical notes
Single module owns allowed transitions. No hard deletes.
## Implementation log
- Created app/offers/state_machine.py with centralized TRANSITIONS map.
- GET /offers now returns full offer objects; cursor pagination guards empty result.
- Fixed datetime import (no __import__ hack); updated_at set on status transition and patch.
- Added unit tests: tests/unit/test_offers_state_machine.py.

## Review
Verdict: APPROUVÉ

### Bloquant
- (aucun) Les deux bloquants précédents sont corrigés : GET /offers renvoie des objets complets avec pagination par curseur ; import datetime/timezone normal.

### Important
- api/app/api/routes/offers.py:140-147 — pagination par `Offer.id` avec `next_cursor` nul si résultat vide ou page incomplète ; OK.
- api/app/api/routes/offers.py:179-183 — transition de statut met à jour `updated_at` ; OK.
- api/app/api/routes/offers.py:198-204 — PATCH met à jour `updated_at` ; OK.
- Tests unitaires de la machine à états présents et passants (tests/unit/test_offers_state_machine.py, 3 tests). Tests d'intégration GET filtres/cursor, 409 et PATCH updated_at toujours absents — à ajouter par QA avant recette finale (condition).

### Mineur / suggestion
- `suspecte` alias mappé sur `suspicious` ; OK.
- Aucun endpoint de suppression dure ; OK.
- Machine à états centralisée et utilisée ; OK.

### Points positifs (max 2)
- State machine centralisée dans app/offers/state_machine.py, source unique de vérité.
- GET /offers renvoie maintenant des objets complets exploitables par le frontend (T-013).

### Go / no-go
Décision recommandée : GO SOUS CONDITIONS
Critères d'acceptation : 4/4 satisfaits côté code
Avis QA : en attente — tests d'intégration à ajouter
Risques résiduels : absence de tests d'intégration sur les endpoints offers
Dette introduite : aucune
Conditions : ajouter tests d'intégration (GET filtres/cursor, 409, PATCH updated_at) avant passage en qa
Décision finale : à l'utilisateur.

Prochaine action : fullstack-qa ajoute les tests d'intégration manquants, puis passage en statut qa.

## QA report
## Avis de recette — T-012
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] critère 1 (GET /offers filtres + cursor) — code vérifié : filtres status/source/city/contract/sector/date/suspecte + cursor par id, next_cursor null si vide/page incomplète.
- [x] critère 2 (transition valide) — is_allowed centralisé, 409 si invalide (test unitaire state machine).
- [x] critère 3 (invalid transition 409) — route lève HTTPException 409.
- [x] critère 4 (PATCH updated_at) — updated_at réassigné à now(utc) dans patch et transition.

### Tests exécutés
- Automatisés : 28 passés / 0 échoués (unit + integration collection via venv)
- Manuels : lecture du diff route + state machine.

### Bugs
- (aucun bloquant)

### Zones non couvertes / risques résiduels
- Tests d'intégration HTTP pour GET filtres/cursor, 409, PATCH updated_at toujours absents (notés par la revue). Risque résiduel : non couverture end-to-end des endpoints.
- `date` filter utilise `>=` (comportement acceptable mais non précisé).

### Non-régression
- Zones vérifiées : unit tests state machine (3), suite globale.

Prochaine action : ajouter tests d'intégration HTTP avant passage en done, ou décision utilisateur de livrer sous réserve.
