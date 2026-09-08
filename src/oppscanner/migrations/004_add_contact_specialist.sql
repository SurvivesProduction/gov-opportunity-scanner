-- 004_add_contact_specialist.sql
-- Adds a named-human-contact triple to `opportunities`. Forced concrete
-- by Washington DC's OCP Contracts and Procurement Transparency Portal,
-- the first real source to surface a specific person (not just a
-- department name/inbox the way Harbor's BuyerName/BuyerEmailAddress or
-- eVA's buyername are) directly in its public results. See
-- `OpportunityRecord.contact_name`'s docstring for the full reasoning on
-- why this is separate from `agency`.

alter table opportunities
    add column if not exists contact_name text;

alter table opportunities
    add column if not exists contact_email text;

alter table opportunities
    add column if not exists contact_phone text;
