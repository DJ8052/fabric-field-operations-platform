"""Unit tests for Bronze weather transformation validators."""

from __future__ import annotations

from copy import deepcopy

import pytest

from weather_transformation.validators import (
    BronzeValidationError,
    validate_bronze_record,
    validate_hourly_array_alignment,
    validate_required_fields,
)


@pytest.fixture
def valid_bronze_record() -> dict:
    """Return a minimal valid Bronze record with three forecast hours."""

    return {
        "source_system": "open_meteo",
        "endpoint_name": "weather_forecast",
        "location_id": "TX-DAL",
        "location_name": "Dallas",
        "pipeline_run_id": "test-run-001",
        "ingestion_timestamp_utc": "2026-07-14T13:03:15+00:00",
        "attempt_count": 1,
        "http_status_code": 200,
        "hourly_record_count": 3,
        "request_parameters": {
            "forecast_days": 1,
            "latitude": 32.7767,
            "longitude": -96.7970,
            "timezone": "America/Chicago",
        },
        "payload": {
            "latitude": 32.75,
            "longitude": -96.75,
            "timezone": "America/Chicago",
            "utc_offset_seconds": -18000,
            "hourly_units": {
                "time": "iso8601",
                "temperature_2m": "°F",
                "apparent_temperature": "°F",
                "relative_humidity_2m": "%",
                "precipitation": "inch",
                "weather_code": "wmo code",
                "wind_gusts_10m": "mph",
            },
            "hourly": {
                "time": [
                    "2026-07-14T00:00",
                    "2026-07-14T01:00",
                    "2026-07-14T02:00",
                ],
                "temperature_2m": [80.1, 79.5, 78.8],
                "apparent_temperature": [84.2, 83.4, 82.7],
                "relative_humidity_2m": [65, 67, 69],
                "precipitation": [0.0, 0.0, 0.01],
                "weather_code": [0, 1, 2],
                "wind_gusts_10m": [12.3, 11.8, 10.9],
            },
        },
    }


def test_validate_required_fields_accepts_valid_record(
    valid_bronze_record: dict,
) -> None:
    validate_required_fields(valid_bronze_record)


def test_validate_required_fields_rejects_missing_hourly_field(
    valid_bronze_record: dict,
) -> None:
    invalid_record = deepcopy(valid_bronze_record)

    del invalid_record["payload"]["hourly"]["precipitation"]

    with pytest.raises(
        BronzeValidationError,
        match="missing required fields",
    ):
        validate_required_fields(invalid_record)


def test_validate_hourly_array_alignment_returns_record_count(
    valid_bronze_record: dict,
) -> None:
    result = validate_hourly_array_alignment(
        valid_bronze_record
    )

    assert result == 3


def test_validate_hourly_array_alignment_rejects_misaligned_arrays(
    valid_bronze_record: dict,
) -> None:
    invalid_record = deepcopy(valid_bronze_record)

    invalid_record["payload"]["hourly"]["temperature_2m"].pop()

    with pytest.raises(
        BronzeValidationError,
        match="misaligned",
    ):
        validate_hourly_array_alignment(invalid_record)


def test_validate_hourly_array_alignment_rejects_declared_count_mismatch(
    valid_bronze_record: dict,
) -> None:
    invalid_record = deepcopy(valid_bronze_record)
    invalid_record["hourly_record_count"] = 168

    with pytest.raises(
        BronzeValidationError,
        match="does not match",
    ):
        validate_hourly_array_alignment(invalid_record)


def test_validate_bronze_record_rejects_empty_hourly_arrays(
    valid_bronze_record: dict,
) -> None:
    invalid_record = deepcopy(valid_bronze_record)

    for field_name in invalid_record["payload"]["hourly"]:
        invalid_record["payload"]["hourly"][field_name] = []

    invalid_record["hourly_record_count"] = 0

    with pytest.raises(
        BronzeValidationError,
        match="at least one",
    ):
        validate_bronze_record(invalid_record)