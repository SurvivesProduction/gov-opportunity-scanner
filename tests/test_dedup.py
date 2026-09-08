from datetime import date

from oppscanner.normalize.dedup import compute_synthetic_external_id


def test_same_inputs_produce_the_same_hash() -> None:
    a = compute_synthetic_external_id("Example County Schools", "Electrical Panel Upgrade", date(2026, 9, 30))
    b = compute_synthetic_external_id("Example County Schools", "Electrical Panel Upgrade", date(2026, 9, 30))
    assert a == b


def test_different_inputs_produce_different_hashes() -> None:
    a = compute_synthetic_external_id("Example County Schools", "Electrical Panel Upgrade", date(2026, 9, 30))
    b = compute_synthetic_external_id("Example County Schools", "Roof Replacement", date(2026, 9, 30))
    assert a != b


def test_normalizes_case_and_whitespace_before_hashing() -> None:
    a = compute_synthetic_external_id("Example County Schools", "Electrical Panel Upgrade")
    b = compute_synthetic_external_id("  EXAMPLE   county schools ", "electrical  panel   upgrade")
    assert a == b


def test_none_and_empty_string_hash_the_same() -> None:
    a = compute_synthetic_external_id("Agency", None)
    b = compute_synthetic_external_id("Agency", "")
    assert a == b


def test_date_part_uses_iso_format() -> None:
    a = compute_synthetic_external_id("Agency", "Title", date(2026, 9, 30))
    b = compute_synthetic_external_id("Agency", "Title", "2026-09-30")
    assert a == b


def test_part_order_matters() -> None:
    a = compute_synthetic_external_id("Agency", "Title")
    b = compute_synthetic_external_id("Title", "Agency")
    assert a != b


def test_returns_a_hex_sha256_digest() -> None:
    result = compute_synthetic_external_id("Agency", "Title")
    assert len(result) == 64
    int(result, 16)  # raises ValueError if not valid hex
