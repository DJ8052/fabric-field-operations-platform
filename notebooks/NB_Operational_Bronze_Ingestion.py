# Fabric notebook source
# Ingest deterministic operational source CSVs into partitioned Bronze storage.

from __future__ import annotations

from datetime import date

from notebookutils import mssparkutils

from operational_bronze_ingestion import (
    ENTITY_CONFIGS,
    AllEntitiesFailedError,
    run_ingestion_with_monitoring,
)


DEFAULT_SOURCE_ROOT = "Files/source/operations"
requested_source_root = (
    globals().get("source_root")
    or globals().get("SOURCE_ROOT")
)
SOURCE_ROOT = (
    requested_source_root.strip()
    if isinstance(requested_source_root, str) and requested_source_root.strip()
    else DEFAULT_SOURCE_ROOT
)
BRONZE_ROOT = "Files/bronze/operations"
INGESTION_DATE = date.today().isoformat()
RUN_ID = "operational-manual"
OVERWRITE = False


def source_paths(source_root: str = SOURCE_ROOT) -> dict[str, str]:
    """Map every approved entity to its incoming source CSV."""
    root = source_root.rstrip("/")
    return {name: f"{root}/{config.folder}.csv" for name, config in ENTITY_CONFIGS.items()}


try:
    summary = run_ingestion_with_monitoring(
        source_paths(),
        INGESTION_DATE,
        RUN_ID,
        spark=spark,
        bronze_root=BRONZE_ROOT,
        filesystem=mssparkutils.fs,
        overwrite=OVERWRITE,
    )
except AllEntitiesFailedError as error:
    summary = error.summary
    print(
        f"status={summary.status}, succeeded={summary.succeeded_count}, "
        f"failed={summary.failed_count}"
    )
    raise

for record in summary.records:
    print(
        f"{record.entity_name}: status={record.status}, "
        f"rows={record.row_count}, destination={record.destination_path}"
    )

print(
    f"status={summary.status}, succeeded={summary.succeeded_count}, "
    f"failed={summary.failed_count}"
)
