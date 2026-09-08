-- 003_add_jurisdiction.sql
-- Adds `jurisdiction` to `opportunities`, a separate axis from
-- `agency`/`county`/`state`. Forced concrete by Virginia's eVA fetcher:
-- a single statewide aggregator `source_slug` whose records span
-- counties, cities, towns, authorities, school districts, and genuine
-- state agencies -- `county`/`state` alone can't express "the specific
-- buying entity for this one record" when that entity isn't reliably a
-- county, and forcing every shape into the `county` column would misuse
-- it. See `OpportunityRecord.jurisdiction`'s docstring for the full
-- reasoning.

alter table opportunities
    add column if not exists jurisdiction text;

create index if not exists idx_opportunities_client_jurisdiction
    on opportunities (client_id, jurisdiction);
