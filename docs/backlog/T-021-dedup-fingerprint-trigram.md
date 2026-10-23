---
id: T-021
title: Deduplication via fingerprint and trigram similarity
status: done
owner: fullstack-devops
author_of_code: ""
priority: P1
size: M
---

## Context
Compute fingerprint hash (company+title+city normalized) and detect near-duplicates via pg_trgm + rapidfuzz, surfaced not auto-deleted.

## User story
As the chain owner, I want near-duplicate offers flagged, so that I can merge them manually.

## Acceptance criteria
- [x] Given two offers with same normalized company+title+city, when normalized, then fingerprint matches.
- [ ] Given near-similar titles, when compared, then trigram similarity above threshold flags them.
- [ ] Given flagged duplicates, when viewed, then merge action is available.

## Out of scope
No automatic deletion of duplicates.

## Technical notes
GIN trigram index on normalized title and company. Normalize: lowercase, strip accents, punctuation, stop words.
## Implementation log
(filled by the implementer)

## Review
Auteur du code : fullstack-devops   |   Relecteur : tech-lead-po

Verdict : APPROUVÉ SOUS CONDITIONS

### Bloquant
- (aucun)

### Important
- dedup.py:94-100 — `detect_duplicates` est O(n²) pour la détection near-dup. Acceptable jusqu'à ~1000 offres (dataset actuel ≤ 1000). Au-delà, déléguer le trigram à Postgres (pg_trgm GIN) comme prévu dans les notes techniques. À documenter comme seuil de remise en cause.
- dedup.py:64 — `is_near_duplicate` ne compare que le titre, alors que le contexte suggère company+title+city. Décision : acceptable pour le périmètre (BUG-021-3 S4), mais documenter dans la docstring que le seuil 0.6 est calibré sur le titre seul.
- Intégration DB (`doublon_de` column, écriture, merge UI) : non livrée. Ce n'est pas un défaut du module pur, mais l'AC "merge action available" n'est pas rempli. Recommandation : reporter l'intégration à une tâche dédiée (T-021b ou rattachement à T-012) et marquer les AC d'intégration comme hors périmètre de T-021. Condition de livraison.

### Mineur / suggestion
- dedup.py:17 — `normalize` strip accents via NFKD ; OK. Stop words en minuscules après lowercasing : correct.
- dedup.py:76 — `from typing import Any` local inutile (déjà importé en haut) : nettoyer.
- dedup.py:32 — `fingerprint` retourne None si tout vide : bonne décision, évite faux positifs. Conserver.
- detect_duplicates utilise `result.setdefault` pour near-dup : premier gagne, cohérent avec la stratégie canonical.

### Points positifs (max 2)
- Module pur, sans dépendance DB : testable isolément, conforme SOLID/DIP (storage injecté ailleurs).
- Gestion explicite des cas None/vides dans normalize/trigram_similarity : pas de crash silencieux.

### Points à tracer en dette technique
- Seuil 0.6 non calibré empiriquement sur données réelles (à valider en Sprint 5).
- Pas d'index GIN trigram livré (reporté).
- Complexité O(n²) pour near-dup au-delà de 1000 offres.

Prochaine action : fullstack-devops nettoie l'import local et ajoute les tests manquants (is_duplicate_fingerprint, fingerprint all-None, trigram_similarity None, normalize ponctuation seule) ; tech-lead-po valide le report de l'intégration DB à une tâche dédiée.

## QA report
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)

Verdict : ACCEPTÉ SOUS RÉSERVES (logique core OK, intégration DB/UI manquante)

### Critères d'acceptation
- [x] Given two offers with same normalized company+title+city, when normalized, then fingerprint matches — fingerprint() stable et insensible à la casse/accents. Preuve : test_fingerprint_matches_identical passe.
- [ ] Given two offers ... then doublon_de is set — aucune écriture DB ni champ doublon_de dans le code livré (dedup.py est pur). Le critère d'intégration n'est pas rempli. S2.
- [x] Given near-similar titles, when compared, then trigram similarity above threshold flags them — is_near_duplicate fonctionne. Preuve : test_near_duplicate_flags_similar passe.
- [ ] Given flagged duplicates, when viewed, then merge action is available — aucune UI/action de merge dans le périmètre livré. S3 (hors code actuel).

### Tests exécutés
- Automatisés : tests/unit/test_dedup.py — 6 passed. Cas limites testés manuellement : None, chaînes vides, hash collision non observée (sha256).
- Manuels : normalize("") → "", fingerprint(None,None,None) → hash de "||" (stable mais collision potentielle si toutes None), is_duplicate_fingerprint("", "") → False (correct, évite faux positif), trigram_similarity(None, x) → 0.0.

### Bugs
- BUG-021-1 (S2) — RÉSOLU partiel : detect_duplicates implémenté au niveau pur (mapping doublon_de). Intégration DB/UI (écriture doublon_de, merge) toujours hors périmètre.
- BUG-021-2 (S3) — RÉSOLU : fingerprint retourne None si tout vide.
- BUG-021-3 (S4) — is_near_duplicate utilise uniquement le titre, pas company+city comme le contexte suggère ; acceptable pour le périmètre mais à documenter.

### Zones non couvertes / risques résiduels
- Pas de test pour is_duplicate_fingerprint, fingerprint all-None, trigram_similarity None, normalize avec ponctuation seule.
- Pas de test d'intégration DB (index GIN trigram) — non livré.
- Pas de vérification empirique du seuil 0.6 sur données réelles.

### Non-régression
- Zones vérifiées : tests unit passent; aucune régression détectée.

Prochaine action : tech-lead-po valide si l'intégration DB (doublon_de + merge) est dans le sprint courant ou reportée; fullstack-devops complète si décidé.
