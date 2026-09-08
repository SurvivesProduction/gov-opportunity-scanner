-- 002_add_needs_review.sql
-- Adds a review-flagging pair to `opportunities`, following Tool 1's
-- `bid_awards.needs_review` precedent: a fetcher that hits missing or
-- unparseable data on an otherwise-required field flags the row for a
-- human instead of silently dropping it or writing a fabricated value.
--
-- Unlike Tool 1, this column is populated directly from
-- `OpportunityRecord.needs_review`/`review_reason` (see that schema's
-- docstring) rather than computed by this layer from dedup-confidence --
-- Tool 3's upsert has no fuzzy-match tier to OR against, so there's only
-- one source of truth here, not two.

alter table opportunities
    add column if not exists needs_review boolean not null default false;

alter table opportunities
    add column if not exists review_reason text;

create index if not exists idx_opportunities_needs_review
    on opportunities (client_id, needs_review)
    where needs_review;
