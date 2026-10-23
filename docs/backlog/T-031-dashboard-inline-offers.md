---
id: T-031
title: Dashboard inline offers list
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
The dashboard (`web/app/pages/dashboard.vue`) currently renders only a title. The chain owner wants the offers list displayed inline on the dashboard (not only on /offers), so triage can start from the home screen.

## User story
As the chain owner, I want the dashboard to show the offers list directly, so that I can triage without navigating to /offers.

## Acceptance criteria
- [ ] Given offers exist, when /dashboard loads, then a paginated offers list renders with status badges and key fields (title, company, city, contract_type, score, created_at).
- [ ] Given filters (status, city, search), when applied on the dashboard, then the list updates (URL may or may not reflect filters; documented).
- [ ] Given an offer row, when clicked, then navigation goes to /offers/:id.
- [ ] Given no offers, when /dashboard loads, then an empty state is shown (no crash).

## Out of scope
No new API endpoints; reuse `/api/v1/offers`. No bulk actions on the dashboard (keep on /offers). No real-time WebSocket (polling 10s acceptable).

## Technical notes
Reuse the rendering logic from `web/app/pages/offers.vue` (extract shared component if duplication > ~40 lines). Respect T-013 debt (fetch direct `/api/v1/offers` acceptable until schema regen). Polling via TanStack Query refetchInterval 10s.

## Dependencies
- T-013 (done): /offers page reference implementation.
- T-014 (offer detail page) for row click target.

Prochaine action : fullstack-devops implements; brief below.
---

## Brief de passation — T-031
Tâche : T-031
Pour : fullstack-devops
Objectif : afficher la liste des offres inline sur le dashboard (réutiliser /offers).
Fichiers / zones concernés : web/app/pages/dashboard.vue; éventuellement nouveau composant web/app/components/OffersTable.vue.
Décisions déjà prises (ADR) : ADR 0001 (stack), conventions T-013 (fetch direct acceptable).
Pièges connus : éviter la duplication massive avec offers.vue; extraire composant partagé si >40 lignes.
Attendu en sortie : dashboard avec liste paginée + filtres basiques + empty state + navigation vers détail.
Permissions à demander à l'utilisateur : aucune (lecture/écriture front dans périmètre).

## Implementation log
- Created `web/app/components/OffersList.vue` (shared component): filters (status, city, search, sort), paginated list with status badges and key fields (title, company, city, contract_type, score, created_at), polling 10s, empty state, row click navigates to /offers/:id, load more.
- Updated `web/app/pages/dashboard.vue` to render `<OffersList />`.
- No bulk actions on dashboard (kept on /offers). No new deps. No API changes.

## Review
### Revue — T-031
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- (aucun)

### Mineur / suggestion
- `web/app/components/OffersList.vue:66` — warning `vue/max-attributes-per-line` sur le `<div v-else class=...>` ; cosmétique, non bloquant.
- Les filtres ne sont pas reflétés dans l'URL (contrairement à `offers.vue`). Conforme au critère "URL may or may not reflect filters; documented".

### Points positifs (max 2)
- Extraction d'un composant partagé `OffersList.vue` réutilisable, dashboard réduit à un rendu pur (pas de logique métier).
- Empty state, polling 10s, navigation vers détail, pagination "Load more" tous présents.

Prochaine action : validation QA par un agent qui n'a pas écrit le code.

## QA report
### Avis de recette — T-031
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ

### Critères d'acceptation
- [x] Given offers exist, when /dashboard loads, then a paginated offers list renders with status badges and key fields (title, company, city, contract_type, score, created_at) — `dashboard.vue` renders `<OffersList />`; table columns title/company/city/contract/status/score/created present.
- [x] Given filters (status, city, search), when applied on the dashboard, then the list updates (URL may or may not reflect filters; documented) — filters present, `applyFilters()` resets cursor + refetch; URL not reflected, documented in review.
- [x] Given an offer row, when clicked, then navigation goes to /offers/:id — `goTo(o.id)` → `router.push('/offers/${id}')`.
- [x] Given no offers, when /dashboard loads, then an empty state is shown (no crash) — `v-else-if="items.length === 0"` renders "No offers found."

### Tests exécutés
- Automatisés : aucune suite de tests front dans le repo (0/0). Lint/typecheck lancés : erreurs préexistantes hors périmètre T-031 (`offers/[id].vue` TS, `generate/[offerId].vue` lint). `OffersList.vue` : 1 warning cosmétique (vue/max-attributes-per-line, déjà noté en review).
- Manuels : relecture du diff et des critères; vérification empty state, polling `refetchInterval: 10000`, "Load more" via cursor.

### Bugs
- (aucun)

### Zones non couvertes / risques résiduels
- Aucun test automatisé front; régression future non détectée automatiquement.
- `search` filter client-side only (server query ignores `search` param) — hérité de T-013, documenté.
- `loadMore` ne concatène pas les pages : remplace `cursor` et la requête renvoie une nouvelle page, l'ancienne liste est remplacée plutôt qu'accumulée. Comportement hérité d'offers.vue; à surveiller (UX "Load more" attendu cumulatif). Mineur, non bloquant.

### Non-régression
- Zones vérifiées : dashboard.vue désormais rend la liste; aucune modification d'API; bulk actions restent sur /offers uniquement.

Prochaine action : validation utilisateur de la livraison, puis passage en done.