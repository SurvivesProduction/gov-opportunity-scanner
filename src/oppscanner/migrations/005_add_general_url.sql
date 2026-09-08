-- 005_add_general_url.sql
-- Adds `general_url`, a separate concept from `url`. Forced concrete by
-- Anne Arundel County's Harbor fetcher, whose `url` field was found to
-- be the SAME generic listing-page link on every record, not a genuine
-- per-record deep link the way eVA/Baltimore County/AACPS's `url`
-- values are -- the same underlying shape DC OCP's `url=null` already
-- represents (no stable per-solicitation link exists). `general_url` is
-- the honest alternative: "browse this SOURCE's listings here," meant
-- to be shown once per source, never repeated per record. See
-- `OpportunityRecord.general_url`'s docstring for the full reasoning.

alter table opportunities
    add column if not exists general_url text;
