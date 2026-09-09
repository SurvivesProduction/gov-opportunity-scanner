# gov-opportunity-scanner

Public template: tracks active/upcoming government contract-bid and permit opportunities across multiple jurisdictions (counties, cities, states), normalizing every source into one shared opportunity shape instead of one schema per portal.

This is the generic/free version -- no real portal targets, no client-specific normalization or alerting. See the full build for a real client deployment: [gov-opportunity-scanner-full](../gov-opportunity-scanner-full).

## What this is

`oppscanner` is a small, reusable framework for turning "N government bid/permit portals across N jurisdictions" into one normalized, queryable table:

- A `sources` registry table (slug, name, state, jurisdiction, portal_type, active) -- jurisdictions are data, not hardcoded scraper logic.
- `BaseOpportunityFetcher` -- the abstract `fetch -> parse -> normalize` pipeline every concrete fetcher implements. One shared interface for both bid and permit sources (see the schema note below).
- `oppscanner.scrapers.registry` -- a `@register_fetcher("source_slug")` decorator and `get_fetcher_class(slug)` lookup. This is what makes adding a new jurisdiction "write one new fetcher module," not "touch shared code": a fetcher module registers itself, and anything holding a `sources.slug` string can resolve and run it without importing that module by name.
- `OpportunityRecord` -- the single normalized schema every fetcher produces, whether the source is a bid portal or a permit portal (`opportunity_type` distinguishes them).
- A Postgres client (`oppscanner.db.client`) that upserts opportunities keyed on their real, stable native identifier (`external_id`), and manages the `sources` registry table.

It intentionally does not include any real scraping targets, client identifiers, or hosting-provider-specific wiring (e.g. Supabase). Those live in a paid/full deployment layer that installs this package as a dependency and adds the client-specific pieces on top.

## Real fetchers live in the full repo

This public package still ships no real scraping targets by design (see "What this is" above) -- but five real ones exist now, in [gov-opportunity-scanner-full](../gov-opportunity-scanner-full): Anne Arundel County MD's Oracle Fusion Cloud procurement portal ("Harbor"), Virginia's statewide eVA eProcurement Marketplace, Baltimore County MD's OpenGov procurement portal, Washington DC's OCP Contracts and Procurement Transparency Portal, and Anne Arundel County Public Schools' current-solicitations page. Each was built only after manually inspecting the real portal first (static HTML vs. JS-rendered, search-form gating, hidden REST APIs behind a JS SPA, non-obvious filter syntax) -- per the same data-source-refinement workflow used for Tool 1's AACPS scraper. `scripts/run_scraper.py` here still demonstrates the generic framework -- including the registry mechanism -- against two small hardcoded synthetic sources, independent of any real fetcher.

## Install

Requires Python >=3.11 and a Postgres database.

```bash
pip install -e .
# or, with test dependencies:
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and fill in your own values:

```bash
cp .env.example .env
```

`DATABASE_URL` is the preferred way to configure the connection; if it's unset, the standard `PGHOST`/`PGPORT`/`PGDATABASE`/`PGUSER`/`PGPASSWORD` variables are used instead.

## Run migrations

```bash
python scripts/migrate.py
```

This applies every SQL file under `src/oppscanner/migrations/` in order: `001_init_schema.sql` (`sources`/`opportunities`), `002_add_needs_review.sql` (`needs_review`/`review_reason`), `003_add_jurisdiction.sql` (`jurisdiction`), `004_add_contact_specialist.sql` (`contact_name`/`contact_email`/`contact_phone`), and `005_add_general_url.sql` (`general_url`, a once-per-source browse link distinct from a per-record `url`). Every migration is written with `if not exists` guards, so it's safe to rerun.

## Run the demo scraper

```bash
python scripts/run_scraper.py --client-id demo
```

Seeds two example rows into the `sources` registry, runs two template fetchers registered against them via `@register_fetcher`, upserts the results, then prints what's on file. Not a real portal -- a reference for what a real fetcher's `fetch`/`parse`/`normalize` methods and its `@register_fetcher(...)` registration should look like.

## How the pieces fit together

- **`oppscanner.scrapers.base.BaseOpportunityFetcher`** -- subclass once per portal. `fetch()` retrieves raw content, `parse()` turns it into a list of raw record dicts, `normalize()` turns one raw record into an `OpportunityRecord`. `run()` orchestrates all three.
- **`oppscanner.scrapers.registry`** -- `register_fetcher(slug)` (class decorator) and `get_fetcher_class(slug)` (lookup). Raises on a conflicting duplicate slug registration rather than silently overwriting.
- **`oppscanner.normalize.schema.OpportunityRecord`** -- the normalized shape every fetcher must produce. `client_id` (data ownership) and `source_slug` (which portal/geography) are separate, independent fields -- see the schema's docstring. `needs_review`/`review_reason` let a fetcher flag a record it couldn't cleanly parse (e.g. a missing required field) instead of silently dropping it or guessing. `jurisdiction` (which government body a posting belongs to, when that's not reliably `county`/`state`) and `contact_name`/`contact_email`/`contact_phone` (a named human contact, when a source has one) were added once real sources made the gap concrete -- both `None` unless a source genuinely provides them. `general_url` is a separate concept from `url`: `url` means "this exact link shows THIS record" (`None` when no such link exists), `general_url` means "here's where to browse this source's listings" (identical across every record from that source, meant to be shown once per source, not per record) -- see the schema's own docstring for the real source that made this distinction necessary.
- **`oppscanner.normalize.dedup.compute_synthetic_external_id`** -- a fallback for a source with no native stable id, mirroring Tool 1's normalized-hash dedup key. Not needed by any of the five real fetchers in the full repo (each exposes a genuine native id) -- exists ahead of need for the next source that doesn't. See that module's docstring for two real, opposite-shaped id-selection mistakes to check for first.
- **`oppscanner.db.client`** -- `upsert_opportunity` (keyed on `client_id, source_slug, external_id`), `upsert_source`/`active_sources` (manage the `sources` registry).

A downstream deployment (like the full/paid repo) adds concrete fetcher subclasses for real portals, seeds real `sources` rows, client_id-tagged wiring, and digest integration on top -- without needing to touch or fork this package's code.

## Tests

```bash
pip install -e ".[dev]"
pytest
```

Covers `OpportunityRecord` schema validation, the fetcher registry's register/resolve/conflict behavior, and `BaseOpportunityFetcher.run()`'s fetch -> parse -> normalize orchestration against a synthetic fixture fetcher -- all testable without a live database or a real scraped portal.
