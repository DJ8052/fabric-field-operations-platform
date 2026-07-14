"""Unit tests for Bronze weather transformation utilities."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from weather_transformation.bronze_reader import (
    BronzeReadError,
    read_bronze_weather,
)
from weather_transformation.transformer import (
    WeatherTransformationError,
    transform_bronze_record,
    transform_bronze_records,
)
from weather_transformation.validators import (
    BronzeValidationError,
    validate_bronze_record,
    validate_hourly_array_alignment,
    validate_required_fields,
)


# =============================================================================
# SHARED TEST FIXTURES
# =============================================================================


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
            "hourly": (
                "temperature_2m,apparent_temperature,"
                "relative_humidity_2m,precipitation,"
                "weather_code,wind_gusts_10m"
            ),
            "latitude": 32.7767,
            "longitude": -96.7970,
            "precipitation_unit": "inch",
            "temperature_unit": "fahrenheit",
            "timeformat": "iso8601",
            "timezone": "America/Chicago",
            "wind_speed_unit": "mph",
        },
        "payload": {
            "latitude": 32.75,
            "longitude": -96.75,
            "elevation": 131.0,
            "generationtime_ms": 0.214,
            "timezone": "America/Chicago",
            "timezone_abbreviation": "GMT-5",
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


# =============================================================================
# VALIDATOR TESTS
# =============================================================================


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


# =============================================================================
# BRONZE READER TESTS
# =============================================================================


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


# =============================================================================
# TRANSFORMER TESTS
# =============================================================================


def test_transform_bronze_record_returns_one_row_per_hour(
    valid_bronze_record: dict,
) -> None:
    """Three aligned hourly values should produce three Silver rows."""

    result = transform_bronze_record(valid_bronze_record)

    assert len(result) == 3


def test_transform_bronze_record_preserves_logical_key(
    valid_bronze_record: dict,
) -> None:
    """Each row should preserve run, location, and forecast timestamp."""

    result = transform_bronze_record(valid_bronze_record)

    first_row = result[0]

    assert first_row["pipeline_run_id"] == "test-run-001"
    assert first_row["location_id"] == "TX-DAL"
    assert first_row["location_name"] == "Dallas"
    assert first_row["forecast_timestamp_local"] == datetime(
        2026,
        7,
        14,
        0,
        0,
    )


def test_transform_bronze_record_maps_hourly_values_by_position(
    valid_bronze_record: dict,
) -> None:
    """Measurements at the same index should remain aligned."""

    result = transform_bronze_record(valid_bronze_record)

    second_row = result[1]

    assert second_row["forecast_hour_index"] == 1
    assert second_row["temperature_2m"] == 79.5
    assert second_row["apparent_temperature"] == 83.4
    assert second_row["relative_humidity_2m"] == 67
    assert second_row["precipitation"] == 0.0
    assert second_row["weather_code"] == 1
    assert second_row["wind_gusts_10m"] == 11.8


def test_transform_bronze_record_preserves_metadata(
    valid_bronze_record: dict,
) -> None:
    """Silver rows should retain lineage, location, units, and API metadata."""

    result = transform_bronze_record(valid_bronze_record)

    first_row = result[0]

    assert first_row["source_system"] == "open_meteo"
    assert first_row["endpoint_name"] == "weather_forecast"
    assert first_row["latitude"] == 32.75
    assert first_row["longitude"] == -96.75
    assert first_row["elevation"] == 131.0
    assert first_row["timezone"] == "America/Chicago"
    assert first_row["timezone_abbreviation"] == "GMT-5"
    assert first_row["utc_offset_seconds"] == -18000
    assert first_row["temperature_unit"] == "°F"
    assert first_row["apparent_temperature_unit"] == "°F"
    assert first_row["relative_humidity_unit"] == "%"
    assert first_row["precipitation_unit"] == "inch"
    assert first_row["weather_code_unit"] == "wmo code"
    assert first_row["wind_gust_unit"] == "mph"
    assert first_row["forecast_days"] == 1
    assert first_row["attempt_count"] == 1
    assert first_row["http_status_code"] == 200


def test_transform_bronze_record_parses_ingestion_timestamp(
    valid_bronze_record: dict,
) -> None:
    """The UTC ingestion string should become a timezone-aware datetime."""

    result = transform_bronze_record(valid_bronze_record)

    assert result[0]["ingestion_timestamp_utc"] == datetime(
        2026,
        7,
        14,
        13,
        3,
        15,
        tzinfo=timezone.utc,
    )


def test_transform_bronze_record_accepts_zulu_timestamp(
    valid_bronze_record: dict,
) -> None:
    """A trailing Z should be normalized to UTC."""

    record = deepcopy(valid_bronze_record)
    record["ingestion_timestamp_utc"] = "2026-07-14T13:03:15Z"

    result = transform_bronze_record(record)

    assert result[0]["ingestion_timestamp_utc"] == datetime(
        2026,
        7,
        14,
        13,
        3,
        15,
        tzinfo=timezone.utc,
    )


def test_transform_bronze_record_allows_nullable_measurements(
    valid_bronze_record: dict,
) -> None:
    """Nullable Silver measurements should remain None when absent."""

    record = deepcopy(valid_bronze_record)

    record["payload"]["hourly"]["temperature_2m"][0] = None
    record["payload"]["hourly"]["weather_code"][0] = None
    record["payload"]["elevation"] = None

    result = transform_bronze_record(record)

    assert result[0]["temperature_2m"] is None
    assert result[0]["weather_code"] is None
    assert result[0]["elevation"] is None


def test_transform_bronze_record_rejects_invalid_ingestion_timestamp(
    valid_bronze_record: dict,
) -> None:
    """Invalid ingestion timestamps should fail with a clear message."""

    record = deepcopy(valid_bronze_record)
    record["ingestion_timestamp_utc"] = "not-a-timestamp"

    with pytest.raises(
        WeatherTransformationError,
        match="invalid ISO-8601 timestamp",
    ):
        transform_bronze_record(record)


def test_transform_bronze_record_rejects_invalid_forecast_timestamp(
    valid_bronze_record: dict,
) -> None:
    """Invalid hourly forecast timestamps should fail transformation."""

    record = deepcopy(valid_bronze_record)
    record["payload"]["hourly"]["time"][1] = "invalid-hour"

    with pytest.raises(
        WeatherTransformationError,
        match="payload.hourly.time",
    ):
        transform_bronze_record(record)


def test_transform_bronze_record_rejects_invalid_numeric_value(
    valid_bronze_record: dict,
) -> None:
    """A nonnumeric weather measurement should fail conversion."""

    record = deepcopy(valid_bronze_record)
    record["payload"]["hourly"]["temperature_2m"][0] = "hot"

    with pytest.raises(
        WeatherTransformationError,
        match="could not be converted to float",
    ):
        transform_bronze_record(record)


def test_transform_bronze_record_rejects_boolean_numeric_value(
    valid_bronze_record: dict,
) -> None:
    """Boolean values should not be accepted as numeric measurements."""

    record = deepcopy(valid_bronze_record)
    record["payload"]["hourly"]["weather_code"][0] = True

    with pytest.raises(
        WeatherTransformationError,
        match="cannot be a Boolean value",
    ):
        transform_bronze_record(record)


def test_transform_bronze_record_propagates_validation_error(
    valid_bronze_record: dict,
) -> None:
    """Structurally invalid Bronze records should fail before transformation."""

    record = deepcopy(valid_bronze_record)
    record["payload"]["hourly"]["wind_gusts_10m"].pop()

    with pytest.raises(
        BronzeValidationError,
        match="misaligned",
    ):
        transform_bronze_record(record)


def test_transform_bronze_records_combines_multiple_records(
    valid_bronze_record: dict,
) -> None:
    """Multiple Bronze records should produce one combined Silver collection."""

    dallas_record = deepcopy(valid_bronze_record)

    houston_record = deepcopy(valid_bronze_record)
    houston_record["location_id"] = "TX-HOU"
    houston_record["location_name"] = "Houston"
    houston_record["pipeline_run_id"] = "test-run-002"

    result = transform_bronze_records(
        [
            dallas_record,
            houston_record,
        ]
    )

    assert len(result) == 6

    location_ids = {
        row["location_id"]
        for row in result
    }

    assert location_ids == {
        "TX-DAL",
        "TX-HOU",
    }


def test_transform_bronze_records_preserves_input_order(
    valid_bronze_record: dict,
) -> None:
    """Rows should remain grouped in the order of input Bronze records."""

    dallas_record = deepcopy(valid_bronze_record)

    houston_record = deepcopy(valid_bronze_record)
    houston_record["location_id"] = "TX-HOU"
    houston_record["location_name"] = "Houston"

    result = transform_bronze_records(
        [
            dallas_record,
            houston_record,
        ]
    )

    assert [
        row["location_id"]
        for row in result
    ] == [
        "TX-DAL",
        "TX-DAL",
        "TX-DAL",
        "TX-HOU",
        "TX-HOU",
        "TX-HOU",
    ]


def test_transform_bronze_records_rejects_empty_list() -> None:
    """The batch transformer should require at least one Bronze record."""

    with pytest.raises(
        WeatherTransformationError,
        match="At least one Bronze record is required",
    ):
        transform_bronze_records([])


def test_transform_bronze_records_rejects_non_list() -> None:
    """The batch transformer should reject unsupported collection types."""

    with pytest.raises(
        WeatherTransformationError,
        match="must be provided as a list",
    ):
        transform_bronze_records(
            {},  # type: ignore[arg-type]
        )