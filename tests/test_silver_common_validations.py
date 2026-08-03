from __future__ import annotations

from decimal import Decimal

from operational_silver_validation.common_validations import (
    decimal_equal,
    duplicate_groups,
    invalid_domain_indices,
    invalid_foreign_key_indices,
    is_missing,
    missing_indices,
    parse_iso_date,
    parse_iso_timestamp,
)


def test_required_values_distinguish_empty_from_whitespace() -> None:
    assert is_missing(None)
    assert is_missing("")
    assert not is_missing("   ")
    assert missing_indices([{"code": None}, {"code": ""}, {"code": " "}], "code") == (0, 1)


def test_duplicates_mark_every_participant() -> None:
    rows = [{"code": "A"}, {"code": "B"}, {"code": "A"}, {"code": "A"}]
    assert duplicate_groups(rows, "code") == ((0, 2, 3),)


def test_foreign_keys_support_required_and_conditional_values() -> None:
    rows = [{"office_id": 1}, {"office_id": 9}, {"office_id": ""}]
    assert invalid_foreign_key_indices(rows, "office_id", {1, 2}) == (1, 2)
    assert invalid_foreign_key_indices(rows, "office_id", {1, 2}, nullable=True) == (1,)


def test_controlled_domain_is_exact() -> None:
    rows = [{"status": "Active"}, {"status": "active"}, {"status": ""}]
    assert invalid_domain_indices(rows, "status", {"Active"}) == (1, 2)


def test_numeric_comparison_uses_documented_tolerance() -> None:
    assert decimal_equal("8.0000004", 8)
    assert not decimal_equal("8.000002", 8)
    assert decimal_equal(0.1 + 0.2, Decimal("0.3"))
    assert not decimal_equal("not-a-number", 1)


def test_iso_parsers_reject_malformed_values_without_conversion() -> None:
    assert parse_iso_timestamp("2026-02-01T07:00:00").isoformat() == "2026-02-01T07:00:00"
    assert parse_iso_timestamp("02/01/2026 07:00") is None
    assert parse_iso_date("2026-02-01").isoformat() == "2026-02-01"
    assert parse_iso_date("02/01/2026") is None

