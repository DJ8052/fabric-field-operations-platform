"""Delta persistence utilities for the Silver weather layer.

This module converts transformed Silver weather records into a Spark DataFrame
and persists them to a Microsoft Fabric Lakehouse Delta table.

The writer uses an idempotent MERGE based on the approved logical key:

    pipeline_run_id
    + location_id
    + forecast_timestamp_local

The module contains no ingestion or transformation logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


DEFAULT_SILVER_TABLE_NAME = (
    "dbo.silver_weather_forecast_hourly"
)

SILVER_MERGE_CONDITION = """
target.pipeline_run_id = source.pipeline_run_id
AND target.location_id = source.location_id
AND target.forecast_timestamp_local
    = source.forecast_timestamp_local
"""


class SilverWriteError(RuntimeError):
    """Raised when Silver records cannot be persisted successfully."""


@dataclass(frozen=True)
class SilverWriteResult:
    """Summary returned after a successful Silver Delta write."""

    table_name: str
    row_count: int
    write_action: str


def _validate_table_name(
    table_name: Any,
) -> str:
    """Validate and normalize the target Delta table name."""

    if not isinstance(table_name, str):
        raise SilverWriteError(
            "Silver table name must be provided as a string."
        )

    normalized_table_name = table_name.strip()

    if not normalized_table_name:
        raise SilverWriteError(
            "Silver table name cannot be blank."
        )

    return normalized_table_name


def _validate_silver_rows(
    silver_rows: Any,
) -> list[dict[str, Any]]:
    """Validate the transformed Silver record collection."""

    if not isinstance(silver_rows, list):
        raise SilverWriteError(
            "Silver rows must be provided as a list."
        )

    if not silver_rows:
        raise SilverWriteError(
            "At least one Silver row is required."
        )

    invalid_indexes = [
        index
        for index, row in enumerate(silver_rows)
        if not isinstance(row, dict)
    ]

    if invalid_indexes:
        raise SilverWriteError(
            "Every Silver row must be a dictionary. "
            f"Invalid row indexes: {invalid_indexes}."
        )

    return silver_rows


def _load_delta_table_factory() -> Any:
    """Import DeltaTable only when the writer executes in Spark."""

    try:
        from delta.tables import DeltaTable
    except ImportError as exc:
        raise SilverWriteError(
            "Delta Lake support is unavailable. Run this writer inside "
            "a Microsoft Fabric Spark environment or install the "
            "required Delta Lake dependency."
        ) from exc

    return DeltaTable


def write_silver_weather(
    spark: Any,
    silver_rows: list[dict[str, Any]],
    table_name: str = DEFAULT_SILVER_TABLE_NAME,
    *,
    delta_table_factory: Callable[..., Any] | None = None,
) -> SilverWriteResult:
    """Create or merge Silver weather records into a Delta table.

    Parameters
    ----------
    spark:
        Active SparkSession supplied by Microsoft Fabric.
    silver_rows:
        Transformed Silver weather records produced by ``transformer.py``.
    table_name:
        Fully qualified Lakehouse Delta table name.
    delta_table_factory:
        Optional DeltaTable-compatible dependency used by automated tests.
        Production callers should leave this argument unset.

    Returns
    -------
    SilverWriteResult
        Target table, processed row count, and action performed.

    Raises
    ------
    SilverWriteError
        If input validation, DataFrame creation, table detection, creation,
        or Delta MERGE fails.
    """

    validated_rows = _validate_silver_rows(
        silver_rows
    )

    normalized_table_name = _validate_table_name(
        table_name
    )

    if spark is None:
        raise SilverWriteError(
            "An active SparkSession is required."
        )

    try:
        silver_df = spark.createDataFrame(
            validated_rows
        )
    except Exception as exc:
        raise SilverWriteError(
            "Unable to create the Silver Spark DataFrame."
        ) from exc

    try:
        silver_row_count = silver_df.count()
    except Exception as exc:
        raise SilverWriteError(
            "The Silver DataFrame was created, but its row count "
            "could not be evaluated."
        ) from exc

    if silver_row_count == 0:
        raise SilverWriteError(
            "The Silver DataFrame contains no rows."
        )

    try:
        table_exists = spark.catalog.tableExists(
            normalized_table_name
        )
    except Exception as exc:
        raise SilverWriteError(
            "Unable to determine whether the Silver Delta table exists."
        ) from exc

    if table_exists:
        factory = (
            delta_table_factory
            if delta_table_factory is not None
            else _load_delta_table_factory()
        )

        try:
            target_table = factory.forName(
                spark,
                normalized_table_name,
            )

            (
                target_table.alias("target")
                .merge(
                    silver_df.alias("source"),
                    SILVER_MERGE_CONDITION,
                )
                .whenMatchedUpdateAll()
                .whenNotMatchedInsertAll()
                .execute()
            )
        except Exception as exc:
            raise SilverWriteError(
                "Unable to merge records into Silver Delta table "
                f"'{normalized_table_name}'."
            ) from exc

        write_action = "merged"

    else:
        try:
            (
                silver_df.write
                .format("delta")
                .mode("overwrite")
                .saveAsTable(normalized_table_name)
            )
        except Exception as exc:
            raise SilverWriteError(
                "Unable to create Silver Delta table "
                f"'{normalized_table_name}'."
            ) from exc

        write_action = "created"

    return SilverWriteResult(
        table_name=normalized_table_name,
        row_count=silver_row_count,
        write_action=write_action,
    )