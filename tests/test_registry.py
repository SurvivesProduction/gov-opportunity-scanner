from typing import Any

import pytest

from oppscanner.normalize.schema import OpportunityRecord
from oppscanner.scrapers import registry
from oppscanner.scrapers.base import BaseOpportunityFetcher


class _FakeFetcher(BaseOpportunityFetcher):
    def fetch(self) -> list[dict[str, Any]]:
        return [{"external_id": "X-1", "title": "Fake"}]

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


@pytest.fixture(autouse=True)
def _clean_registry():
    registry._clear_registry_for_tests()
    yield
    registry._clear_registry_for_tests()


def test_register_fetcher_makes_it_resolvable_by_slug() -> None:
    registry.register_fetcher("test-slug")(_FakeFetcher)
    assert registry.get_fetcher_class("test-slug") is _FakeFetcher
    assert "test-slug" in registry.registered_source_slugs()


def test_get_fetcher_class_raises_for_unregistered_slug() -> None:
    with pytest.raises(KeyError):
        registry.get_fetcher_class("nonexistent-slug")


def test_register_fetcher_rejects_conflicting_duplicate_slug() -> None:
    registry.register_fetcher("dup-slug")(_FakeFetcher)

    class _OtherFetcher(_FakeFetcher):
        pass

    with pytest.raises(ValueError):
        registry.register_fetcher("dup-slug")(_OtherFetcher)


def test_register_fetcher_allows_reregistering_the_same_class() -> None:
    registry.register_fetcher("same-class-slug")(_FakeFetcher)
    # Re-decorating the identical class (e.g. module reimported) should
    # not raise -- only a genuine conflicting registration should.
    registry.register_fetcher("same-class-slug")(_FakeFetcher)
