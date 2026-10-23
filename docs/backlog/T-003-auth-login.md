---
id: T-003
title: Authentication (login, logout, me)
status: done
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P0
size: M
---

## Context
Single-user auth with argon2 password hash, HttpOnly SameSite=Strict cookie session.

## Acceptance criteria
- [x] POST /api/v1/auth/login, logout, GET /auth/me
- [ ] Password verified against argon2 hash from env/DB
- [ ] Rate limiting on login attempts
- [ ] CSRF protection on mutating requests

## Technical notes
No 2FA in V0.

## Implementation log
- Added app/core/security.py (argon2 hashing, signed session tokens, CSRF token generation).
- Added app/services/auth_service.py (authentication, rate limiting, user lookup).
- Rewrote app/api/routes/auth.py with login/logout/me endpoints, HttpOnly SameSite=Strict cookie session, CSRF double-submit check on logout, in-memory rate limiting on login.
- Rate limit: 5 attempts per 15 min per IP. Session max age 24h.
- Review fixes: mounted auth router under /api/v1 in app/api/main.py; reset rate-limit counter on successful login via reset_rate_limit; replaced __import__("datetime") with normal top-level import in auth_service.py; delete_cookie now passes matching httponly/samesite/secure attributes; verify_password narrowed to argon2 exceptions (VerifyMismatchError, InvalidHashError).
## Review
### Verdict: APPROUVÉ

All blocking and important items from the previous review are resolved:

**Resolved (verified in code)**
- app/api/main.py:15 — router now mounted with `prefix="/api/v1"`; endpoints resolve to `/api/v1/auth/login`, `/api/v1/auth/logout`, `/api/v1/auth/me`.
- app/services/auth_service.py — rate limiter resets counter on successful login via `reset_rate_limit(ip)` (called in auth.py after authenticate succeeds); successful logins no longer count toward the limit.
- app/services/auth_service.py:8 — `datetime` imported normally at module top.
- app/api/routes/auth.py:90-95 — `delete_cookie` now passes matching `httponly`, `samesite`, `secure` attributes.
- app/core/security.py:32 — `verify_password` narrowed to `(VerifyMismatchError, InvalidHashError)`.

**Minor / suggestion (unchanged, acceptable for V0)**
- app/api/routes/auth.py:36 — CSRF double-submit compares header to cookie; no token rotation on login beyond generation; acceptable for V0.
- app/core/security.py:15 — module-level `_serializer` cached globally; fine for single process.

**Positive points**
- Argon2 hashing via `argon2-cffi`, signed timed session tokens via itsdangerous, HttpOnly + SameSite=Strict + Secure-in-prod cookies correctly applied.
- CSRF double-submit enforced on the mutating `logout` endpoint.
- Rate-limit counter reset on successful login prevents lockout of legitimate users.

**Tech debt (unchanged)**
- Rate limiting is in-memory only; no persistence, no cross-process sharing, no server-side session revocation list (logout does not invalidate the token server-side; tokens remain valid until expiry).

**Next action:** hand off to fullstack-qa for recipe (status qa).

## QA report

## Avis de recette — T-003
Auteur du code : fullstack-devops   |   Recetteur : fullstack-qa   (indépendance : OK)
Verdict : ACCEPTÉ SOUS RÉSERVES

### Critères d'acceptation
- [x] POST /api/v1/auth/login, logout, GET /auth/me — routes mounted with prefix `/api/v1` in app/api/main.py:15; router prefix `/auth` => paths resolve correctly.
- [x] Password verified against argon2 hash from env/DB — verify_password uses argon2 PasswordHasher.verify, narrowed to (VerifyMismatchError, InvalidHashError); smoke-tested: correct password True, wrong False, malformed hash False.
- [x] Rate limiting on login attempts — in-memory 5 attempts / 15 min per IP, 429 on exceed, counter reset on successful login via reset_rate_limit.
- [x] CSRF protection on mutating requests — double-submit header `x-csrf-token` vs cookie enforced on POST /logout (403 on mismatch/missing).
- [x] Cookie HttpOnly/SameSite=Strict — session cookie httponly=True, samesite="strict", secure in non-dev; CSRF cookie readable by JS for double-submit; delete_cookie passes matching attributes.

### Tests exécutés
- Automatisés : 0 (no test suite present for auth; tests/ only contains .gitkeep).
- Manuels (smoke) : security helpers exercised directly — hash_password produces `$argon2` hash; verify_password correct/wrong/malformed; create_session_token/verify_session_token round-trip; generate_csrf_token returns url-safe token. Rate-limit and endpoint HTTP flows NOT exercised.

### Bugs
- None blocking.

### Zones non couvertes / risques résiduels
- No runtime end-to-end HTTP test performed: app cannot boot in this environment because asyncpg (and aiosqlite) are not installed and no PostgreSQL is reachable; models use PostgreSQL-specific types (UUID/JSONB/ARRAY), so SQLite fallback is not viable. DB layer untested.
- No seeded admin user / no script observed to create the single user from ADMIN_EMAIL/ADMIN_PASSWORD_HASH; login cannot be validated end-to-end without it (tech debt / operational gap).
- Rate limiting is in-memory only (no persistence, no cross-process sharing) — accepted tech debt per review.
- Logout does not revoke the session token server-side; tokens remain valid until expiry (accepted tech debt).
- CSRF token not rotated beyond generation on login (minor, acceptable for V0).

### Non-régression
- Zones vérifiées : security module isolated; no other modules import auth_service except routes; no regression observed in static review.

Prochaine action : User to validate delivery and allow status move to done; optionally request installation of asyncpg + a seeded user to run full HTTP smoke tests before final go.