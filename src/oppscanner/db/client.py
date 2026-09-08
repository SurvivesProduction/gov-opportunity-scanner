"""Generic Postgres client wrapper for oppscanner.

Handles connecting to Postgres and the upsert logic shared by every
fetcher, plus the `sources` registry table. Nothing here is specific to
any hosting provider (e.g. Supabase) or client -- that kind of wiring
belongs in a downstream "full" deployment package.

Dedup is a plain exact-match upsert on `(client_id, source_slug,
external_id)`, following Tool 2's precedent (`leadscorer.db.client`) over
Tool 1's 3-tier fuzzy match: government bid and permit postings are
virtually always issued with a genuine stable reference/permit number by
the source itself, so a fuzzy-match tier isn't needed here either. If a
real source turns out not to expose one, that's a reason to revisit this
for that source specifically, not to force a hash-based key where a real
id should exist.
"""
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from oppscanner.config import DatabaseConfig
from oppscanner.normalize.schema import OpportunityRecord


def get_connection(dsn: str | None = None) -> psycopg.Connection:
    """Open a Postgres connection.

    Uses `dsn` if given, otherwise resolves connection settings from the
    environment via `DatabaseConfig.from_env()`.
    """
    resolved_dsn = dsn or DatabaseConfig.from_env().dsn
    return psycopg.connect(resolved_dsn)


def _opportunity_content_params(record: OpportunityRecord) -> dict[str, Any]:
    return {
        "opportunity_type": record.opportunity_type,
        "title": record.title,
        "description": record.description,
        "status": record.status,
        "agency": record.agency,
        "address": record.address,
        "county": record.county,
        "state": record.state,
        "jurisdiction": record.jurisdiction,
        "contact_name": record.contact_name,
        "contact_email": record.contact_email,
        "contact_phone": record.contact_phone,
        "posted_date": record.posted_date,
        "due_date": record.due_date,
        "estimated_value": record.estimated_value,
        "url": record.url,
        "raw_data": Jsonb(record.raw_data),
        "needs_review": record.needs_review,
        "review_reason": record.review_reason,
    }


def upsert_opportunity(conn: psycopg.Connection, record: OpportunityRecord) -> dict[str, Any]:
    """Insert or update an opportunity, keyed on (client_id, source_slug, external_id).

    An exact match refreshes the row's content and bumps `last_seen_at`;
    no match inserts a new row (`first_seen_at` set by the column
    default).
    """
    query = """
        insert into opportunities (
            client_id, source_slug, external_id, opportunity_type, title,
            description, status, agency, address, county, state, jurisdiction,
            contact_name, contact_email, contact_phone,
            posted_date, due_date, estimated_value, url, raw_data,
            needs_review, review_reason
        ) values (
            %(client_id)s, %(source_slug)s, %(external_id)s, %(opportunity_type)s,
            %(title)s, %(description)s, %(status)s, %(agency)s, %(address)s,
            %(county)s, %(state)s, %(jurisdiction)s,
            %(contact_name)s, %(contact_email)s, %(contact_phone)s,
            %(posted_date)s, %(due_date)s,
            %(estimated_value)s, %(url)s, %(raw_data)s,
            %(needs_review)s, %(review_reason)s
        )
        on conflict (client_id, source_slug, external_id) do update set
            opportunity_type = excluded.opportunity_type,
            title = excluded.title,
            description = excluded.description,
            status = excluded.status,
            agency = excluded.agency,
            address = excluded.address,
            county = excluded.county,
            state = excluded.state,
            jurisdiction = excluded.jurisdiction,
            contact_name = excluded.contact_name,
            contact_email = excluded.contact_email,
            contact_phone = excluded.contact_phone,
            posted_date = excluded.posted_date,
            due_date = excluded.due_date,
            estimated_value = excluded.estimated_value,
            url = excluded.url,
            raw_data = excluded.raw_data,
            needs_review = excluded.needs_review,
            review_reason = excluded.review_reason,
            last_seen_at = now(),
            updated_at = now()
        returning *
    """
    params = {
        "client_id": record.client_id,
        "source_slug": record.source_slug,
        "external_id": record.external_id,
        **_opportunity_content_params(record),
    }
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    conn.commit()
    assert row is not None
    return row


def opportunities_for_client(conn: psycopg.Connection, client_id: str) -> list[dict[str, Any]]:
    """Return every opportunity record for `client_id`."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from opportunities where client_id = %(client_id)s", {"client_id": client_id})
        return cur.fetchall()


def upsert_source(
    conn: psycopg.Connection,
    slug: str,
    name: str,
    state: str,
    jurisdiction: str | None = None,
    portal_type: str | None = None,
    active: bool = True,
) -> dict[str, Any]:
    """Insert or update a row in the `sources` registry table, keyed on `slug`.

    This is metadata about a jurisdiction/portal, not client data -- it
    carries no `client_id` and is shared across every client that ends up
    referencing it. Seeding real rows here (once real sources are
    discovered) is how a new jurisdiction gets turned "on"; a fetcher
    module registering itself in code (`oppscanner.scrapers.registry`) is
    the other half -- both need to exist for a source to actually run.
    """
    query = """
        insert into sources (slug, name, state, jurisdiction, portal_type, active)
        values (%(slug)s, %(name)s, %(state)s, %(jurisdiction)s, %(portal_type)s, %(active)s)
        on conflict (slug) do update set
            name = excluded.name,
            state = excluded.state,
            jurisdiction = excluded.jurisdiction,
            portal_type = excluded.portal_type,
            active = excluded.active,
            updated_at = now()
        returning *
    """
    params = {
        "slug": slug,
        "name": name,
        "state": state,
        "jurisdiction": jurisdiction,
        "portal_type": portal_type,
        "active": active,
    }
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        row = cur.fetchone()
    conn.commit()
    assert row is not None
    return row


def active_sources(conn: psycopg.Connection) -> list[dict[str, Any]]:
    """Return every row in `sources` with `active = true`.

    This is the client-agnostic half of "which sources should run" -- a
    downstream deployment's orchestration script (e.g. `oppscanner_full`'s
    client-run script) is what narrows this down to the sources a
    specific client actually wants, typically by cross-referencing
    `clients/<client_id>/config.yaml`'s `targets:` list against this
    table's `slug` column.
    """
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("select * from sources where active = true order by slug")
        return cur.fetchall()
