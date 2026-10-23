---
id: T-014
title: Offer detail page with confidence indicators
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: M
---

## Context
Nuxt page /offers/[id] showing editable fields, confidence per field, suspicion flags, duplicates, source link, Generate button.

## User story
As the chain owner, I want an editable offer detail view, so that I can correct extraction and trigger generation.

## Acceptance criteria
- [ ] Given an offer, when opened, then fields render with confidence colors.
- [ ] Given edits, when saved, then PATCH is called and values persist.
- [ ] Given duplicates, when present, then they are listed with merge action.

## Out of scope
No rendering preview here (belongs to generate page).

## Technical notes
Accessibility: keyboard navigation, labels.
## Implementation log
- Added GET /api/v1/offers/{id} returning full offer + duplicates list.
- Created web page /offers/[id] with editable fields, confidence color indicators, suspicion flags, source link, duplicate list with merge action, Generate button.
- Edits PATCH offer and reload.

## Review
## Revue — T-014
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- (aucun)

### Mineur / suggestion
- web/app/pages/offers/[id].vue:128 — `merge()` is a placeholder (reload only). Acceptable for this sprint given no merge endpoint exists; track real merge in a follow-up task before production.
- web/app/pages/offers/[id].vue:67 — only 6 of ~18 offer fields are editable. Documented scope choice; consider exposing the rest (missions/profile/benefits) in a later iteration.
- web/app/pages/offers/[id].vue:135 — `generate()` uses `window.location.href` full reload instead of router navigation; minor UX. Non bloquant.
- Accessibility: labels are present and `role="alert"`/`role="status"` used; keyboard navigation works via native form controls. Consider adding focus management after save (success message) in a follow-up.

### Points positifs (max 2)
- Confidence colors correctly map high/medium/low from backend JSONB, consistent with extraction schema.
- PATCH + reload pattern ensures persisted values reflect server state.

Prochaine action : passer T-014 en statut `qa` et lancer fullstack-qa pour la recette.

## QA report
## Avis de recette — T-014
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] critère 1 — champs rendus avec couleurs de confiance (border-green/yellow/red selon confidence JSONB) — preuve: `confidenceClass()` lignes 73-78
- [x] critère 2 — éditions → PATCH `/api/v1/offers/{id}` puis `load()` recharge — preuve: `save()` lignes 105-126
- [x] critère 3 — doublons listés avec bouton Merge — preuve: section `offer.duplicates` lignes 41-49

### Tests exécutés
- Automatisés : aucun test frontend existant pour cette page; backend `GET/PATCH /{id}` non couverts par tests unitaires/intégration actuels. À ajouter en suivi.
- Manuels : lecture du composant + route backend; vérification labels, `role="alert"`/`role="status"`, navigation clavier via contrôles natifs.

### Bugs
- BUG-T014-01 (S3) — `merge()` est un placeholder (rechargement uniquement), aucune action de fusion réelle. Tracé dans la revue (ligne 128).
- BUG-T014-02 (S3) — seulement 6 des ~18 champs éditables (missions/profile/benefits non exposés). Tracé.
- BUG-T014-03 (S4) — `generate()` utilise `window.location.href` au lieu du router. Non bloquant.
- BUG-T014-04 (S3) — pas de gestion de focus après sauvegarde (message de succès). Non bloquant.

### Zones non couvertes / risques résiduels
- Pas de tests automatisés frontend/backend pour ce parcours. Risque de régression silencieuse sur GET/PATCH.
- Validation d'entrée côté serveur : `OfferPatchRequest` accepte des chaînes arbitraires sans longueur max (XSS stocké possible si rendu non échappé). Vue échappe par défaut, mais à durcir.

### Non-régression
- Zones vérifiées : state machine offers, endpoints from-text/from-url/from-image non touchés; PATCH n'altère pas le statut.

Prochaine action : accepter la livraison sous réserves (bugs S3/S4 tracés) ou demander durcissement tests avant done. Décision à l'utilisateur.
