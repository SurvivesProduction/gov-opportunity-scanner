"""Fallback synthetic `external_id` construction, for a source with no
native stable record id.

`OpportunityRecord.external_id` is a required field, and this project's
standing precedent (see that schema's own docstring, and every real
fetcher's `normalize()`) is: if a source doesn't expose a genuine native
id, raise `ValueError` rather than inventing one -- UNLESS a stable
synthetic key can be derived from content that's guaranteed present and
distinguishing. This module exists for that second case, mirroring Tool 1
(`bidscraper.db.client.compute_record_key`)'s normalized-hash fallback --
the same construction (lowercase, collapse whitespace, join with `|`,
sha256), adapted here to a plain function a fetcher's own `normalize()`
calls directly to produce its `external_id`, rather than a DB-layer
concept: Tool 3 has no fuzzy-match tier and no `dedup_method` column (see
`oppscanner.db.client`'s docstring) for a "which tier did this land in"
distinction to live in, so unlike Tool 1's `(record_key, dedup_method)`
pair, this returns just the id string.

None of Tool 3's five real fetchers (as of 2026-09-07) need this --
Harbor, eVA, Baltimore County, DC OCP, and AACPS each expose a genuine
native id (see each module's own docstring for what it is and why it's
trusted). This exists ahead of need for the next source that doesn't.

## Before reaching for this: the id-selection lesson from Tool 2 and Tool 3's own history

Two real, opposite-shaped mistakes to check for before assuming no native
id exists or picking the wrong one:

- **A display-only field that's SOMETIMES ABSENT, used as if it were
  always present.** Tool 2's Accela permit portal (`aaco_permits.py`)
  found exactly this: a `lblPermitNumber1`-style issued permit number
  looks like a fine identifier until you notice it's simply missing on
  "unlinked" grid rows. The fetcher was written to prefer the hidden
  `RecordId` input (always present) and fall back to the display number
  only when `RecordId` is absent -- check for an equivalent hidden/
  internal id before trusting a display-formatted field as this source's
  ONLY identifier.
- **A human-facing number CAN still be the right primary choice** -- Tool
  3's own Harbor fetcher (`anne_arundel_harbor.py`) deliberately prefers
  the human-facing `Negotiation` (SOL) number over Oracle's internal
  `AuctionHeaderId`, because that's the number vendors and staff actually
  reference, falling back to the internal id (flagged) only when
  `Negotiation` is missing. Baltimore County's `financialId` (also
  human-facing) was independently confirmed always-present and unique
  across a full live pull before being trusted alone, with no fallback
  needed. The lesson isn't "always prefer the internal id" -- it's
  "confirm whichever field you pick is actually always present and
  unique before trusting it alone," and prefer a hidden/internal field
  ONLY when the human-facing one turns out not to satisfy that.

Reach for `compute_synthetic_external_id` only after confirming neither a
native id NOR a hidden/internal one exists at all.
"""
from __future__ import annotations

import hashlib
import re
from datetime import date


def _normalize_text(value: str) -> str:
    """Lowercase and collapse whitespace, for hash-based dedup comparisons.

    Identical in behavior to Tool 1's `bidscraper.db.client._normalize_text`
    -- kept as its own private copy rather than a cross-package import,
    since Tool 1 and Tool 3 are independent public packages with no shared
    dependency between them.
    """
    return re.sub(r"\s+", " ", value.strip().lower())


def compute_synthetic_external_id(*parts: str | date | None) -> str:
    """Return a stable sha256 hash of `parts`, for use as `external_id`.

    Each part is normalized (see `_normalize_text`) before joining with
    `|`; a `date` is converted via `.isoformat()`; `None` becomes an empty
    string. Order matters and must stay consistent across a given
    fetcher's own calls (e.g. always `agency, title, due_date`, never
    swapped), since a re-scrape has to reproduce the identical hash for
    the identical posting to dedup correctly -- passing fields in a
    different order (or a different combination) than a prior run used
    would silently mint a NEW `external_id` for the same real-world
    posting, splitting one opportunity into two rows.

    Callers should pick fields that are (a) always present on every real
    record from that source and (b) jointly distinguish one posting from
    another for that source specifically -- e.g. agency + title + due
    date, following Tool 1's own agency + title + vendor + award date
    choice adapted to what a bid *posting* (not yet an award) actually
    has. This function itself has no opinion on which fields make sense
    for a given source; that judgment belongs in that fetcher's own
    `normalize()` and should be documented there, the same way every real
    Tool 3 fetcher documents its `external_id` choice today.
    """
    def _part_to_text(part: str | date | None) -> str:
        if part is None:
            return ""
        if isinstance(part, date):
            return part.isoformat()
        return part

    normalized = "|".join(_normalize_text(_part_to_text(part)) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
