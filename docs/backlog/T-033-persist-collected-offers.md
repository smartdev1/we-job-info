---
id: T-033
title: Persist collected offers from sources into database
status: review
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
Collected offers from source connectors (T-018/T-019) are currently not persisted; dashboard and /offers read from the offers table. This task wires collection to persistence with idempotence by origin_url / fingerprint, so the collected queue appears in the UI.

## User story
As the chain owner, I want offers retrieved by source collectors to be stored in the offers table, so that they appear in the dashboard and /offers without manual entry.

## Acceptance criteria
- [ ] Given a successful collection run, when offers are retrieved, then each is upserted into offers (idempotent by origin_url, fallback fingerprint).
- [ ] Given a duplicate origin_url, when re-collected, then no duplicate row is created and existing row is updated with latest metadata.
- [ ] Given an async extraction job, when it completes, then the persisted offer reflects extracted fields.
- [ ] Given collection failure on one source, when others succeed, then partial results are persisted and error logged.
- [ ] Given empty collection, when run, then no rows inserted and run marked complete.

## Out of scope
- New connectors (covered by T-018/T-019).
- Dedup merging logic (covered by T-021).
- Changes to dashboard UI (already reads from DB).

## Technical notes
- Depends on T-020 (collection jobs) and T-021 (fingerprint/dedup).
- Use parametrized queries only (OWASP A03).
- Respect state machine from T-012 (new offers enter as 'nouvelle').
- Idempotence key: origin_url unique; fallback composite fingerprint (company+title+city) per T-021.

## Implementation log
- Created app/storage/offers.py with async upsert_collected_offer (idempotent by origin_url then fingerprint, status 'nouvelle').
- Integrated into collect_source (returns origin_url+raw_text) and collect_source_task (persists + defers extraction).
- Added sync persistence helper for workers.

## Review

## QA report
---
id: T-033
title: Persist collected offers from sources into database
status: todo
owner: fullstack-devops
author_of_code:
priority: P1
size: M

## Context
Collected offers from source connectors (T-018/T-019) are currently not persisted; dashboard and /offers read from the offers table. This task wires collection to persistence with idempotence by origin_url / fingerprint, so the collected queue appears in the UI.

## User story
As the chain owner, I want offers retrieved by source collectors to be stored in the offers table, so that they appear in the dashboard and /offers without manual entry.

## Acceptance criteria
- [ ] Given a successful collection run, when offers are retrieved, then each is upserted into offers (idempotent by origin_url, fallback fingerprint).
- [ ] Given a duplicate origin_url, when re-collected, then no duplicate row is created and existing row is updated with latest metadata.
- [ ] Given an async extraction job, when it completes, then the persisted offer reflects extracted fields.
- [ ] Given collection failure on one source, when others succeed, then partial results are persisted and error logged.
- [ ] Given empty collection, when run, then no rows inserted and run marked complete.

## Out of scope
- New connectors (covered by T-018/T-019).
- Dedup merging logic (covered by T-021).
- Changes to dashboard UI (already reads from DB).

## Technical notes
- Depends on T-020 (collection jobs) and T-021 (fingerprint/dedup).
- Use parametrized queries only (OWASP A03).
- Respect state machine from T-012 (new offers enter as 'nouvelle').
- Idempotence key: origin_url unique; fallback composite fingerprint (company+title+city) per T-021.

## Implementation log

## Review

## QA report
