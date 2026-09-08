"""The normalized output contract every fetcher must produce.

One schema, not one per source type: unlike Tool 2 (which cross-
references two genuinely different record types, property assessments
and permits), Tool 3's bid postings and permit postings -- across every
jurisdiction -- all resolve to the same "here is a posted opportunity"
shape. `opportunity_type` is what a downstream reader uses to tell them
apart, not a different class. If a real source's fields turn out to
diverge enough that this stops holding, that's a reason to revisit this
decision once real data is in hand, not to force-fit it now.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class OpportunityRecord(BaseModel):
    """A normalized government bid or permit opportunity record.

    `client_id` and `source_slug` are two independent axes, deliberately
    kept separate: `client_id` is data ownership (which client's
    dashboard this belongs to), `source_slug` is which portal/geography
    this record came from (a foreign key into the `sources` registry
    table -- see `migrations/001_init_schema.sql`). Conflating the two
    would make it impossible for a future second client to also
    reference a source an earlier client already uses without
    duplicating rows.

    `external_id` is required: like Tool 2's permit/parcel numbers,
    government bid and permit postings are virtually always issued with
    a genuine stable reference number by the source itself, so this
    schema assumes one exists and dedups on it directly (see
    `oppscanner.db.client.upsert_opportunity`). If a real source turns
    out not to expose one, that's a reason to revisit this assumption
    before wiring up that source, not to fake an id.

    `needs_review`/`review_reason` are first-class fields here, unlike
    Tool 1's `BidAward` (which deliberately excludes `needs_review` --
    see that schema's docstring) -- Tool 1's flag is computed by the DB
    layer from fuzzy-dedup match confidence, a fact `BidAward` itself
    can't know. Tool 3 has no fuzzy-dedup tier (exact-key upsert only,
    see `upsert_opportunity`'s docstring), so the only source of
    review-worthiness here is a fetcher's own extraction confidence
    (e.g. a required field it couldn't cleanly parse) -- something the
    fetcher's `normalize()` step already knows when it builds this
    record, so there's no reason to smuggle it through `raw_data` for a
    later layer to re-derive.

    `jurisdiction` is a separate axis from `agency`/`county`/`state`,
    added once a real source (Virginia's eVA, a single statewide
    aggregator feed spanning counties, cities, towns, authorities, and
    genuine state agencies all in one `source_slug`) made the gap
    concrete: `county`/`state` alone can't express "the specific buying
    entity for this one record" when that entity isn't reliably a county
    at all, and forcing every shape into the `county` column would
    misuse it. `agency` remains "who do I contact" (may be a department
    within a jurisdiction, not the jurisdiction itself); `jurisdiction`
    is "which government body this posting belongs to," e.g. "Henrico
    County, VA" or "Norfolk Airport Authority, VA" -- for a
    single-jurisdiction source like Anne Arundel County's Harbor fetcher
    the two values happen to coincide, which is fine, they're still
    tracked separately since that's a coincidence of that source, not a
    general rule.

    `contact_name`/`contact_email`/`contact_phone` are first-class fields,
    added once a real source (Washington DC's OCP Contracts and
    Procurement Transparency Portal) made a named human contact -- not
    just a department name/inbox the way Harbor's `BuyerName`/
    `BuyerEmailAddress` or eVA's `buyername` are -- a genuine per-record
    data point rather than something to bury in `raw_data`. `agency`
    remains "which department/office," these three are "which specific
    person"; a source that only has the weaker department-level contact
    (Harbor, eVA) has no reason to populate these and leaves them `None`
    rather than duplicating `agency` into `contact_name`.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: str
    source_slug: str
    external_id: str
    opportunity_type: Literal["bid", "permit"]
    title: str
    description: str | None = None
    status: str | None = None
    agency: str | None = None
    address: str | None = None
    county: str | None = None
    state: str | None = None
    jurisdiction: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    posted_date: date | None = None
    due_date: date | None = None
    estimated_value: Decimal | None = None
    url: str | None = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    needs_review: bool = False
    review_reason: str | None = None
