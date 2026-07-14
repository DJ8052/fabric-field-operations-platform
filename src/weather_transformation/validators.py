"""Validation utilities for Bronze-to-Silver weather transformations.

The functions in this module validate the structural contract of a single
Bronze weather record before it is flattened into hourly Silver rows.

These validators are deliberately framework-independent so they can be tested
locally with pytest without requiring a live Microsoft Fabric Spark session.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS: tuple[str, ...] = (
    "source_system",
    "endpoint_name",
    "location_id",
    "location_name",
    "pipeline_run_id",
    "ingestion_timestamp_utc",
    "attempt_count",
    "http_status_code",
    "hourly_record_count",
    "request_parameters",
    "payload",
)

REQUIRED_PAYLOAD_FIELDS: tuple[str, ...] = (
    "latitude",
    "longitude",
    "timezone",
    "utc_offset_seconds",
    "hourly_units",
    "hourly",
)

REQUIRED_HOURLY_FIELDS: tuple[str, ...] = (
    "time",
    "temperature_2m",
    "apparent_temperature",
    "relative_humidity_2m",
    "precipitation",
    "weather_code",
    "wind_gusts_10m",
)


class BronzeValidationError(ValueError):
    """Raised when a Bronze weather record violates the Silver data contract."""


def _require_mapping(
    value: Any,
    field_name: str,
) -> Mapping[str, Any]:
    """Return a mapping or raise a descriptive validation error."""

    if not isinstance(value, Mapping):
        raise BronzeValidationError(
            f"Expected '{field_name}' to be an object, "
            f"but received {type(value).__name__}."
        )

    return value


def _missing_fields(
    record: Mapping[str, Any],
    required_fields: Sequence[str],
) -> list[str]:
    """Return required fields that are absent from a mapping."""

    return sorted(
        field
        for field in required_fields
        if field not in record
    )


def validate_required_fields(
    record: Mapping[str, Any],
) -> None:
    """Validate required top-level, payload, and hourly fields.

    Parameters
    ----------
    record:
        One raw Bronze weather record loaded from JSON.

    Raises
    ------
    BronzeValidationError
        If required fields are missing or nested objects have invalid types.
    """

    top_level_missing = _missing_fields(
        record,
        REQUIRED_TOP_LEVEL_FIELDS,
    )

    if top_level_missing:
        raise BronzeValidationError(
            "Bronze record is missing required top-level fields: "
            f"{top_level_missing}"
        )

    payload = _require_mapping(
        record["payload"],
        "payload",
    )

    payload_missing = _missing_fields(
        payload,
        REQUIRED_PAYLOAD_FIELDS,
    )

    if payload_missing:
        raise BronzeValidationError(
            "Bronze payload is missing required fields: "
            f"{payload_missing}"
        )

    hourly = _require_mapping(
        payload["hourly"],
        "payload.hourly",
    )

    hourly_missing = _missing_fields(
        hourly,
        REQUIRED_HOURLY_FIELDS,
    )

    if hourly_missing:
        raise BronzeValidationError(
            "Bronze hourly payload is missing required fields: "
            f"{hourly_missing}"
        )


def validate_hourly_array_alignment(
    record: Mapping[str, Any],
) -> int:
    """Validate that every hourly array has the same number of elements.

    Each array position represents the same forecast hour. Any difference in
    array lengths would cause measurements to be paired with the wrong
    timestamp during the Silver transformation.

    Parameters
    ----------
    record:
        One raw Bronze weather record loaded from JSON.

    Returns
    -------
    int
        The validated number of hourly forecast records.

    Raises
    ------
    BronzeValidationError
        If an hourly value is not an array, arrays are empty, array lengths
        differ, or ``hourly_record_count`` disagrees with the actual length.
    """

    validate_required_fields(record)

    payload = _require_mapping(
        record["payload"],
        "payload",
    )

    hourly = _require_mapping(
        payload["hourly"],
        "payload.hourly",
    )

    array_lengths: dict[str, int] = {}

    for field_name in REQUIRED_HOURLY_FIELDS:
        values = hourly[field_name]

        if (
            not isinstance(values, Sequence)
            or isinstance(values, (str, bytes))
        ):
            raise BronzeValidationError(
                f"Expected 'payload.hourly.{field_name}' to be an array."
            )

        array_lengths[field_name] = len(values)

    time_count = array_lengths["time"]

    if time_count == 0:
        raise BronzeValidationError(
            "Bronze hourly arrays must contain at least one forecast record."
        )

    misaligned_fields = {
        field_name: field_count
        for field_name, field_count in array_lengths.items()
        if field_count != time_count
    }

    if misaligned_fields:
        raise BronzeValidationError(
            "Bronze hourly arrays are misaligned. "
            f"Expected {time_count} elements based on 'time'; "
            f"received {misaligned_fields}."
        )

    declared_count = record["hourly_record_count"]

    if not isinstance(declared_count, int):
        raise BronzeValidationError(
            "'hourly_record_count' must be an integer."
        )

    if declared_count != time_count:
        raise BronzeValidationError(
            "'hourly_record_count' does not match the actual hourly "
            f"array length. Declared={declared_count}, actual={time_count}."
        )

    return time_count


def validate_bronze_record(
    record: Mapping[str, Any],
) -> int:
    """Run the complete structural validation for one Bronze record.

    Returns the validated hourly record count when all checks pass.
    """

    return validate_hourly_array_alignment(record)