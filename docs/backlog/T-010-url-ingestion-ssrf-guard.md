---
id: T-010
title: URL ingestion with SSRF guard
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: M
---

## Context
Fetch a job URL safely and feed extracted text into the extraction pipeline.

## User story
As the chain owner, I want to submit a job URL, so that the tool fetches and structures it without SSRF risk.

## Acceptance criteria
- [ ] Given a public http/https URL, when submitted, then content is fetched, hashed, stored as raw_document, and extraction job created.
- [ ] Given a URL resolving to a private/loopback/link-local/cloud-metadata address, when submitted, then request is rejected.
- [ ] Given a known URL hash, when submitted, then no new LLM call is made and existing offer is returned (idempotent).
- [ ] Given redirects, when followed, then each hop is re-validated against SSRF rules.

## Out of scope
No Playwright rendering in V1 unless needed for JS pages.

## Technical notes
DNS resolution, redirect re-validation, size and redirect limits, timeout. See section 15.
## Implementation log
- Implemented safe fetch + store raw_document + extraction job in offer_service.
- Idempotence by URL and content hash.
- Added max_bytes limit to safe_fetch.
- Patched safe_fetch to read response in bounded 8192-byte chunks, aborting when exceeding max_bytes (SSRF memory blowup guard).
- Strengthened integration tests: idempotence by normalized URL (existing=True/offer_id), idempotence by content hash, redirect-to-private rejection via safe_fetch.
- author_of_code: fullstack-devops

## Review
## Revue — T-010 (re-revue post-corrections)
Verdict : APPROUVÉ

### Bloquant
- (aucun)

### Important
- api/app/services/offer_service.py:67-76 — `content_type` hardcodé à `text/html` et décodage UTF-8 avec remplacement silencieux. Acceptable en V1, tracé comme dette (contenu binaire, encodage réel). Non bloquant pour cette story.

### Mineur / suggestion
- api/app/services/url_safety.py:110-113 — chemin `resp.status in (301,...)` mort (l'opener sans redirect lève HTTPError). Inoffensif, à nettoyer plus tard.
- normalize_url conserve la query string dans l'idempotence par URL : deux URL identiques à paramètre d'ordre près ne matcheront pas. Acceptable.

### Points positifs (max 2)
- safe_fetch lit en chunks bornés à max_bytes et abort au-delà (guard mémoire), re-valide chaque hop et détecte le DNS rebinding via `pinned_ips`.
- Idempotence double (URL normalisée + hash de contenu) correctement implémentée et couverte par tests (existing=True/offer_id).

### Vérifications
- safe_fetch lit en chunks bornés à max_bytes : OK (url_safety.py:118-129).
- Tests idempotence par URL et hash de contenu : OK (test_offers_from_url.py).
- Redirect SSRF rejeté : OK (test_redirect_to_private_rejected + DNS rebinding unit test).
- Suite : 18 passed, 1 skipped (unit + integration).

Prochaine action : passer au QA (fullstack-qa recette), puis go/no-go final.

## QA report
## Avis de recette — T-010
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ

### Critères d'acceptation
- [x] URL publique fetchée, hashée, stockée en raw_document et job créé — create_extraction_job_from_url (offer_service.py) + tests idempotence.
- [x] URL privée/loopback/link-local/cloud-metadata rejetée — _is_unsafe_ip + _resolve_and_check, tests unitaires.
- [x] Idempotence par URL et hash — tests integration passants.
- [x] Redirect re-validé à chaque hop — safe_fetch re-valide hostname + DNS rebinding detection.

### Tests exécutés
- Automatisés : 28 passed / 3 skipped (unit + integration).
- Manuels : revue code url_safety.py, offer_service.py.

### Bugs
- Aucun bloquant. Dette mineure tracée (content_type hardcodé, chemin mort) — S3/S4.

### Zones non couvertes / risques résiduels
- max_bytes memory guard présent.
- Encodage réel non géré (V1 acceptable).

### Non-régression
- Zones vérifiées : url_safety unit tests, offers integration.

Prochaine action : go/no-go final par tech-lead-po et utilisateur.
