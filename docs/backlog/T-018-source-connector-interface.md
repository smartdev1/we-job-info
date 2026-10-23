---
id: T-018
title: Source connector interface and registry
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: S
---

## Context
Define common connector interface (lister, recuperer, sante) and registry to add a source with one file plus one registry line.

## User story
As a developer, I want a pluggable source connector interface, so that adding a source is trivial and testable.

## Acceptance criteria
- [ ] Given a new connector, when registered, then collect_source job can invoke it.
- [ ] Given a connector failure, when it occurs, then it is recorded (counter, last error) not swallowed.
- [ ] Given sante(), when called, then it reports source health.

## Out of scope
No specific connectors here.

## Technical notes
Preference order: RSS/API, email, HTTP scraping, Playwright. Respect robots.txt, User-Agent, timeouts in core.
## Implementation log
- Created `app/sources/connector.py`: `SourceConnector` protocol (lister/recuperer/sante), `ConnectorHealth`, `RegisteredConnector` wrapper tracking failures (counter, last error, timestamps) without swallowing, registry functions register/get_connector/list_sources/unregister.
- Created `app/jobs/collect_source.py`: `collect_source(source_id)` invokes connector lister+recuperer; failures propagate.
- Health state persists in registry instance.
- Fix: BaseException -> Exception in connector.py (no longer intercepts KeyboardInterrupt/SystemExit).
- Fix: sante() now records success (updates last_success_at) on success; swallows exceptions only for health reporting (documented).
- Fix: factory condition extracted to is_factory helper with comment.
- Added tests/unit/test_sources_connector.py covering runtime-checkable interface, registry, collect_source, recorded failures, sante().

## Review
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- (aucun) — BaseException remplacé par Exception (lignes 69,78,93) ; sante() avale l'exception du connecteur pour le reporting de santé, choix documenté en docstring, les autres opérations propagent.

### Mineur / suggestion
- (aucun) — condition de factory extraite en helper `is_factory` avec commentaire explicatif ; ConnectorHealth.last_success_at mis à jour par sante() réussie (ligne 92).

### Points positifs (max 2)
- Échecs enregistrés (compteur, last_error, timestamps) puis re-propagés, jamais avalés.
- Health persistée via instance conservée dans le registre ; interface runtime-checkable et registry testés (10 tests passants).

Prochaine action : passer à fullstack-qa pour recette (agent différent de l'auteur du code), puis go/no-go.

## QA report
(filled by the QA agent)
