---
id: T-016
title: Copywriting variants generation
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: M
---

## Context
Generate 2-3 WhatsApp text variants from an offer and an editable style guide, with regeneration and manual edit.

## User story
As the chain owner, I want 2-3 text variants per offer, so that I can pick the best one for publication.

## Acceptance criteria
- [ ] Given an offer and active style guide, when generate is called, then 2-3 variants are stored on generated_asset.
- [ ] Given regeneration requested, when triggered, then new variants replace old ones.
- [ ] Given manual edits, when saved, then text is persisted.
- [ ] Given source attribution, when any variant is produced, then original offer link is included.

## Out of scope
No weekly recap format (V3).

## Technical notes
WhatsApp formatting (*bold*, _italic_). Only facts present in offer; no invented salary/contact/date.
## Implementation log
- Created api/app/copywriting/prompt.py (build_prompt, parse_variants with source link enforcement).
- Created api/app/copywriting/service.py (generate_variants).
- Updated core/llm.py rediger to use build_prompt.
- Created api/app/api/routes/copywriting.py (generate/list/patch variants on generated_assets, replace on regenerate).
- Registered router in main.py.
- Added tests/unit/test_copywriting.py.
- No new migration (uses existing generated_assets.text/variant/style_guide_id).
- Fix BUG-016-2: scoped regenerate delete to copywriting assets (template_id IS NULL) instead of all text assets of the offer.

## Review
(filled by tech-lead-po)

### Verdict : APPROUVÉ SOUS CONDITIONS (passé à qa)

**Points positifs**
- LLM logic stays in core/llm (rediger); prompt centralized in copywriting/prompt.
- Pydantic validation on inputs (count 2-3, min_length text).
- Source link enforced in parse_variants.

**Bloquant**
- Aucun.

**Important**
- Delete on regenerate uses `text.isnot(None)` which may wipe non-copywriting text assets for the offer; scope delete to copywriting variants (e.g. by variant index / no template) — to confirm with QA.
- service.generate_variants ignores `n` when calling parse_variants; route slices after, wasteful but functional. Align n.
- Dead `prompt = build_prompt(...)` in service (rediger rebuilds). Remove.

**Mineur**
- Only 2 unit tests; missing service/route coverage.
- parse_variants fallback split on blank lines may produce <2 variants; AC says 2-3. Caller should enforce minimum or raise.

Prochaine action : QA recette (fullstack-qa).

## QA report

### Avis de recette — T-016
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ — RECETTE VALIDÉE

### Critères d'acceptation
- [x] critère 1 (2-3 variants stored on generated_asset) — generate() crée assets avec variant=i, test parse_variants OK ; réserve : si LLM renvoie <2 variantes, moins de 2 assets stockés (BUG-016-1).
- [x] critère 2 (regeneration replaces old) — delete scoped to template_id IS NULL + text IS NOT NULL (BUG-016-2 résolu); recreate OK.
- [x] critère 3 (manual edits persisted) — PATCH met à jour asset.text + commit.
- [x] critère 4 (source attribution) — parse_variants ajoute source_url si absent ; réserve si offer sans origin_url/application_url (pas de lien à inclure).

### Tests exécutés
- Automatisés : 2 passés / 0 échoués (pytest tests/unit/test_copywriting.py)
- Manuels : lecture du diff, inspection route/service/prompt.

### Bugs
- BUG-016-1 (S3) parse_variants fallback peut produire <2 variantes ; AC exige 2-3. Recommandation : lever une erreur ou boucler.
- BUG-016-2 (S2) RÉSOLU — delete sur regenerate désormais scopé à `template_id IS NULL` (assets copywriting), ne touche plus les autres assets texte de l'offer.
- BUG-016-3 (S4) n ignoré dans service.generate_variants (parse_variants tronque à 3 puis route re-tronque). Cosmétique/perf.
- BUG-016-4 (S4) prompt = build_prompt(...) mort dans service.

### Zones non couvertes / risques résiduels
- Pas de tests service/route (DB, LLM provider).
- Offer sans URL source : impossible de satisfaire AC #4.
- Pas de validation que le style guide actif est bien celui utilisé si aucun id fourni (OK: premier actif par created_at).

### Non-régression
- Zones vérifiées : prompt/parse_variants, route CRUD minimal, scoping delete regenerate (template_id IS NULL).

Prochaine action : go/no-go utilisateur pour passage en done (S3/S4 tracés, non bloquants).
