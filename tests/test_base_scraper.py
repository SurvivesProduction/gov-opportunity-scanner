from typing import Any

from oppscanner.normalize.schema import OpportunityRecord
from oppscanner.scrapers.base import BaseOpportunityFetcher


class _StaticFetcher(BaseOpportunityFetcher):
    def fetch(self) -> list[dict[str, Any]]:
        return [
            {"external_id": "A-1", "title": "First"},
            {"external_id": "A-2", "title": "Second"},
        ]

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


def test_run_orchestrates_fetch_parse_normalize_in_order() -> None:
    fetcher = _StaticFetcher(client_id="demo", source_slug="static-source")
    records = list(fetcher.run())

    assert [r.external_id for r in records] == ["A-1", "A-2"]
    assert all(isinstance(r, OpportunityRecord) for r in records)
    assert all(r.client_id == "demo" and r.source_slug == "static-source" for r in records)
