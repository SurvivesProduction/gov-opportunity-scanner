#!/usr/bin/env python
"""Example end-to-end run of the oppscanner framework.

This is a template/demo, NOT a real scraper. `ExampleStaticBidFetcher` and
`ExampleStaticPermitFetcher` below fetch from small hardcoded in-memory
datasets instead of a real portal, and register themselves via
`oppscanner.scrapers.registry.register_fetcher` under example source
slugs -- demonstrating the exact mechanism a real downstream deployment
(e.g. `oppscanner_full.scrapers`) uses to add a new jurisdiction: write
one fetcher module, decorate its class, and the orchestration code below
never needs to import that module by name.

Usage:
    python scripts/run_scraper.py --client-id demo
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from dotenv import load_dotenv

from oppscanner.db.client import (
    get_connection,
    opportunities_for_client,
    upsert_opportunity,
    upsert_source,
)
from oppscanner.normalize.schema import OpportunityRecord
from oppscanner.scrapers.base import BaseOpportunityFetcher
from oppscanner.scrapers.registry import get_fetcher_class, register_fetcher

_EXAMPLE_BID_SLUG = "example-county-bids"
_EXAMPLE_PERMIT_SLUG = "example-city-permits"

_EXAMPLE_BIDS: list[dict[str, Any]] = [
    {
        "external_id": "BID-2026-001",
        "title": "Elementary School Electrical Panel Upgrade",
        "description": "Replace end-of-life electrical panels at two elementary schools.",
        "status": "open",
        "agency": "Example County Public Schools",
        "address": "100 Example School Rd",
        "county": "Example County",
        "state": "MD",
        "posted_date": "2026-08-01",
        "due_date": "2026-09-30",
        "estimated_value": "185000.00",
        "url": "https://example.gov/bids/BID-2026-001",
    },
]

_EXAMPLE_PERMITS: list[dict[str, Any]] = [
    {
        "external_id": "PM-2026-4471",
        "title": "Commercial Electrical Permit",
        "description": "New service and panel install, retail buildout.",
        "status": "issued",
        "agency": "Example City Permits Office",
        "address": "200 Example Retail Plaza",
        "county": "Example County",
        "state": "MD",
        "posted_date": "2026-08-15",
        "due_date": None,
        "estimated_value": None,
        "url": "https://example.gov/permits/PM-2026-4471",
    },
]


@register_fetcher(_EXAMPLE_BID_SLUG)
class ExampleStaticBidFetcher(BaseOpportunityFetcher):
    """Template fetcher demonstrating the interface for a bid source."""

    def fetch(self) -> list[dict[str, Any]]:
        return _EXAMPLE_BIDS

    def parse(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return raw

    def normalize(self, raw_record: dict[str, Any]) -> OpportunityRecord:
        return OpportunityRecord(
            client_id=self.client_id,
            source_slug=self.source_slug,
            opportunity_type="bid",
            raw_data=raw_record,
            **raw_record,
        )


@register_fetcher(_EXAMPLE_PERMIT_SLUG)
class ExampleStaticPermitFetcher(BaseOpportunityFetcher):
    """Template fetcher demonstrating the interface for a permit source."""

    def fetch(self) -> list[dict[str, Any]]:
        return _EXAMPLE_PERMITS

    def parse(self, raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return raw

    def normalize(self, raw_record: dict[str, Any]) -> OpportunityRecord:
        return OpportunityRecord(
            client_id=self.client_id,
            source_slug=self.source_slug,
            opportunity_type="permit",
            raw_data=raw_record,
            **raw_record,
        )


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Run the example oppscanner demo scrape.")
    parser.add_argument("--client-id", required=True, help="Client id to tag records with.")
    args = parser.parse_args()

    conn = get_connection()
    try:
        # Seed the sources registry -- a real deployment does this once
        # per jurisdiction (or via a one-off seed script), not on every
        # scrape run.
        upsert_source(
            conn,
            slug=_EXAMPLE_BID_SLUG,
            name="Example County Bid Portal",
            state="MD",
            jurisdiction="Example County",
            portal_type="example_static",
        )
        upsert_source(
            conn,
            slug=_EXAMPLE_PERMIT_SLUG,
            name="Example City Permit Portal",
            state="MD",
            jurisdiction="Example City",
            portal_type="example_static",
        )

        total = 0
        for slug in (_EXAMPLE_BID_SLUG, _EXAMPLE_PERMIT_SLUG):
            fetcher_cls = get_fetcher_class(slug)
            fetcher = fetcher_cls(client_id=args.client_id, source_slug=slug)
            for record in fetcher.run():
                row = upsert_opportunity(conn, record)
                total += 1
                print(f"Upserted {row['opportunity_type']}: {row['title']} (external_id={row['external_id']})")

        print(f"Done. Processed {total} opportunit(y/ies).")

        opportunities = opportunities_for_client(conn, args.client_id)
        print(f"\n{len(opportunities)} total opportunit(y/ies) on file for client '{args.client_id}'.")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
