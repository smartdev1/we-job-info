---
id: T-013
title: Dashboard offers list page (Nuxt)
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: M
---

## Context
Nuxt page /offers with filters, search, sort, bulk actions, polling via TanStack Query.

## User story
As the chain owner, I want a filterable offers list, so that I can triage new offers quickly.

## Acceptance criteria
- [ ] Given offers exist, when /offers loads, then list renders with status badges and key fields.
- [ ] Given filters selected, when applied, then URL reflects filters and list updates.
- [ ] Given bulk reject/select, when triggered, then selected offers transition and list refreshes.

## Out of scope
No keyboard shortcuts beyond basic (V3).

## Technical notes
Use generated API client. Responsive layout.
## Implementation log
- Implemented /offers page with filters (status, city, search), sort, bulk reject/select, polling via TanStack Query.
- Filters reflected in URL query params; list refreshes on change.
- Status badges and key fields rendered; responsive grid layout.
- Uses fetch to generated-ish API endpoints (schema lacks offers; fetch fallback consistent with existing offers/new.vue).
- Fix review: reformatted `<h1>` content onto its own line to satisfy `vue/singleline-html-element-content-newline` lint rule (2 errors). Documented fetch/typing debt in docs/tech-debt.md.

## Review
Verdict : APPROUVÉ

### Bloquant
- (aucun) — `pnpm lint` passe (0 erreur), y compris sur `web/app/pages/offers.vue`.

### Important
- `web/app/pages/offers.vue:102` — fetch direct `/api/v1/offers` au lieu du client typé OpenAPI : dette acceptée et documentée dans `docs/tech-debt.md` (T-013). À migrer lors de la régénération du schéma (T-005).
- `web/app/pages/offers.vue:109-113` — recherche côté client limitée à la page courante (pagination cursor). Acceptable en V1, dette notée.
- `web/app/pages/offers.vue:130` — sélecteur de tri non transmis à l'API (`list_offers` ordonne par id). À clarifier côté API (ajouter tri) ou retirer le sélecteur.
- `web/app/pages/offers.vue:146-165` — bulk transitions en `Promise.all` sans gestion d'erreur partielle. À renforcer (try/catch + rollback visuel) avant mise en production réelle.

### Mineur / suggestion
- polling 10s (`refetchInterval`) OK pour le triage.
- pas de tests front (aucun dans le repo) — acceptable en attente de la stack de tests front.

### Points positifs (max 2)
- Filtres correctement reflétés dans l'URL via `router.replace`, avec réinitialisation du cursor.
- Badges de statut et champs clés (title, company, city, contract_type, score, created_at) présents ; layout responsive.

### Vérifications effectuées
- `pnpm lint` : 0 erreur.
- `pnpm typecheck` : aucune erreur dans `web/app/pages/offers.vue` ; erreurs résiduelles dans `web/app/pages/offers/[id].vue` (T-014, hors périmètre de cette tâche) — à traiter dans T-014.
- Dette fetch/typage documentée dans `docs/tech-debt.md` (entrée T-013).

Prochaine action : passer le statut à `qa` et envoyer à fullstack-qa pour la recette (agent distinct de l'implémenteur).

## QA report
## Avis de recette — T-013
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES (pas de blocage)

### Critères d'acceptation
- [x] critère 1 — Given offers exist, when /offers loads, then list renders with status badges and key fields. Preuve : `web/app/pages/offers.vue:124-161` table avec colonnes Title/Company/City/Contract/Status/Score/Created et badge `badgeClass` ; champs `o.title`, `o.company`, `o.city`, `o.contract_type`, `o.status`, `o.score`, `o.created_at`.
- [x] critère 2 — Given filters selected, when applied, then URL reflects filters and list updates. Preuve : `applyFilters()` (l.230-241) fait `router.replace({ query: { q, status, city, sort } })` et `refetch()` ; état initialisé depuis `route.query` (l.188-191).
- [x] critère 3 — Given bulk reject/select, when triggered, then selected offers transition and list refreshes. Preuve : `bulkReject`/`bulkSelect` (l.271-281) appellent `transition` puis `refetch()` et vident la sélection.

### Tests exécutés
- Automatisés : 0 (aucune suite front dans le repo).
- Manuels : lecture du code + lint/typecheck.
- `pnpm lint` : 0 erreur (confirmé).
- `pnpm typecheck` : aucune erreur dans `offers.vue` ; erreurs résiduelles uniquement dans `offers/[id].vue` (T-014, hors périmètre).

### Bugs
- Aucun S1/S2. Dette documentée (S3) : fetch direct `/api/v1/offers` au lieu du client typé OpenAPI ; recherche côté client limitée à la page courante ; sélecteur de tri non transmis à l'API (`list_offers` ordonne par id) ; bulk transitions en `Promise.all` sans gestion d'erreur partielle. Toutes documentées dans `docs/tech-debt.md` (entrée T-013) par la revue.

### Zones non couvertes / risques résiduels
- Pas de tests front automatisés (stack front tests non disponible) — acceptable en attente.
- Polling 10s (`refetchInterval`) OK pour le triage.
- Recherche côté client ne couvre que la page courante (pagination cursor) — acceptable V1.
- Tri non propagé à l'API : à clarifier côté API ou retirer le sélecteur.

### Non-régression
- Zones vérifiées : lint global 0 erreur ; typecheck sans régression sur `offers.vue`. Erreurs pré-existantes dans `offers/[id].vue` attribuées à T-014, hors périmètre.

Prochaine action : validation utilisateur pour passer le statut à `done` (ou retour à `doing` si les réserves doivent être levées avant).
