"""Bronze-to-Silver weather record transformation utilities.

This module converts one validated Bronze weather JSON record into relational
hourly Silver records.

The transformation is framework-independent so it can be tested locally
without requiring a Microsoft Fabric Spark session. The Fabric notebook will
later convert the returned records into a Spark DataFrame.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from weather_transformation.validators import validate_bronze_record


class WeatherTransformationError(ValueError):
    """Raised when a Bronze record cannot be transformed into Silver rows."""


def _parse_timestamp(
    value: Any,
    field_name: str,
) -> datetime:
    """Parse an ISO-8601 timestamp into a Python datetime."""

    if not isinstance(value, str) or not value.strip():
        raise WeatherTransformationError(
            f"'{field_name}' must be a non-empty ISO-8601 string."
        )

    normalized_value = value.strip()

    if normalized_value.endswith("Z"):
        normalized_value = (
            normalized_value[:-1]
            + "+00:00"
        )

    try:
        return datetime.fromisoformat(normalized_value)
    except ValueError as exc:
        raise WeatherTransformationError(
            f"'{field_name}' contains an invalid ISO-8601 timestamp: "
            f"{value!r}."
        ) from exc


def _to_int(
    value: Any,
    field_name: str,
) -> int:
    """Convert a source value to integer or raise a descriptive error."""

    if isinstance(value, bool):
        raise WeatherTransformationError(
            f"'{field_name}' cannot be a Boolean value."
        )

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise WeatherTransformationError(
            f"'{field_name}' could not be converted to integer: "
            f"{value!r}."
        ) from exc


def _to_float_or_none(
    value: Any,
    field_name: str,
) -> float | None:
    """Convert an optional source value to float."""

    if value is None:
        return None

    if isinstance(value, bool):
        raise WeatherTransformationError(
            f"'{field_name}' cannot be a Boolean value."
        )

    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WeatherTransformationError(
            f"'{field_name}' could not be converted to float: "
            f"{value!r}."
        ) from exc


def _to_int_or_none(
    value: Any,
    field_name: str,
) -> int | None:
    """Convert an optional source value to integer."""

    if value is None:
        return None

    return _to_int(
        value,
        field_name,
    )


def transform_bronze_record(
    record: dict[str, Any],
) -> list[dict[str, Any]]:
    """Convert one Bronze weather record into hourly Silver records.

    Parameters
    ----------
    record:
        One validated Bronze weather JSON record.

    Returns
    -------
    list[dict[str, Any]]
        One relational Silver record for every hourly forecast position.

    Raises
    ------
    WeatherTransformationError
        If timestamps or numeric values cannot be converted.
    BronzeValidationError
        If the Bronze structural contract is invalid.
    """

    hourly_record_count = validate_bronze_record(record)

    payload = record["payload"]
    hourly = payload["hourly"]
    hourly_units = payload["hourly_units"]
    request_parameters = record["request_parameters"]

    ingestion_timestamp_utc = _parse_timestamp(
        record["ingestion_timestamp_utc"],
        "ingestion_timestamp_utc",
    )

    silver_rows: list[dict[str, Any]] = []

    for hour_index in range(hourly_record_count):
        forecast_timestamp_local = _parse_timestamp(
            hourly["time"][hour_index],
            (
                "payload.hourly.time"
                f"[{hour_index}]"
            ),
        )

        silver_rows.append(
            {
                "pipeline_run_id": str(
                    record["pipeline_run_id"]
                ),
                "source_system": str(
                    record["source_system"]
                ),
                "endpoint_name": str(
                    record["endpoint_name"]
                ),
                "location_id": str(
                    record["location_id"]
                ),
                "location_name": str(
                    record["location_name"]
                ),
                "ingestion_timestamp_utc": (
                    ingestion_timestamp_utc
                ),
                "forecast_timestamp_local": (
                    forecast_timestamp_local
                ),
                "forecast_hour_index": hour_index,
                "temperature_2m": _to_float_or_none(
                    hourly["temperature_2m"][hour_index],
                    (
                        "payload.hourly.temperature_2m"
                        f"[{hour_index}]"
                    ),
                ),
                "apparent_temperature": _to_float_or_none(
                    hourly["apparent_temperature"][hour_index],
                    (
                        "payload.hourly.apparent_temperature"
                        f"[{hour_index}]"
                    ),
                ),
                "relative_humidity_2m": _to_int_or_none(
                    hourly["relative_humidity_2m"][hour_index],
                    (
                        "payload.hourly.relative_humidity_2m"
                        f"[{hour_index}]"
                    ),
                ),
                "precipitation": _to_float_or_none(
                    hourly["precipitation"][hour_index],
                    (
                        "payload.hourly.precipitation"
                        f"[{hour_index}]"
                    ),
                ),
                "weather_code": _to_int_or_none(
                    hourly["weather_code"][hour_index],
                    (
                        "payload.hourly.weather_code"
                        f"[{hour_index}]"
                    ),
                ),
                "wind_gusts_10m": _to_float_or_none(
                    hourly["wind_gusts_10m"][hour_index],
                    (
                        "payload.hourly.wind_gusts_10m"
                        f"[{hour_index}]"
                    ),
                ),
                "latitude": _to_float_or_none(
                    payload["latitude"],
                    "payload.latitude",
                ),
                "longitude": _to_float_or_none(
                    payload["longitude"],
                    "payload.longitude",
                ),
                "elevation": _to_float_or_none(
                    payload.get("elevation"),
                    "payload.elevation",
                ),
                "timezone": str(
                    payload["timezone"]
                ),
                "timezone_abbreviation": (
                    str(payload["timezone_abbreviation"])
                    if payload.get(
                        "timezone_abbreviation"
                    ) is not None
                    else None
                ),
                "utc_offset_seconds": _to_int(
                    payload["utc_offset_seconds"],
                    "payload.utc_offset_seconds",
                ),
                "temperature_unit": str(
                    hourly_units["temperature_2m"]
                ),
                "apparent_temperature_unit": str(
                    hourly_units["apparent_temperature"]
                ),
                "relative_humidity_unit": str(
                    hourly_units["relative_humidity_2m"]
                ),
                "precipitation_unit": str(
                    hourly_units["precipitation"]
                ),
                "weather_code_unit": str(
                    hourly_units["weather_code"]
                ),
                "wind_gust_unit": str(
                    hourly_units["wind_gusts_10m"]
                ),
                "forecast_days": _to_int(
                    request_parameters["forecast_days"],
                    "request_parameters.forecast_days",
                ),
                "attempt_count": _to_int(
                    record["attempt_count"],
                    "attempt_count",
                ),
                "http_status_code": _to_int(
                    record["http_status_code"],
                    "http_status_code",
                ),
            }
        )

    return silver_rows


def transform_bronze_records(
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Transform multiple Bronze records into one Silver row collection."""

    if not isinstance(records, list):
        raise WeatherTransformationError(
            "Bronze records must be provided as a list."
        )

    if not records:
        raise WeatherTransformationError(
            "At least one Bronze record is required."
        )

    silver_rows: list[dict[str, Any]] = []

    for record in records:
        silver_rows.extend(
            transform_bronze_record(record)
        )

    return silver_rows