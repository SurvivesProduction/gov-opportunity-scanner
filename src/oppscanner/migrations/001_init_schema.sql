-- 001_init_schema.sql
-- Initial schema for oppscanner: a jurisdiction/portal registry
-- (`sources`) plus the normalized opportunity records fetched from them
-- (`opportunities`). Written to be safe to rerun (idempotent): every
-- statement uses an `if not exists` guard.
--
-- Lives in its own migration namespace, separate from Tool 1's
-- (bid_awards, digest_runs) and Tool 2's (properties, permits) -- all
-- three packages can run their own migrations against the same shared
-- Postgres database without colliding, since table names don't overlap.

create extension if not exists pgcrypto;

-- Registry of known jurisdictions/portals. Client-agnostic and global:
-- multiple clients can reference the same source (e.g. two future
-- clients both caring about the same county's bid portal), so this
-- table deliberately carries no client_id. `slug` (not a surrogate uuid)
-- is the primary key and the thing every fetcher module and every
-- `opportunities` row references -- see this repo's README for how a
-- new jurisdiction gets added.
create table if not exists sources (
    slug text primary key,
    name text not null,
    state text not null,
    jurisdiction text,
    portal_type text,
    active boolean not null default true,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_sources_state on sources (state);

-- Normalized bid/permit opportunity records. `client_id` is data
-- ownership (which client's dashboard this belongs to); `source_slug` is
-- which portal/geography it came from -- two independent axes, not
-- conflated. A single unified shape (not one table per source type)
-- because bid and permit postings across many jurisdictions all resolve
-- to the same "here is a posted opportunity" shape; `opportunity_type`
-- distinguishes them.
create table if not exists opportunities (
    id uuid primary key default gen_random_uuid(),
    client_id text not null,
    source_slug text not null references sources(slug),
    external_id text not null,
    opportunity_type text not null,
    title text not null,
    description text,
    status text,
    agency text,
    address text,
    county text,
    state text,
    posted_date date,
    due_date date,
    estimated_value numeric,
    url text,
    raw_data jsonb,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (client_id, source_slug, external_id)
);

create index if not exists idx_opportunities_client_source
    on opportunities (client_id, source_slug);

create index if not exists idx_opportunities_client_due_date
    on opportunities (client_id, due_date);

create index if not exists idx_opportunities_client_type
    on opportunities (client_id, opportunity_type);
