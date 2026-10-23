---
id: T-034
title: Restyle the back-office with the design language of web/screens
status: review
owner: fullstack-devops
author_of_code: fullstack-devops
priority: P1
size: M
---

## Context

The mockups in `web/screens` define the visual identity of the channel: sky/slate
palette (Tailwind sky + slate), Public Sans for the text, JetBrains Mono for the
figures, uppercase column headers, coloured pills, relative timestamps, white
filter card with `border-l` separators, "Charger plus d'offres" button.

The back-office had a raw Tailwind table, the Nuxt Starter landing page, a green
custom palette in `main.css`, and several controls that lied to the operator
(English statuses, a search that only filtered the loaded page, an unsent sort
parameter, a `merge()` button doing nothing, relative `fetch()` URLs that never
reached the API).

## User story

As the operator, I want the dashboard to look like the design I approved and to
show only true information, so that I can validate the collected offers without
second-guessing the screen.

## Acceptance criteria

- [x] The palette is the one of the mockups: `primary: sky`, `neutral: slate`,
      no custom green scale left in `main.css`.
- [x] Public Sans and JetBrains Mono are loaded and applied.
- [x] The offers list stays a **table** (decision of the owner: "Tableau").
- [x] The status vocabulary is the French one of the state machine
      (`nouvelle`, `selectionnee`, `rejetee`, `publiee`, `archivee`).
- [x] The search is done by the API (`q` on title, company, city, sector), not
      by the browser on the loaded page only.
- [x] The list is ordered by creation date, most recent first, with a composite
      cursor so that pages never overlap.
- [x] "Charger plus d'offres" appends the next page instead of replacing the
      current one.
- [x] The offer sheet (`/offers/:id`) loads, and the "Préparer la publication"
      button leads to `/generate/:id`.
- [x] The duplicates are signalled, never deleted: the action moves the
      duplicate to `rejetee`, a state the operator can undo.
- [x] `/offers/new` is reachable and the pages of the `/offers` section no
      longer trigger `NUXT_E4016`.
- [x] Every page verified in a real browser (Playwright), no console error.

## Out of scope

- The public job board of the mockups (company pages, salary, tags, application
  tracking): we have a back-office, not a public site.
- The visual rendering of the offer image: the API has no endpoint that
  triggers the rendering pipeline, so the sheet says so instead of showing an
  empty preview.
- The merge of two offers: no endpoint exists, and the spec forbids deleting a
  near-duplicate silently.

## Technical notes

- `pages/offers.vue` is now an empty shell rendering `<NuxtPage />`: Nuxt nests
  `pages/offers/*` under it, and a page file plus a folder of the same name
  triggers `NUXT_E4016`. The list moved to `pages/offers/index.vue`.
- `GET /api/v1/offers/stats` (new) returns the counters of the dashboard, so
  the numbers are computed by the database and not by downloading the catalogue.
- `GET /api/v1/offers/{id}` now returns `allowed_transitions`, so the front
  does not duplicate the state machine.
- The contract type is normalised to a single value: the platforms publish a
  multi-select list as one string ("CDI - CDD - Stage"), which broke the layout
  of the table. Nine offers already stored were corrected in place.

## Implementation log

- API: search `q`, chronological order with a composite cursor, `stats`
  endpoint, `allowed_transitions` on the offer sheet, contract type
  normalisation.
- Front: `app.vue` shell, `BrandLogo`, `app.config.ts`, `main.css`,
  `OffersList` (table, filters, pills, relative time, bulk bar, load more),
  `pages/offers/index.vue`, `pages/offers.vue` shell, `pages/offers/[id].vue`
  (two columns, correction form with the confidence colours, duplicates),
  `pages/offers/new.vue`, `pages/generate/[offerId].vue`, `pages/dashboard.vue`
  (counters), `pages/index.vue` (redirect).
- Bugs fixed: statuses in English (filter never matched, bulk actions answered
  409), `fetch()` without `apiBase` in two pages (404), `/generate?offer=`
  (route that does not exist), `merge()` no-op, `sort` never sent, "Charger
  plus" replacing the list instead of appending.

## Review

(filled by tech-lead-po)

## QA report

(filled by the QA agent)
