"""Bronze weather JSON reader for the Silver transformation layer.

This module contains the Spark-specific logic required to read all raw Bronze
weather JSON files from Microsoft Fabric OneLake.

The reader performs no business transformation and writes no data. Its only
responsibility is to return a Spark DataFrame containing the Bronze records.
"""

from __future__ import annotations

from typing import Any


DEFAULT_BRONZE_ROOT_PATH = "Files/bronze/weather_forecast"


class BronzeReadError(RuntimeError):
    """Raised when Bronze weather data cannot be read successfully."""


def read_bronze_weather(
    spark: Any,
    bronze_root_path: str = DEFAULT_BRONZE_ROOT_PATH,
) -> Any:
    """Read all Bronze weather JSON records into a Spark DataFrame.

    Parameters
    ----------
    spark:
        Active SparkSession supplied by Microsoft Fabric.
    bronze_root_path:
        Root OneLake path containing partitioned Bronze weather JSON files.

    Returns
    -------
    DataFrame
        Spark DataFrame containing one row per Bronze JSON file.

    Raises
    ------
    BronzeReadError
        If the path is blank, Spark cannot read the data, or no records exist.
    """

    if not isinstance(bronze_root_path, str):
        raise BronzeReadError(
            "Bronze root path must be provided as a string."
        )

    normalized_path = bronze_root_path.strip()

    if not normalized_path:
        raise BronzeReadError(
            "Bronze root path cannot be blank."
        )

    try:
        bronze_df = (
            spark.read
            .option("recursiveFileLookup", "true")
            .option("multiline", "true")
            .json(normalized_path)
        )
    except Exception as exc:
        raise BronzeReadError(
            "Unable to read Bronze weather JSON from "
            f"'{normalized_path}'."
        ) from exc

    try:
        bronze_record_count = bronze_df.count()
    except Exception as exc:
        raise BronzeReadError(
            "Bronze weather data was read, but the record count "
            "could not be evaluated."
        ) from exc

    if bronze_record_count == 0:
        raise BronzeReadError(
            "No Bronze weather records were found under "
            f"'{normalized_path}'."
        )

    return bronze_df