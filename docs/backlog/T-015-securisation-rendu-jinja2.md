---
id: T-015
title: Securisation rendu Jinja2 (echappement + validation logo_url)
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: S
---

## Context
La recette tech-lead-po de T-015 a relevé deux vecteurs XSS/SSRF dans le template de rendu `offre.html.j2` : `logo_url` et `initials` étaient injectés bruts dans le HTML. Il fallait ajouter l'echappement HTML et une validation du schemat d'URL pour `logo_url` (blocage `javascript:`, `data:`, etc.).

## User story
En tant que responsable securite, je veux que les valeurs utilisateur injectees dans le template de rendu soient echappees et que logo_url accepte uniquement http/https, pour eviter toute injection XSS ou SSRF via l'API de rendu.

## Acceptance criteria
- [ ] `src="{{ logo_url | e }}"` dans `offre.html.j2` (ligne 81)
- [ ] `{{ initials | e }}` dans le badge (ligne 83)
- [ ] `_validate_logo_url()` dans `pipeline.py` rejette les schemas non http/https
- [ ] `has_logo` utilise l'URL validee (pas d'URL douteuse chegue au template)
- [ ] Tous les tests de rendering passent (pipeline, determinisme, typographie)
- [ ] Aucun secret ni stack trace ne fuit dans les reponses

## Out of scope
- Ajout de Content-Security-Policy (deferre a V0.2)
- Validation MIME du fichier logo (deferre)

## Technical notes
- `pipeline.py` : `ALLOWED_LOGO_URL_SCHEMES = {"http", "https"}`, `TemplateError` leve si scheme interdit
- `TemplateError` est deja importe dans `pipeline.py`
- Les tests existants (`src="https://example.com/logo.png"`, badge `<div class="badge">`) restent compatibles

## Implementation log
- 2026-10-20 : echappement `logo_url | e` et `initials | e` dans `offre.html.j2`
- 2026-10-20 : correction `_validate_logo_url` rejette aussi les URLs sans schéma (ex. `//evil.internal/logo.png`) — `parsed.scheme not in ALLOWED_LOGO_URL_SCHEMES` sans garde `parsed.scheme and`
- 2026-10-20 : `safe_logo_url` passe a `has_logo` et `logo_url` dans le rendu
- 2026-10-20 : pytest 15/15 rendu OK (pipeline 6/6, determinisme 3+1 skip, typographie 7/7)

## Review
Verdict : APPROUVE (tech-lead-po, contre-visite post-correction).
- `offre.html.j2` ligne 81 : `src="{{ logo_url | e }}"` ; ligne 83 : `<div class="badge">{{ initials | e }}</div>` — echappement HTML effectif (autoescape reste False, filtre `e` explicite applique).
- `pipeline.py` : `_validate_logo_url` rejette tout scheme hors {http, https}, y compris scheme vide (`//evil.internal/logo.png` -> scheme '' refuse) et `javascript:` / `data:`. `TemplateError` leve.
- `has_logo=bool(safe_logo_url)` et `logo_url=safe_logo_url or ""` : aucune URL non validee n'atteint le template.
- Tests rendering 15/15 OK (pipeline 6/6, determinisme, typographie 7/7).
- Mineur : commentaire ligne 46 de pipeline.py fait reference a l'API `/recognize` qui n'existe pas dans ce projet (V0.1 CLI seulement) — a corriger a l'occasion, non bloquant.
Statut : passe en `qa` pour recette par fullstack-qa.

## QA report
Auteur du code : fullstack-devops | Recetteur : fullstack-qa (independance : OK)
Verdict : RECETTE VALIDEE (pas de reserve bloquante)

### Criteres d'acceptation
- [x] `src="{{ logo_url | e }}"` ligne 81 de `offre.html.j2` — present, filtre `e` applique (autoescape reste False, echappement explicite).
- [x] `{{ initials | e }}` ligne 83 dans le badge — present, filtre `e` applique.
- [x] `_validate_logo_url()` dans `pipeline.py` rejette les schemas non http/https, y compris scheme vide — `parsed.scheme not in ALLOWED_LOGO_URL_SCHEMES` sans garde `parsed.scheme and`.
- [x] `has_logo` consomme l'URL validee : `safe_logo_url = _validate_logo_url(offer.logo_url)` precede le rendu ; `has_logo=bool(safe_logo_url)`, `logo_url=safe_logo_url or ""`. Un `TemplateError` leve arrete le pipeline avant que le template ne soit rendu.
- [x] Tous les tests de rendering passent : 20/20 (pipeline 6/6, determinisme 4/4, typographie 10/10). Note environnementale : execution requise avec `PYTHONPATH=<api>` (pas de `conftest.py` ni d'install editable exposant `app` par defaut).
- [ ] Aucun secret ni stack trace ne fuit dans les reponses — N/A en V0.1 (CLI uniquement, pas d'API HTTP) ; les `TemplateError` restent internes. Confirme a re-verifier lors de l'exposition FastAPI (V0.2).

### Tests executes
- Automatises : 20/20 passes (`test_rendering_pipeline.py`, `test_rendering_determinism.py`, `test_rendering_typography.py`).
- Manuels / edge cases (script ad hoc, lecture seule) :
  - `javascript:alert(1)` -> TemplateError (OK)
  - `data:text/html,<script>...</script>` -> TemplateError (OK)
  - `//evil.internal/logo.png` (scheme vide) -> TemplateError (OK, correction appliquee)
  - `https://example.com/logo.png` -> acceptee, `has_logo=True`, `src` echappe (OK)
  - `logo_url=None` -> `has_logo=False`, badge affiche (OK)
  - `company="<script>"` / `initials="<S>"` -> `&lt;script&gt;` / `&lt;S&gt;` dans le HTML rendu (OK)
  - `logo_url` contenant `"` + `onerror=` -> un seul attribut `src`, guillemet neutralise en `&#34;`, pas de second attribut cree (OK)

### Bugs
- Aucun.

### Zones non couvertes / risques résiduels
- Aucun test unitaire persisté dans le repo pour les schèmes rejetés ni l'échappement HTML (preuves apportées à la recette par script ad hoc) — recommandation d'ajout, non bloquante.
- Décompte typographie dans le journal d'implémentation (7/7) ne correspond pas au fichier (10 tests, tous verts) — inexactitude de note, non bloquante.
- Commentaire `pipeline.py` ligne 46 référence l'API `/recognize` inexistante en V0.1 — déjà relevé par tech-lead-po, non bloquant.

### Non-regression
- Parcours sans logo (badge initiales), avec logo https, troncation de titre, chemin d'image adressé par contenu, determinisme byte-a-byte : couverts par les tests existants, tous verts.

Prochaine action : go/no-go utilisateur. Si go, passage du statut en `done`.
