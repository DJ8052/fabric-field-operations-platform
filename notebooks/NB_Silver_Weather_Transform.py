"""
===============================================================================
NB_Silver_Weather_Transform.py
===============================================================================

Purpose
-------
Enterprise orchestration notebook for the Silver Weather Forecast layer.

Responsibilities
----------------
1. Make the reusable Silver transformation package available to Fabric.
2. Read all Bronze weather JSON records from OneLake.
3. Convert the Bronze Spark DataFrame into validated Python records.
4. Flatten the nested hourly arrays into relational Silver rows.
5. Persist the Silver rows to an idempotent Delta table.
6. Report execution metrics for operational validation.

Architecture
------------
This notebook intentionally contains very little business logic.

Reusable logic lives inside:

    Files/src/weather_transformation/

Modules used:
    bronze_reader.py
    validators.py
    transformer.py
    delta_writer.py

Author
------
Devon Johnson

Project
-------
Microsoft Fabric Field Operations Intelligence Platform
===============================================================================
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any


# =============================================================================
# 1. Type Checking Support
# =============================================================================

if TYPE_CHECKING:
    from pyspark.sql import SparkSession

    spark: SparkSession


# =============================================================================
# 2. Notebook Configuration
# =============================================================================

LAKEHOUSE_ROOT = Path("/lakehouse/default")
PACKAGE_ROOT = LAKEHOUSE_ROOT / "Files/src"

BRONZE_ROOT_PATH = "Files/bronze/weather_forecast"

SILVER_TABLE_NAME = (
    "dbo.silver_weather_forecast_hourly"
)

NOTEBOOK_NAME = "NB_Silver_Weather_Transform"


# =============================================================================
# 3. Make Reusable Project Modules Available
# =============================================================================

if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PACKAGE_ROOT),
    )


from weather_transformation.bronze_reader import (  # noqa: E402
    read_bronze_weather,
)
from weather_transformation.delta_writer import (  # noqa: E402
    SilverWriteResult,
    write_silver_weather,
)
from weather_transformation.transformer import (  # noqa: E402
    transform_bronze_records,
)


# =============================================================================
# 4. Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger(
    NOTEBOOK_NAME
)


# =============================================================================
# 5. Bronze DataFrame Conversion
# =============================================================================

def dataframe_to_bronze_records(
    bronze_df: Any,
) -> list[dict[str, Any]]:
    """Convert a Bronze Spark DataFrame into Python dictionaries.

    The reusable transformation layer operates on Python mappings so its
    business rules can be tested locally without requiring Spark.

    Parameters
    ----------
    bronze_df:
        Spark DataFrame returned by ``read_bronze_weather``.

    Returns
    -------
    list[dict[str, Any]]
        Bronze records ready for structural validation and transformation.

    Raises
    ------
    RuntimeError
        If Spark cannot serialize the DataFrame or no records are returned.
    """

    try:
        bronze_json_records = (
            bronze_df
            .toJSON()
            .collect()
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to serialize the Bronze Spark DataFrame "
            "into JSON records."
        ) from exc

    if not bronze_json_records:
        raise RuntimeError(
            "The Bronze Spark DataFrame produced no records."
        )

    try:
        bronze_records = [
            json.loads(record)
            for record in bronze_json_records
        ]
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "A Bronze record could not be decoded as valid JSON."
        ) from exc

    return bronze_records


# =============================================================================
# 6. Main Silver Orchestration
# =============================================================================

def run_silver_weather_transform() -> SilverWriteResult:
    """Execute the complete Bronze-to-Silver weather workflow.

    Returns
    -------
    SilverWriteResult
        Summary of the Delta table write.

    Raises
    ------
    Exception
        Any read, validation, transformation, or persistence failure is logged
        and propagated so a Fabric pipeline can correctly mark the notebook
        activity as failed.
    """

    run_started_utc = datetime.now(
        timezone.utc
    )

    logger.info("=" * 78)
    logger.info(
        "SILVER WEATHER TRANSFORMATION STARTED"
    )
    logger.info("=" * 78)
    logger.info(
        "Notebook: %s",
        NOTEBOOK_NAME,
    )
    logger.info(
        "Started UTC: %s",
        run_started_utc.isoformat(),
    )
    logger.info(
        "Bronze path: %s",
        BRONZE_ROOT_PATH,
    )
    logger.info(
        "Silver table: %s",
        SILVER_TABLE_NAME,
    )

    try:
        # ---------------------------------------------------------------------
        # Read all Bronze weather JSON files
        # ---------------------------------------------------------------------

        bronze_df = read_bronze_weather(
            spark=spark,
            bronze_root_path=BRONZE_ROOT_PATH,
        )

        bronze_record_count = (
            bronze_df.count()
        )

        logger.info(
            "Bronze records read: %s",
            bronze_record_count,
        )

        # ---------------------------------------------------------------------
        # Convert Spark rows into validated Python record structures
        # ---------------------------------------------------------------------

        bronze_records = (
            dataframe_to_bronze_records(
                bronze_df
            )
        )

        logger.info(
            "Bronze records prepared for transformation: %s",
            len(bronze_records),
        )

        # ---------------------------------------------------------------------
        # Flatten hourly arrays into relational Silver rows
        # ---------------------------------------------------------------------

        silver_rows = (
            transform_bronze_records(
                bronze_records
            )
        )

        logger.info(
            "Silver rows produced: %s",
            len(silver_rows),
        )

        # ---------------------------------------------------------------------
        # Persist the Silver rows using an idempotent Delta write
        # ---------------------------------------------------------------------

        write_result = (
            write_silver_weather(
                spark=spark,
                silver_rows=silver_rows,
                table_name=SILVER_TABLE_NAME,
            )
        )

        run_completed_utc = datetime.now(
            timezone.utc
        )

        run_duration_seconds = (
            run_completed_utc
            - run_started_utc
        ).total_seconds()

        # ---------------------------------------------------------------------
        # Display final operational summary
        # ---------------------------------------------------------------------

        print()
        print("=" * 78)
        print(
            "SILVER WEATHER TRANSFORMATION SUMMARY"
        )
        print("=" * 78)
        print(
            f"Notebook              : {NOTEBOOK_NAME}"
        )
        print(
            f"Started UTC           : "
            f"{run_started_utc.isoformat()}"
        )
        print(
            f"Completed UTC         : "
            f"{run_completed_utc.isoformat()}"
        )
        print(
            f"Duration seconds      : "
            f"{run_duration_seconds:.3f}"
        )
        print(
            f"Bronze records read   : "
            f"{bronze_record_count}"
        )
        print(
            f"Silver rows produced  : "
            f"{len(silver_rows)}"
        )
        print(
            f"Silver rows written   : "
            f"{write_result.row_count}"
        )
        print(
            f"Write action          : "
            f"{write_result.write_action}"
        )
        print(
            f"Target table          : "
            f"{write_result.table_name}"
        )
        print(
            "Overall status        : success"
        )
        print("=" * 78)

        logger.info(
            "Silver transformation completed successfully."
        )

        return write_result

    except Exception:
        run_failed_utc = datetime.now(
            timezone.utc
        )

        run_duration_seconds = (
            run_failed_utc
            - run_started_utc
        ).total_seconds()

        logger.exception(
            "Silver weather transformation failed "
            "after %.3f seconds.",
            run_duration_seconds,
        )

        raise


# =============================================================================
# 7. Notebook Entry Point
# =============================================================================

silver_write_result = (
    run_silver_weather_transform()
)