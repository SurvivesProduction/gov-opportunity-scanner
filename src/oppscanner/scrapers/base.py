"""Abstract base class every jurisdiction/portal-specific fetcher implements.

One shared interface, not two: unlike Tool 2's property/permit split (two
genuinely different record shapes), this tool's bid and permit sources
both resolve to the same "posted opportunity" shape (see
`oppscanner.normalize.schema.OpportunityRecord`) -- the fetch -> parse ->
normalize -> yield pipeline below is identical for either, and
`OpportunityRecord.opportunity_type` is what a downstream reader uses to
tell them apart, not a different class.

Concrete subclasses live in a downstream package (e.g. the paid per-client
deployment) and are parametrized per portal / jurisdiction. This class has
no knowledge of any specific scraping target.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from typing import Any

from oppscanner.normalize.schema import OpportunityRecord


class BaseOpportunityFetcher(ABC):
    """Fetch -> parse -> normalize -> yield pipeline for one source.

    `source_slug` must match a row in the `sources` registry table
    (see `migrations/001_init_schema.sql`) -- that row carries the
    human-facing metadata (name, state, jurisdiction, portal type, active
    flag) this class deliberately doesn't know about. See
    `oppscanner.scrapers.registry` for how a concrete subclass gets wired
    to its `source_slug` at runtime.
    """

    def __init__(self, client_id: str, source_slug: str) -> None:
        self.client_id = client_id
        self.source_slug = source_slug

    @abstractmethod
    def fetch(self) -> Any:
        """Retrieve the raw content for this source (HTML, JSON, CSV, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def parse(self, raw: Any) -> list[dict[str, Any]]:
        """Parse raw fetched content into a list of raw record dicts."""
        raise NotImplementedError

    @abstractmethod
    def normalize(self, raw_record: dict[str, Any]) -> OpportunityRecord:
        """Convert a single raw record dict into an `OpportunityRecord`."""
        raise NotImplementedError

    def run(self) -> Iterator[OpportunityRecord]:
        """Orchestrate fetch -> parse -> normalize -> yield `OpportunityRecord` records."""
        raw = self.fetch()
        for raw_record in self.parse(raw):
            yield self.normalize(raw_record)
