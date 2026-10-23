---
id: T-002
title: Database schema and Alembic migrations (Neon)
status: done
owner: fullstack-devops
priority: P0
size: M
---

## Context
Create initial tables: users, sources, raw_documents, offers, templates, style_guides, generated_assets, publications. users table for login.

## Acceptance criteria
- [ ] Alembic configured with async SQLAlchemy
- [ ] Initial migration creates all V0 tables
- [ ] Migration runs against Neon DATABASE_URL
- [ ] Indexes per spec (fingerprint, status+created_at)

## Technical notes
UUID primary keys, timestamptz UTC, no hard deletes.
## Implementation log
- author_of_code: fullstack-devops
- Created app/core/db.py (async engine + Base + session factory).
- Created app/models.py with all V0 tables.
- Rewrote migrations/env.py for async SQLAlchemy.
- Added migrations/versions/0001_initial_schema.py initial migration.
- Pending: add asyncpg dependency (permission required) to run migrations against Neon.

## Review
Verdict : APPROUVÉ (sous réserve de condition)

### Bloquant
- None (code).

### Important
- Migration not yet executed against Neon (no DATABASE_URL configured, asyncpg dependency pending) — acceptance criterion "Migration runs against Neon DATABASE_URL" not yet satisfied. Must be executed and verified before done.
- Offer index `idx_offers_title_company_trgm` declared with `postgresql_using="gin"` and `gin_trgm_ops` ops in migration, but model declares `Index(..., postgresql_using="gin")` without ops — autogenerate drift risk; keep migration as source of truth, ensure model matches to avoid spurious diffs.

### Mineur / suggestion
- `_now()` uses `__import__("datetime")` inline; prefer a normal import for readability.
- `onupdate=func.now()` relies on ORM-side update; consider DB trigger for updated_at if needed (not required by spec).

### Points positifs (max 2)
- All V0 tables present and consistent with we-info-jobs.md section 6, UUID PKs, timestamptz UTC, soft-delete-friendly FKs (SET NULL/CASCADE).
- Required indexes (fingerprint, status+created_at, pg_trgm) present in migration; pg_trgm extension created.

## QA report
### Avis de recette — T-002
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ (sous réserve de validation utilisateur pour passage en done)

### Critères d'acceptation
- [x] Alembic configured with async SQLAlchemy — migrations/env.py async; alembic_version table present, revision 0001_initial_schema recorded.
- [x] Initial migration creates all V0 tables — 9 app tables present: users, sources, raw_documents, offers, templates, style_guides, generated_assets, publications, jobs_log (plus alembic_version).
- [x] Migration runs against Neon DATABASE_URL — verified live against Neon; alembic_version = 0001_initial_schema.
- [x] Indexes per spec — idx_offers_fingerprint, idx_offers_status_created, idx_offers_origin_url, idx_offers_title_company_trgm (GIN, gin_trgm_ops), idx_raw_documents_url, unique constraint raw_documents_content_hash_key (content_hash unique).
- [x] Extension pg_trgm — present (plpgsql also).

### Tests exécutés
- Automatisés : N/A (schema validation via live SQL).
- Manuels : information_schema/pg_indexes/pg_extension/pg_constraint/alembic_version queries against Neon.

### Bugs
- None blocking.

### Zones non couvertes / risques résiduels
- Model/migration drift risk on idx_offers_title_company_trgm ops noted in Review remains; not blocking, track separately.
- Downgrade drops pg_trgm extension globally (could affect other objects); not exercised.

### Non-régression
- Zones vérifiées : live Neon schema matches migration 0001_initial_schema.

Prochaine action : utilisateur valide le passage en done (status: done).
