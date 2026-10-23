# ADR 0001 - Hosting, database and tooling choices

Status: Accepted

## Context
Solo developer, tight budget, internal tool. No Docker, no Kubernetes, no microservices.

## Options considered
- Docker + self-hosted Postgres + Caddy on VPS
- Render native services + Neon managed PostgreSQL
- Serverless (Vercel/Netlify) + managed DB

## Decision
- No Docker: Render native Web Service + Background Worker.
- Database: Neon (managed PostgreSQL), connected via DATABASE_URL env var.
- Front tooling: pnpm (Nuxt 3, SPA mode).
- Python tooling: uv for dependencies and environments.
- API init via official commands (nuxi for Nuxt, uv for Python).
- Reverse proxy: Render built-in HTTPS (no Caddy).

## Consequences
Positive: less ops burden, managed backups, simpler CI.
Negative: Render free tier cold starts; Neon connection pooling limits; less control over runtime.
Risks: vendor lock-in to Render/Neon (mitigated by standard Postgres + FastAPI portability).