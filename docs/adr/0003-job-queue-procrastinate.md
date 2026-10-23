# ADR 0003 — Job queue: Procrastinate (PostgreSQL-backed)

Status: accepted
Date: 2026-10-20

## Context

T-020 introduces the scheduled collection and processing pipeline (collect_source, fetch, extract, normalize, plus maintenance jobs). The project runs on Render (ADR 0001) with Neon managed PostgreSQL and no Docker/Redis. The job queue must not add a new managed service or container.

## Options considered

1. Redis + RQ — pros: mainstream, simple, well-documented; cons: requires Redis (new managed service, cost, ops), contradicts ADR 0001 (no new infra, tight budget), two data stores to operate.
2. Procrastinate (PostgreSQL-backed) — pros: reuses the existing Neon Postgres, no new service, native retries/locks/queues, fits Render Background Worker; cons: smaller ecosystem than RQ, connector tied to psycopg sync driver, fewer third-party integrations.
3. Celery + Redis — pros: feature-rich; cons: heavier, requires Redis, over-engineered for a solo dev (YAGNI).

## Decision

- Use Procrastinate, backed by the same PostgreSQL instance (DATABASE_URL, converted to a sync psycopg DSN at runtime).
- Run workers as a Render Background Worker (ADR 0001).
- Retries are declared per task (`retry=3`); backoff relies on Procrastinate defaults unless a task explicitly sets `retry_after`.
- Task-level locks (`lock="collect:{source_id}"`) guarantee idempotent collection per source.

## Consequences

Positive: zero new managed service, single source of truth (Postgres), simpler ops, native retry/lock primitives.
Negative: smaller community; debugging requires Postgres inspection; sync driver bridge adds a conversion step.
Risks: Procrastinate version upgrades may break connector DSN handling; mitigated by pinning the version in pyproject/requirements.

## Revisit when

- Job throughput or concurrency outgrows a single Postgres-backed worker.
- A second queue backend becomes genuinely needed (YAGNI until then).
- Render/Neon constraints force a move to a dedicated queue service.