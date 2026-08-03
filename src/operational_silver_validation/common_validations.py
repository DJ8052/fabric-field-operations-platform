"""Reusable deterministic validation primitives with no Fabric dependency."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable, Mapping, Sequence

NUMERIC_ABSOLUTE_TOLERANCE = Decimal("0.000001")


def is_missing(value: Any) -> bool:
    """Treat only null and exact empty string as missing; never trim source text."""
    return value is None or value == ""


def missing_indices(records: Sequence[Mapping[str, Any]], field: str) -> tuple[int, ...]:
    return tuple(index for index, record in enumerate(records) if is_missing(record.get(field)))


def duplicate_groups(records: Sequence[Mapping[str, Any]], field: str) -> tuple[tuple[int, ...], ...]:
    groups: dict[Any, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        value = record.get(field)
        if not is_missing(value):
            groups[value].append(index)
    return tuple(tuple(indices) for indices in groups.values() if len(indices) > 1)


def invalid_domain_indices(records: Sequence[Mapping[str, Any]], field: str, allowed: Iterable[Any]) -> tuple[int, ...]:
    domain = frozenset(allowed)
    return tuple(index for index, record in enumerate(records) if record.get(field) not in domain)


def invalid_foreign_key_indices(records: Sequence[Mapping[str, Any]], field: str, referenced_values: Iterable[Any], *, nullable: bool = False) -> tuple[int, ...]:
    valid = frozenset(referenced_values)
    return tuple(
        index
        for index, record in enumerate(records)
        if not (nullable and is_missing(record.get(field))) and record.get(field) not in valid
    )


def parse_iso_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or is_missing(value):
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_iso_date(value: Any) -> date | None:
    if not isinstance(value, str) or is_missing(value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def decimal_equal(left: Any, right: Any, *, tolerance: Decimal = NUMERIC_ABSOLUTE_TOLERANCE) -> bool:
    try:
        left_decimal = Decimal(str(left))
        right_decimal = Decimal(str(right))
    except (InvalidOperation, ValueError, TypeError):
        return False
    return abs(left_decimal - right_decimal) <= tolerance


def parse_decimal(value: Any) -> Decimal | None:
    """Parse a finite decimal without changing the source value."""
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return parsed if parsed.is_finite() else None
