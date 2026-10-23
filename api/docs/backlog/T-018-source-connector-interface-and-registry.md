---
id: T-018
title: Source connector interface and registry
status: qa
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context
Common source connector interface, health tracking and registry.

## Acceptance criteria
- [x] Interface SourceConnector runtime-checkable (lister, recuperer, sante).
- [x] Registry (register, get_connector, list_sources, unregister).
- [x] collect_source job invokes the connector.
- [x] Failure recorded (counter, last error), not swallowed.
- [x] sante() reports health.
- [x] Tests 10 passing.

## Implementation log
Implemented in app/sources/connector.py and app/jobs/collect_source.py, tests in tests/unit/test_sources_connector.py.

## Review
(filled by tech-lead-po)

## QA report
## Avis de recette — T-018
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ

### Critères d'acceptation
- [x] Interface SourceConnector runtime-checkable (lister, recuperer, sante) — preuve : `@runtime_checkable` Protocol, test_source_connector_is_runtime_checkable passe
- [x] Registry (register, get_connector, list_sources, unregister) — preuve : tests test_register_and_get_connector_instance, test_register_factory, test_unregister
- [x] collect_source job invoque le connecteur — preuve : test_collect_source_invokes_lister_and_recuperer (result == ["A","B"])
- [x] Échec enregistré (compteur, dernière erreur), non avalé — preuve : test_failure_is_recorded_and_propagated, test_recuperer_failure_recorded
- [x] sante() rapporte la santé — preuve : test_sante_reports_health_success, test_sante_swallows_exception_for_reporting

### Tests exécutés
- Automatisés : 10 passés / 0 échoués (pytest tests/unit/test_sources_connector.py, 0.03s)
- Manuels : lecture du code, vérification runtime_checkable, factory persistence

### Bugs
- (aucun)

### Zones non couvertes / risques résiduels
- Registry en mémoire process-global ; pas de thread-safety (S3, à surveiller si multi-worker)
- sante() avale les exceptions volontairement (documenté) — S3

### Non-régression
- Zones vérifiées : app/jobs, app/sources ; pas de régression détectée

Prochaine action : statut peut passer à done après validation utilisateur.