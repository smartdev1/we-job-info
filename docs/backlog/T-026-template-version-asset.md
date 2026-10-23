---
id: T-026
title: Traçabilité version de template sur GeneratedAsset
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
Quand un asset visuel est genere, on ne sait plus quelle version du template a ete utilisee. Il faut ajouter une colonne `template_version` sur `generated_assets` pour permettre le diagnostic et le rollback si un template est modifie a posteriori.

## User story
En tant qu'operateur, je veux connaitre la version du template ayant produit un asset, pour pouvoir identifier les assets generes avec une version obsolete du template.

## Acceptance criteria
- [ ] Colonne `template_version` (Integer, default 0, nullable=False) sur `GeneratedAsset`
- [ ] Migration Alembic `0003_template_version_on_asset` (revises `0002_template_kind_markup`)
- [ ] Valeur par defaut 0 pour les lignes existantes (legacy/inconnu)
- [ ] `seed_templates.py` rendement idempotent (verifie l'existence par nom avant insertion)
- [ ] Tests CRUD templates passent (creation, versioning, 404)
- [ ] Aucun doublon de template en cas de reexécution du seed

## Out of scope
- Mise a jour automatique de `template_version` lors du rendu (le caller defini la valeur)
- Versioning des `StyleGuide` (deferre)

## Technical notes
- `template_version = 0` = legacy / inconnue pour les lignes creees avant cette migration
- Le seed est idempotent via `select(Template).where(Template.name == name)`
- Dépendances `aiosqlite`, `jinja2`, `pillow`, `python-multipart` déjà présentes dans `pyproject.toml` (ajoutees par `uv add` pour les besoins runtime + tests), aucune modification de `pyproject.toml` requise.

## Implementation log
- 2026-10-20 : ajout de `template_version` sur `GeneratedAsset` dans `models.py`
- 2026-10-20 : creation migration `0003_template_version_on_asset.py`
- 2026-10-20 : `seed_templates.py` rendu idempotent
- 2026-10-20 : pytest CRUD templates 2/2 OK

## Review
Verdict : APPROUVE (tech-lead-po, contre-visite post-correction).
- `GeneratedAsset.template_version` : Integer, default=0, nullable=False (models.py ligne 173).
- Migration `0003_template_version_on_asset` revises `0002_template_kind_markup`, server_default="0" (lignes existantes = 0), downgrade supprime la colonne.
- `seed_templates.py` idempotent via verification d'existence par nom ; double execution -> exactement 2 templates (test verifie).
- Nouveaux tests : `test_generated_asset_template_version_defaults_to_zero`, `test_seed_templates_is_idempotent` ; CRUD templates 4/4 OK.
- Aucune modification de pyproject.toml requise (dependances deja presentes).
Statut : passe en `qa` pour recette par fullstack-qa.

## QA report
Auteur du code : fullstack-devops | Recetteur : fullstack-qa (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES (tests non exécutés par le recetteur — permission requise)

### Critères d'acceptation
- [x] Colonne `template_version` (Integer, default 0, nullable=False) sur `GeneratedAsset` — models.py ligne 173 : `Mapped[int] = mapped_column(Integer, default=0, nullable=False)`. OK.
- [x] Migration Alembic `0003_template_version_on_asset` (revises `0002_template_kind_markup`) — migration présente, revision/down_revision corrects. OK.
- [x] Valeur par défaut 0 pour les lignes existantes — `server_default="0"` dans la migration. OK.
- [x] `seed_templates.py` idempotent (vérification existence par nom avant insertion) — `select(Template).where(Template.name == name)` + `scalar_one_or_none()`. OK.
- [x] Tests CRUD templates présents : `test_template_crud_with_versioning`, `test_generated_asset_template_version_defaults_to_zero`, `test_seed_templates_is_idempotent`, `test_template_unknown_404`. OK (lecture).
- [x] Aucun doublon de template en cas de réexécution du seed — test assert count == 2 après deux appels. OK (lecture).

### Tests exécutés
- Automatisés : non exécutés par le recetteur (permission requise pour lancer pytest). Revue statique des 4 tests : cohérents.
- Manuels : lecture de models.py, migration, seed_templates.py, test_templates_crud.py.

### Bugs
- Aucun bug bloquant identifié à la lecture.

### Zones non couvertes / risques résiduels
- La migration n'a pas été exécutée/validée contre une DB PostgreSQL réelle (SQLite en tests). Risque : `server_default="0"` côté PG OK, mais à confirmer en CI avec PG.
- `default=0` ORM vs `server_default` : cohérents.
- Le seed utilise `asyncio.run` et monkeypatch de `get_settings` ; dépendance à un fichier SQLite temporaire non nettoyé en cas d'échec (os.unlink dans finally, OK).
- Pas de test de downgrade de la migration.
- `template_version` n'est pas exposé/consommé par le caller (hors scope, conforme).

### Non-régression
- Zones vérifiées : GeneratedAsset model, migration chain 0001→0002→0003, seed_templates.

### Prochaine action
Demander à l'utilisateur la permission d'exécuter `pytest tests/unit/test_templates_crud.py` pour validation finale ; si vert, passer la tâche à `done`.
