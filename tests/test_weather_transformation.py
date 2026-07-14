"""Unit tests for Bronze-to-Silver weather transformation utilities."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from weather_transformation.bronze_reader import (
    BronzeReadError,
    read_bronze_weather,
)
from weather_transformation.delta_writer import (
    DEFAULT_SILVER_TABLE_NAME,
    SILVER_MERGE_CONDITION,
    SilverWriteError,
    SilverWriteResult,
    write_silver_weather,
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
# SHARED FIXTURES AND TEST HELPERS
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


@pytest.fixture
def valid_silver_rows() -> list[dict]:
    """Return two minimal transformed Silver records."""

    return [
        {
            "pipeline_run_id": "test-run-001",
            "location_id": "TX-DAL",
            "forecast_timestamp_local": datetime(
                2026,
                7,
                14,
                0,
                0,
            ),
            "temperature_2m": 80.1,
        },
        {
            "pipeline_run_id": "test-run-001",
            "location_id": "TX-DAL",
            "forecast_timestamp_local": datetime(
                2026,
                7,
                14,
                1,
                0,
            ),
            "temperature_2m": 79.5,
        },
    ]


def _build_mock_spark(
    *,
    record_count: int = 1,
) -> tuple[MagicMock, MagicMock]:
    """Return mocked SparkSession and DataFrame objects for Bronze reads."""

    spark = MagicMock()
    bronze_df = MagicMock()

    spark.read.option.return_value = spark.read
    spark.read.json.return_value = bronze_df
    bronze_df.count.return_value = record_count

    return spark, bronze_df


def _build_mock_delta_writer_spark(
    *,
    table_exists: bool,
    row_count: int = 2,
) -> tuple[MagicMock, MagicMock]:
    """Return mocked SparkSession and DataFrame objects for Delta writes."""

    spark = MagicMock()
    silver_df = MagicMock()

    spark.createDataFrame.return_value = silver_df
    silver_df.count.return_value = row_count
    spark.catalog.tableExists.return_value = table_exists

    silver_df.alias.return_value = silver_df

    silver_df.write.format.return_value = silver_df.write
    silver_df.write.mode.return_value = silver_df.write

    return spark, silver_df


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
    """Aligned arrays should return their validated record count."""

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
    """The declared count must equal the actual array length."""

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
    """Bronze records with no hourly forecasts should fail."""

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
    """The reader should support a custom Bronze path."""

    spark, _ = _build_mock_spark(record_count=2)

    read_bronze_weather(
        spark,
        "Files/bronze/custom_weather",
    )

    spark.read.json.assert_called_once_with(
        "Files/bronze/custom_weather"
    )


def test_read_bronze_weather_trims_custom_path() -> None:
    """Whitespace should be removed from a custom path."""

    spark, _ = _build_mock_spark(record_count=2)

    read_bronze_weather(
        spark,
        "  Files/bronze/custom_weather  ",
    )

    spark.read.json.assert_called_once_with(
        "Files/bronze/custom_weather"
    )


def test_read_bronze_weather_rejects_blank_path() -> None:
    """A blank Bronze path should fail before Spark is called."""

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
    """A non-string Bronze path should fail clearly."""

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
    """An empty Bronze dataset should fail."""

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
    """DataFrame count failures should be wrapped clearly."""

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
    """Three forecast hours should produce three Silver rows."""

    result = transform_bronze_record(valid_bronze_record)

    assert len(result) == 3


def test_transform_bronze_record_preserves_logical_key(
    valid_bronze_record: dict,
) -> None:
    """Each row should preserve its logical key values."""

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
    """Measurements sharing an array index should remain aligned."""

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
    """Silver rows should retain lineage and source metadata."""

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
    """The UTC ingestion string should become a datetime."""

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
    """Nullable measurements should remain None."""

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
    """Invalid ingestion timestamps should fail clearly."""

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
    """Invalid forecast timestamps should fail."""

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
    """A nonnumeric measurement should fail conversion."""

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
    """Boolean values should not be accepted as numeric values."""

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
    """Invalid Bronze structure should fail before transformation."""

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
    """Multiple Bronze records should produce combined rows."""

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

    assert {
        row["location_id"]
        for row in result
    } == {
        "TX-DAL",
        "TX-HOU",
    }


def test_transform_bronze_records_preserves_input_order(
    valid_bronze_record: dict,
) -> None:
    """Rows should remain grouped by source-record order."""

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
    """The batch transformer should require input records."""

    with pytest.raises(
        WeatherTransformationError,
        match="At least one Bronze record is required",
    ):
        transform_bronze_records([])


def test_transform_bronze_records_rejects_non_list() -> None:
    """The batch transformer should require a list."""

    with pytest.raises(
        WeatherTransformationError,
        match="must be provided as a list",
    ):
        transform_bronze_records(
            {},  # type: ignore[arg-type]
        )


# =============================================================================
# DELTA WRITER TESTS
# =============================================================================


def test_write_silver_weather_creates_new_table(
    valid_silver_rows: list[dict],
) -> None:
    """A missing target table should be created."""

    spark, silver_df = _build_mock_delta_writer_spark(
        table_exists=False,
        row_count=2,
    )

    result = write_silver_weather(
        spark,
        valid_silver_rows,
    )

    assert result == SilverWriteResult(
        table_name=DEFAULT_SILVER_TABLE_NAME,
        row_count=2,
        write_action="created",
    )

    spark.createDataFrame.assert_called_once_with(
        valid_silver_rows
    )
    spark.catalog.tableExists.assert_called_once_with(
        DEFAULT_SILVER_TABLE_NAME
    )

    silver_df.write.format.assert_called_once_with("delta")
    silver_df.write.mode.assert_called_once_with("overwrite")
    silver_df.write.saveAsTable.assert_called_once_with(
        DEFAULT_SILVER_TABLE_NAME
    )


def test_write_silver_weather_merges_existing_table(
    valid_silver_rows: list[dict],
) -> None:
    """An existing target table should use an idempotent merge."""

    spark, silver_df = _build_mock_delta_writer_spark(
        table_exists=True,
        row_count=2,
    )

    delta_factory = MagicMock()
    target_table = MagicMock()
    aliased_target = MagicMock()
    merge_builder = MagicMock()

    delta_factory.forName.return_value = target_table
    target_table.alias.return_value = aliased_target
    aliased_target.merge.return_value = merge_builder
    merge_builder.whenMatchedUpdateAll.return_value = merge_builder
    merge_builder.whenNotMatchedInsertAll.return_value = merge_builder

    result = write_silver_weather(
        spark,
        valid_silver_rows,
        delta_table_factory=delta_factory,
    )

    assert result == SilverWriteResult(
        table_name=DEFAULT_SILVER_TABLE_NAME,
        row_count=2,
        write_action="merged",
    )

    delta_factory.forName.assert_called_once_with(
        spark,
        DEFAULT_SILVER_TABLE_NAME,
    )
    target_table.alias.assert_called_once_with("target")
    silver_df.alias.assert_called_once_with("source")
    aliased_target.merge.assert_called_once_with(
        silver_df,
        SILVER_MERGE_CONDITION,
    )
    merge_builder.whenMatchedUpdateAll.assert_called_once_with()
    merge_builder.whenNotMatchedInsertAll.assert_called_once_with()
    merge_builder.execute.assert_called_once_with()


def test_write_silver_weather_accepts_and_trims_custom_table_name(
    valid_silver_rows: list[dict],
) -> None:
    """A custom table name should be normalized before use."""

    spark, silver_df = _build_mock_delta_writer_spark(
        table_exists=False,
    )

    result = write_silver_weather(
        spark,
        valid_silver_rows,
        "  dbo.custom_silver_weather  ",
    )

    assert result.table_name == "dbo.custom_silver_weather"

    spark.catalog.tableExists.assert_called_once_with(
        "dbo.custom_silver_weather"
    )
    silver_df.write.saveAsTable.assert_called_once_with(
        "dbo.custom_silver_weather"
    )


def test_write_silver_weather_rejects_non_list_rows() -> None:
    """Silver rows must be provided as a list."""

    with pytest.raises(
        SilverWriteError,
        match="must be provided as a list",
    ):
        write_silver_weather(
            MagicMock(),
            {},  # type: ignore[arg-type]
        )


def test_write_silver_weather_rejects_empty_rows() -> None:
    """At least one Silver row is required."""

    with pytest.raises(
        SilverWriteError,
        match="At least one Silver row is required",
    ):
        write_silver_weather(
            MagicMock(),
            [],
        )


def test_write_silver_weather_rejects_non_dictionary_rows() -> None:
    """Every Silver row must be a dictionary."""

    with pytest.raises(
        SilverWriteError,
        match="Invalid row indexes",
    ):
        write_silver_weather(
            MagicMock(),
            [
                {"location_id": "TX-DAL"},
                "invalid-row",  # type: ignore[list-item]
            ],
        )


def test_write_silver_weather_rejects_blank_table_name(
    valid_silver_rows: list[dict],
) -> None:
    """A blank target table name should fail."""

    with pytest.raises(
        SilverWriteError,
        match="cannot be blank",
    ):
        write_silver_weather(
            MagicMock(),
            valid_silver_rows,
            "   ",
        )


def test_write_silver_weather_rejects_non_string_table_name(
    valid_silver_rows: list[dict],
) -> None:
    """The target table name must be a string."""

    with pytest.raises(
        SilverWriteError,
        match="must be provided as a string",
    ):
        write_silver_weather(
            MagicMock(),
            valid_silver_rows,
            None,  # type: ignore[arg-type]
        )


def test_write_silver_weather_rejects_missing_spark_session(
    valid_silver_rows: list[dict],
) -> None:
    """An active SparkSession is required."""

    with pytest.raises(
        SilverWriteError,
        match="active SparkSession is required",
    ):
        write_silver_weather(
            None,
            valid_silver_rows,
        )


def test_write_silver_weather_wraps_dataframe_creation_error(
    valid_silver_rows: list[dict],
) -> None:
    """Spark DataFrame creation failures should be wrapped."""

    spark = MagicMock()
    spark.createDataFrame.side_effect = RuntimeError(
        "Simulated DataFrame failure"
    )

    with pytest.raises(
        SilverWriteError,
        match="Unable to create the Silver Spark DataFrame",
    ):
        write_silver_weather(
            spark,
            valid_silver_rows,
        )


def test_write_silver_weather_wraps_dataframe_count_error(
    valid_silver_rows: list[dict],
) -> None:
    """Silver DataFrame count failures should be wrapped."""

    spark, silver_df = _build_mock_delta_writer_spark(
        table_exists=False,
    )
    silver_df.count.side_effect = RuntimeError(
        "Simulated count failure"
    )

    with pytest.raises(
        SilverWriteError,
        match="row count could not be evaluated",
    ):
        write_silver_weather(
            spark,
            valid_silver_rows,
        )


def test_write_silver_weather_rejects_empty_dataframe(
    valid_silver_rows: list[dict],
) -> None:
    """A Spark DataFrame reporting zero rows should fail."""

    spark, _ = _build_mock_delta_writer_spark(
        table_exists=False,
        row_count=0,
    )

    with pytest.raises(
        SilverWriteError,
        match="contains no rows",
    ):
        write_silver_weather(
            spark,
            valid_silver_rows,
        )


def test_write_silver_weather_wraps_table_lookup_error(
    valid_silver_rows: list[dict],
) -> None:
    """Table-existence lookup failures should be wrapped."""

    spark, _ = _build_mock_delta_writer_spark(
        table_exists=False,
    )
    spark.catalog.tableExists.side_effect = RuntimeError(
        "Simulated catalog failure"
    )

    with pytest.raises(
        SilverWriteError,
        match="Unable to determine whether",
    ):
        write_silver_weather(
            spark,
            valid_silver_rows,
        )


def test_write_silver_weather_wraps_table_creation_error(
    valid_silver_rows: list[dict],
) -> None:
    """Delta table creation failures should be wrapped."""

    spark, silver_df = _build_mock_delta_writer_spark(
        table_exists=False,
    )
    silver_df.write.saveAsTable.side_effect = RuntimeError(
        "Simulated write failure"
    )

    with pytest.raises(
        SilverWriteError,
        match="Unable to create Silver Delta table",
    ):
        write_silver_weather(
            spark,
            valid_silver_rows,
        )


def test_write_silver_weather_wraps_merge_error(
    valid_silver_rows: list[dict],
) -> None:
    """Delta merge failures should be wrapped."""

    spark, _ = _build_mock_delta_writer_spark(
        table_exists=True,
    )

    delta_factory = MagicMock()
    delta_factory.forName.side_effect = RuntimeError(
        "Simulated merge failure"
    )

    with pytest.raises(
        SilverWriteError,
        match="Unable to merge records",
    ):
        write_silver_weather(
            spark,
            valid_silver_rows,
            delta_table_factory=delta_factory,
        )