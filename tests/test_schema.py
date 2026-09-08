from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from oppscanner.normalize.schema import OpportunityRecord


def test_opportunity_record_accepts_full_valid_bid_record() -> None:
    record = OpportunityRecord(
        client_id="demo",
        source_slug="example-county-bids",
        external_id="BID-001",
        opportunity_type="bid",
        title="Electrical Panel Upgrade",
        description="Replace end-of-life panels.",
        status="open",
        agency="Example County Public Schools",
        address="100 Example School Rd",
        county="Example County",
        state="MD",
        posted_date=date(2026, 8, 1),
        due_date=date(2026, 9, 30),
        estimated_value=Decimal("185000.00"),
        url="https://example.gov/bids/BID-001",
        raw_data={"id": "BID-001"},
    )
    assert record.opportunity_type == "bid"
    assert record.estimated_value == Decimal("185000.00")
    assert record.needs_review is False
    assert record.review_reason is None
    assert record.jurisdiction is None


def test_opportunity_record_accepts_a_jurisdiction_distinct_from_agency() -> None:
    record = OpportunityRecord(
        client_id="demo",
        source_slug="example-state-bids",
        external_id="BID-003",
        opportunity_type="bid",
        title="Statewide Lighting Retrofit RFP",
        agency="Department of General Services",
        jurisdiction="Example County, EX",
    )
    assert record.agency == "Department of General Services"
    assert record.jurisdiction == "Example County, EX"


def test_opportunity_record_accepts_a_named_contact_distinct_from_agency() -> None:
    record = OpportunityRecord(
        client_id="demo",
        source_slug="example-district-bids",
        external_id="BID-004",
        opportunity_type="bid",
        title="Facilities Maintenance RFP",
        agency="Department of General Services",
        contact_name="Jane Smith",
        contact_email="jane.smith@example.gov",
        contact_phone="(202) 555-0100",
    )
    assert record.agency == "Department of General Services"
    assert record.contact_name == "Jane Smith"
    assert record.contact_email == "jane.smith@example.gov"
    assert record.contact_phone == "(202) 555-0100"


def test_opportunity_record_allows_optional_fields_to_be_omitted() -> None:
    record = OpportunityRecord(
        client_id="demo",
        source_slug="example-city-permits",
        external_id="PM-001",
        opportunity_type="permit",
        title="Commercial Electrical Permit",
    )
    assert record.due_date is None
    assert record.estimated_value is None
    assert record.raw_data == {}
    assert record.contact_name is None


def test_opportunity_record_requires_core_fields() -> None:
    with pytest.raises(ValidationError):
        OpportunityRecord(client_id="demo", source_slug="example-city-permits")


def test_opportunity_record_accepts_needs_review_flag_with_reason() -> None:
    record = OpportunityRecord(
        client_id="demo",
        source_slug="example-county-bids",
        external_id="BID-002",
        opportunity_type="bid",
        title="Unclear Posting",
        needs_review=True,
        review_reason="missing due date",
    )
    assert record.needs_review is True
    assert record.review_reason == "missing due date"


def test_opportunity_record_rejects_unknown_opportunity_type() -> None:
    with pytest.raises(ValidationError):
        OpportunityRecord(
            client_id="demo",
            source_slug="example-city-permits",
            external_id="PM-001",
            opportunity_type="rfp",
            title="Something",
        )
