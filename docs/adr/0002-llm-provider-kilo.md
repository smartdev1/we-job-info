# ADR 0002 — LLM provider: Kilo AI (OpenAI-compatible) as default for V0/V1

Status: Accepted
Date: 2026-10-19

## Context

The project's extraction pipeline (offer data extraction from URLs/images, copywriting variants) depends on an LLM. The developer has no Anthropic API key available, and Kilo AI exposes an OpenAI-compatible gateway with free models. The `core/llm` abstraction layer is already planned, so the provider is swappable behind a single interface. The V1 success criterion requires an extraction accuracy of at least 90% measured on a 30-offer non-regression dataset.

## Options considered

1. Anthropic SDK (Claude Haiku/Sonnet) — pros: strong extraction quality, well-documented; cons: requires a paid API key the developer does not have; blocks V0/V1 progress.
2. Kilo AI via an OpenAI-compatible client (free models) — pros: zero cost, unblocks development, OpenAI-compatible API means a standard client; cons: free-model quality and quotas unproven against the 90% extraction criterion; rate limits may constrain batch ingestion.
3. Local model (Ollama) — pros: fully offline, no quota; cons: hardware-dependent, heavier ops, extraction quality uncertain, adds infra not in scope.

## Decision

- Default LLM provider for V0/V1 is Kilo AI, accessed through an OpenAI-compatible client (`openai` SDK pointed at the Kilo base URL), not the Anthropic SDK.
- The `core/llm` interface stays the single integration point: no LLM-specific logic leaks into `engine/`, `matching/`, or endpoints. Provider selection is driven by `LLM_PROVIDER` env var, so Anthropic remains a supported option without code changes.
- Stack section 3 is updated: replace the Python Anthropic SDK dependency with the OpenAI-compatible client targeting Kilo. No new dependency beyond the client already mainstream.
- Free models available on Kilo are used for both extraction and copywriting until accuracy is measured; model IDs are configured via env vars, not hardcoded.
- ARCCloud fallback and all other non-LLM paths are unaffected.

## Consequences

Positive: unblocks V0/V1 with zero LLM cost; keeps provider swappable via the existing abstraction; standard OpenAI client is well-audited and stable.

Negative: extraction quality of free models is unverified against the V1 90% criterion on 30 offers — may require switching models or provider. Free-tier quotas/rate limits may slow batch ingestion and scheduled collection jobs. Copywriting variant quality may be lower than with a paid model.

Risks: if free models fail the accuracy gate, V1 slips until a paid provider is funded; rate limits could mask as "no match"/failed extractions if not handled with clear errors. Mitigation: keep `LLM_PROVIDER=anthropic` path working, measure accuracy per model on the 30-offer dataset before promoting any model to default, log provider/model on every extraction call.

Vigilance points:
- Extraction accuracy gate (90% on 30 offers) must be re-run when changing the default model.
- Rate limits: implement basic backoff and clear error surfacing; never silently fall back to a wrong result.
- Interchangeability of `core/llm`: any provider must honor the same input/output contract so swapping is a config change.

## Revisit when

- A paid Anthropic key becomes available and benchmarks show materially better accuracy or cost-adjusted quality.
- Free-model accuracy on the 30-offer dataset falls below 90%.
- Kilo rate limits or quota changes block batch ingestion.
- A second provider is genuinely needed (YAGNI until then).
