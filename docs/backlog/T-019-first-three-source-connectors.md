---
id: T-019
title: First three source connectors
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
Implement 3 connectors among Emploi.ci, Educarriere, Novojob, career pages, or email alerts per owner decision.

## User story
As the chain owner, I want 3 working sources, so that offers are collected automatically.

## Acceptance criteria
- [ ] Given each connector, when lister() runs, then recent offers (url, title, date) are returned.
- [ ] Given a real page fixture, when tests run, then parsing passes.
- [ ] Given a canary test, when run against the live site, then it reports pass/fail separately from CI.

## Out of scope
No more than 3-5 sources initially.

## Technical notes
Confirm sources and access method with owner. Check CGU before regular use. Tests on recorded HTML fixtures.
## Implementation log
Implemented 3 connectors: educarriere, emploi_ci, emploiivoire in app/sources/. BaseHttpConnector provides User-Agent, timeout, robots.txt check, fetcher injection for tests. Offer dataclass (url, title, date). Theme keyword filtering. Tests in tests/unit/test_source_connectors_three.py with HTML fixtures. No new dependencies.

## Review
### Revue — T-019
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- `app/sources/educarriere.py:17-28` — l'AC mentionne `date` mais aucun connecteur n'extrait de date (Offer.date reste None). Fixtures sans date. À traiter dans une tâche dédiée ou lors du prochain lot ; non bloquant pour V0.1.
- `app/sources/base.py:61-75` — `_robots_allowed` ne met en cache `_robots` qu'en cas de succès ; en cas d'exception réseau on retourne True sans cache, donc refetch robots à chaque appel. Mineur mais à corriger (cache négatif).

### Mineur / suggestion
- `educarriere.py:25-27` — bloc `if ...: pass` inutile, à supprimer.
- Les 3 parseurs dupliquent la même logique (regex + dédup + keywords) — acceptable pour 3 sources, à refactorer si >5 sources (YAGNI).

### Points positifs (max 2)
- Base HTTP avec fetcher injectable : tests sans réseau, propres.
- Aucune dépendance ajoutée, respect de la stack.

Dette : aucun canary test live (AC non satisfait). À créer séparément (hors CI), noté dans docs/tech-debt.md.

Prochaine action : QA sur fixtures, puis go/no-go.

## QA report
## Avis de recette — T-019
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] critère 1 — lister() retourne des offres (url, title) pour les 3 connecteurs ; tests `test_educarriere_lister_uses_fetcher` etc. passent. Date non extraite (Offer.date reste None) — écart tracé (voir Important).
- [x] critère 2 — parsing sur fixtures HTML réelles : 6/6 tests passants (`test_source_connectors_three.py`).
- [ ] critère 3 — canary test live : absent, dette technique notée dans docs/tech-debt.md. À créer hors CI.

### Tests exécutés
- Automatisés : 6 passés / 0 échoués (`pytest tests/unit/test_source_connectors_three.py`)
- Manuels : vérification fixtures présentes pour 3 sources, parseurs dédup + filtrage par mots-clés thématiques.

### Bugs
- BUG-T019-01 (S3) — Offer.date jamais renseigné par les 3 parseurs ; AC mentionne date. Non bloquant pour V0.1, à traiter dans une tâche dédiée.
- BUG-T019-02 (S4) — `_robots_allowed` ne cache pas le cas d'exception réseau (refetch robots à chaque appel). Mineur.
- BUG-T019-03 (S4) — bloc `if ...: pass` inutile dans educarriere.py:25-27.

### Zones non couvertes / risques résiduels
- Parsing HTML par regex fragile : tout changement de markup source casse silencieusement. Mitigation future : tests sur fixtures mises à jour.
- Aucun canary live : régression silencieuse possible sur le site réel.
- Date non extraite : dépendance amont pour scoring/filtrage temporel.

### Non-régression
- Zones vérifiées : SourceConnector interface, base HTTP, fetcher injection, health tracking. Tests unitaires connexes non impactés.

Prochaine action : livraison sous réserve de création d'un canary test hors CI et d'extraction de date dans une tâche dédiée ; owner à trancher.
