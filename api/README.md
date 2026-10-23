# we-info-jobs API

FastAPI backend. Python 3.12+, managed with `uv`.

## Local setup

```bash
cp .env.example .env
uv sync
uv run uvicorn app.api.main:app --reload
```

Health check: `GET /healthz`.

## Migrations

```bash
uv run alembic upgrade head
```

Schema lives in T-002.

## Seeding an admin user

To enable full HTTP authentication tests against a Neon (or local) database,
create or update an admin user with an argon2-hashed password:

```bash
uv run python scripts/seed_admin.py --email admin@example.com --password 'secret'
```

If `--email` is omitted, `ADMIN_EMAIL` from `.env` is used. If `--password`
is omitted, the script prompts securely (input is not echoed). An existing
user with the same email has its password updated.