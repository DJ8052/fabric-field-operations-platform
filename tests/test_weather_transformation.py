"""Unit tests for Bronze weather transformation utilities."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import MagicMock

import pytest

from weather_transformation.bronze_reader import (
    BronzeReadError,
    read_bronze_weather,
)
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


def _build_mock_spark(
    *,
    record_count: int = 1,
) -> tuple[MagicMock, MagicMock]:
    """Return mocked SparkSession and DataFrame objects."""

    spark = MagicMock()
    bronze_df = MagicMock()

    spark.read.option.return_value = spark.read
    spark.read.json.return_value = bronze_df
    bronze_df.count.return_value = record_count

    return spark, bronze_df


def test_validate_required_fields_accepts_valid_record(
    valid_bronze_record: dict,
) -> None:
    """A complete Bronze record should pass structural validation."""

    validate_required_fields(valid_bronze_record)


def test_validate_required_fields_rejects_missing_hourly_field(
    valid_bronze_record: dict,
) -> None:
    """A missing required hourly measurement should fail validation."""

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
    """Aligned arrays should return their validated forecast-record count."""

    result = validate_hourly_array_alignment(valid_bronze_record)

    assert result == 3


def test_validate_hourly_array_alignment_rejects_misaligned_arrays(
    valid_bronze_record: dict,
) -> None:
    """Hourly arrays with unequal lengths should fail validation."""

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
    """The declared record count must equal the actual hourly-array length."""

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
    """Bronze records with no hourly forecasts should fail validation."""

    invalid_record = deepcopy(valid_bronze_record)

    for field_name in invalid_record["payload"]["hourly"]:
        invalid_record["payload"]["hourly"][field_name] = []

    invalid_record["hourly_record_count"] = 0

    with pytest.raises(
        BronzeValidationError,
        match="at least one",
    ):
        validate_bronze_record(invalid_record)


def test_read_bronze_weather_returns_dataframe() -> None:
    """The reader should return the DataFrame produced by Spark."""

    spark, bronze_df = _build_mock_spark(record_count=3)

    result = read_bronze_weather(spark)

    assert result is bronze_df

    spark.read.option.assert_any_call(
        "recursiveFileLookup",
        "true",
    )
    spark.read.option.assert_any_call(
        "multiline",
        "true",
    )
    spark.read.json.assert_called_once_with(
        "Files/bronze/weather_forecast"
    )
    bronze_df.count.assert_called_once_with()


def test_read_bronze_weather_accepts_custom_path() -> None:
    """The reader should support a caller-supplied Bronze root path."""

    spark, _ = _build_mock_spark(record_count=2)

    read_bronze_weather(
        spark,
        "Files/bronze/custom_weather",
    )

    spark.read.json.assert_called_once_with(
        "Files/bronze/custom_weather"
    )


def test_read_bronze_weather_trims_custom_path() -> None:
    """Leading and trailing whitespace should be removed from the path."""

    spark, _ = _build_mock_spark(record_count=2)

    read_bronze_weather(
        spark,
        "  Files/bronze/custom_weather  ",
    )

    spark.read.json.assert_called_once_with(
        "Files/bronze/custom_weather"
    )


def test_read_bronze_weather_rejects_blank_path() -> None:
    """A blank Bronze root path should fail before Spark is called."""

    spark, _ = _build_mock_spark()

    with pytest.raises(
        BronzeReadError,
        match="cannot be blank",
    ):
        read_bronze_weather(
            spark,
            "   ",
        )

    spark.read.json.assert_not_called()


def test_read_bronze_weather_rejects_non_string_path() -> None:
    """A non-string Bronze path should fail with a descriptive error."""

    spark, _ = _build_mock_spark()

    with pytest.raises(
        BronzeReadError,
        match="must be provided as a string",
    ):
        read_bronze_weather(
            spark,
            None,  # type: ignore[arg-type]
        )

    spark.read.json.assert_not_called()


def test_read_bronze_weather_rejects_empty_dataset() -> None:
    """A successfully read but empty Bronze dataset should fail."""

    spark, _ = _build_mock_spark(record_count=0)

    with pytest.raises(
        BronzeReadError,
        match="No Bronze weather records",
    ):
        read_bronze_weather(spark)


def test_read_bronze_weather_wraps_spark_read_error() -> None:
    """Spark read failures should be wrapped in BronzeReadError."""

    spark = MagicMock()
    spark.read.option.return_value = spark.read
    spark.read.json.side_effect = RuntimeError(
        "Simulated Spark failure"
    )

    with pytest.raises(
        BronzeReadError,
        match="Unable to read Bronze weather JSON",
    ):
        read_bronze_weather(spark)


def test_read_bronze_weather_wraps_count_error() -> None:
    """DataFrame evaluation failures should be wrapped clearly."""

    spark, bronze_df = _build_mock_spark()
    bronze_df.count.side_effect = RuntimeError(
        "Simulated count failure"
    )

    with pytest.raises(
        BronzeReadError,
        match="record count could not be evaluated",
    ):
        read_bronze_weather(spark)