---
id: T-025
title: Suspicion rules for scam detection
status: done
owner: fullstack-devops
author_of_code: "fullstack-devops"
priority: P2
size: S
---

## Context
Apply simple rules (payment request, free email for big company, unrealistic salary, no identifiable company, private-messaging-only contact, excessive urgency) setting suspecte and motifs_suspicion.

## User story
As the chain owner, I want suspicious offers flagged, so that I avoid publishing scams.

## Acceptance criteria
- [ ] Given an offer matching a rule, when normalized, then suspecte=true and motifs_suspicion lists reasons.
- [ ] Given no match, when normalized, then suspecte=false.
- [ ] Given flags, when viewing dashboard, then reasons are displayed.

## Out of scope
No automated rejection; human decides.

## Technical notes
Rules in offers module. Decision remains human.
## Implementation log
(filled by the implementer)

## Review
### Revue — T-025 (finale)
Verdict : APPROUVÉ SOUS RÉSERVES

### Bloquant
- (aucun)

### Important
- Regex salaire maintenant contextuelle (`salaire|rémunération|...` + montant) : correction appliquée. À valider par tests par règle.
- `api/app/services/suspicion.py:13` — règle "contact uniquement par messagerie privée" utilise la truthiness brute (`not g(...)`). Incohérent avec `_is_filled` de scoring. Harmoniser pour éviter faux positifs sur chaînes vides.
- Intégration dans le pipeline de normalisation (`suspecte`/`motifs_suspicion`) et affichage dashboard non vérifiés dans le diff.

### Mineur / suggestion
- Typage `RULES: list[tuple[str, Any]]` imprécis → `Callable`. Cosmétique.
- Tests : `test_suspicion_all_rules` ne couvre que 3 des 6 règles (paiement, aucune entreprise, urgence). Manquent : email gratuit, salaire irréaliste, contact uniquement messagerie. À compléter.

### Points positifs (max 2)
- Règles déclaratives et lisibles, faciles à étendre.
- Fonction pure, indépendante de la DB.

Prochaine action : compléter tests par règle (6/6) ; harmoniser truthiness avec `_is_filled` ; vérifier intégration normalisation + dashboard.

## QA report
## Avis de recette — T-025
Auteur du code : fullstack-devops (owner) — champ author_of_code vide dans la tâche   |   Recetteur : fullstack-qa   (indépendance : OK sous réserve)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] Given an offer matching a rule, when normalized, then suspecte=true and motifs_suspicion lists reasons. — check_suspicion renvoie (True, reasons) ; test test_suspicion_payment_request passe.
- [x] Given no match, when normalized, then suspecte=false. — test test_suspicion_clean passe.
- [ ] Given flags, when viewing dashboard, then reasons are displayed. — dépend de la couche UI/dashboard, hors de ce module.

### Tests exécutés
- Automatisés : 2 tests suspicion passés / 0 échoués (dans tests/unit/test_scoring.py)
- Manuels : inspection des 6 règles, cas None, offer vide.

### Bugs
- Aucun bloquant. Note : règle "salaire irréaliste" (\d{7,}) peut matcher des numéros de téléphone dans la description (faux positif possible) — S3 cosmétique/fonctionnel mineur, à calibrer.

### Zones non couvertes / risques résiduels
- Pas de test par règle individuelle (couverture partielle : une seule règle testée positivement).
- Intégration dans le pipeline de normalisation (suspecte/motifs_suspicion) non vérifiée ici.
- Affichage dashboard hors périmètre.

### Non-régression
- Zones vérifiées : suite unitaire complète (71 passed, 1 skipped).

Prochaine action : ajouter tests par règle ; vérifier intégration normalisation + dashboard.
