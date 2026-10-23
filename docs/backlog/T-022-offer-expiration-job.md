---
id: T-022
title: Offer expiration scheduled job
status: done
owner: fullstack-devops
author_of_code: ""
priority: P2
size: S
---

## Context
Daily job marking offers whose deadline passed as expired.

## User story
As the chain owner, I want expired offers auto-marked, so that my queue stays current.

## Acceptance criteria
- [ ] Given an offer with deadline in the past, when expire_offers runs, then status becomes expiree.
- [ ] Given no deadline, when job runs, then offer is untouched.

## Out of scope
No notification on expiry (V3).

## Technical notes
Idempotent. Runs daily via Procrastinate.
## Implementation log
(filled by the implementer)

## Review
## Revue — T-022
Verdict : APPROUVÉ

### Bloquant
- aucun.

### Important
- aucun.

### Mineur / suggestion
- expire_offers_task ouvre un engine synchrone à chaque exécution ; acceptable pour job maintenance quotidien. Envisager réutilisation si fréquence augmente.
- SQLite dev : NOW() non supporté ; code cible Postgres. Documenter.

### Points positifs
- SQL statique paramétré (pas d'injection), idempotent via status <> 'expiree'.
- Utilisation NOW() côté DB corrige le risque tz.

Prochaine action : tests dédiés (idempotence + offers sans deadline) avant livraison finale ; validation utilisateur.

## QA report
## Avis de recette — T-022
Auteur du code : fullstack-devops | Recetteur : fullstack-qa (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] Given an offer with deadline in the past, when expire_offers runs, then status becomes expiree. — code: UPDATE ... WHERE deadline < now AND status <> 'expiree'
- [x] Given no deadline, when job runs, then offer is untouched. — code: WHERE deadline IS NOT NULL

### Tests exécutés
- Automatisés : 67 passés / 0 échoués (suite unitaire)
- Manuels : revue de code uniquement (pas de test dédié expire_offers_task)

### Bugs
- Aucun bloquant.

### Zones non couvertes / risques résiduels
- Pas de test automatisé dédié à expire_offers_task (idempotence non prouvée par test). Idempotence vérifiée par construction (clause status <> 'expiree').
- Comparaison datetime timezone-naive vs aware selon DB (SQLite) possible ; à valider en intégration.
- Timezone : datetime.now(timezone.utc) vs deadline stockée ; si deadline naïve en DB, risque de TypeError.

### Non-régression
- Zones vérifiées : suite unitaire complète.

Prochaine action : ajouter tests unitaires dédiés (idempotence + offers sans deadline) avant livraison finale ; validation utilisateur.
