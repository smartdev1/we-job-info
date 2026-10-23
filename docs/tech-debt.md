# Technical debt

- T-005 — `web/app/api-client/schema.ts` is a placeholder (`export type paths = Record<string, never>`). The openapi-fetch client cannot type-check against real endpoints until the FastAPI OpenAPI spec is generated (`pnpm run generate:api`, requires running API). Until then `pnpm typecheck` cannot pass. Regenerate once the API is available locally.
- ADR 0002 — Anthropic provider path in `api/app/core/llm.py` is a stub raising NotImplementedError; only Kilo implemented. Implement when an Anthropic key becomes available.
- T-006 - Extraction LLM is never triggered: job persisted with status `pending`, no worker consumes it. Real extraction lands in T-008+. Acceptable for T-006 scope, but must not be presented as functional extraction.
- T-013 - Frontend `/offers` uses direct `fetch` to `/api/v1/offers` instead of the typed OpenAPI client, because the schema (`web/app/api-client/schema.ts`) lacks the offers endpoints (see T-005 debt). Reconcile when the OpenAPI spec is regenerated (`pnpm run generate:api`, requires running API) and migrate this fetch to the typed client. Client-side search is also limited to the current page (cursor pagination); consider server-side `q` param in `list_offers` (API) and transmitting the `sort` selector to the API.
- T-019 - No live canary tests yet (AC not satisfied). To be added outside CI.

- T-020 - `expire_offers_task` is a placeholder returning 0 (no DB wiring yet). Implement expiry logic when the offers storage layer is integrated (T-012 / T-021b).

- T-015 - Rendering pipeline:
  - `playwright` is not installed and was not added to `api/pyproject.toml` (dependency addition requires user agreement). The pipeline degrades to `FakeScreenshotEngine` locally; real screenshots require `playwright` + Chromium install.
  - No embedded woff2 font files exist in the repo; the template uses the local system font stack ("-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial"). Font embedding to be added when font files are provided (was noted as a target in tech notes, no file available yet).
