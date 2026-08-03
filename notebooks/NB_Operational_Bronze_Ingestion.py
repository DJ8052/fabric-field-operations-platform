# Fabric notebook source
# Ingest deterministic operational source CSVs into partitioned,
# immutable Bronze storage with per-entity monitoring.

from __future__ import annotations

from datetime import date

from notebookutils import mssparkutils

from operational_bronze_ingestion import (
    ENTITY_CONFIGS,
    AllEntitiesFailedError,
    run_ingestion_with_monitoring,
)


# -------------------------------------------------------------------
# Runtime parameter resolution
# -------------------------------------------------------------------

DEFAULT_SOURCE_ROOT = "Files/source/operations"
DEFAULT_BRONZE_ROOT = "Files/bronze/operations"
MONITORING_TABLE = "monitoring_operational_ingestion_runs"


def normalize_boolean(value) -> bool:
    """Normalize manual or pipeline Boolean parameters."""

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()

        if normalized in {"true", "1", "yes", "y"}:
            return True

        if normalized in {"false", "0", "no", "n", ""}:
            return False

    raise ValueError(f"Unsupported Boolean value: {value!r}")


requested_source_root = (
    globals().get("source_root")
    or globals().get("SOURCE_ROOT")
)

SOURCE_ROOT = (
    str(requested_source_root).strip().rstrip("/")
    if requested_source_root is not None
    and str(requested_source_root).strip()
    else DEFAULT_SOURCE_ROOT
)

requested_bronze_root = (
    globals().get("bronze_root")
    or globals().get("BRONZE_ROOT")
)

BRONZE_ROOT = (
    str(requested_bronze_root).strip().rstrip("/")
    if requested_bronze_root is not None
    and str(requested_bronze_root).strip()
    else DEFAULT_BRONZE_ROOT
)

INGESTION_DATE = str(
    globals().get("ingestion_date")
    or globals().get("INGESTION_DATE")
    or date.today().isoformat()
).strip()

RUN_ID = str(
    globals().get("run_id")
    or globals().get("RUN_ID")
    or "operational-manual"
).strip()

raw_overwrite = globals().get(
    "overwrite",
    globals().get("OVERWRITE", False),
)

OVERWRITE = normalize_boolean(raw_overwrite)


if not SOURCE_ROOT:
    raise ValueError("source_root cannot be blank.")

if not BRONZE_ROOT:
    raise ValueError("bronze_root cannot be blank.")

if not INGESTION_DATE:
    raise ValueError("ingestion_date cannot be blank.")

if not RUN_ID:
    raise ValueError("run_id cannot be blank.")


# -------------------------------------------------------------------
# Source mapping
# -------------------------------------------------------------------

def source_paths(
    source_root_value: str = SOURCE_ROOT,
) -> dict[str, str]:
    """Map every approved entity to its incoming source CSV."""

    root = source_root_value.rstrip("/")

    return {
        entity_name: f"{root}/{config.folder}.csv"
        for entity_name, config in ENTITY_CONFIGS.items()
    }


# -------------------------------------------------------------------
# Execution configuration
# -------------------------------------------------------------------

print("=== Operational Bronze Ingestion ===")
print(f"Source root      : {SOURCE_ROOT}")
print(f"Bronze root      : {BRONZE_ROOT}")
print(f"Monitoring table : {MONITORING_TABLE}")
print(f"Ingestion date   : {INGESTION_DATE}")
print(f"Run ID           : {RUN_ID}")
print(f"Overwrite        : {OVERWRITE}")
print(f"Entity count     : {len(ENTITY_CONFIGS)}")


# -------------------------------------------------------------------
# Bronze ingestion
# -------------------------------------------------------------------

try:
    summary = run_ingestion_with_monitoring(
        source_paths=source_paths(),
        ingestion_date=INGESTION_DATE,
        run_id=RUN_ID,
        bronze_root=BRONZE_ROOT,
        filesystem=mssparkutils.fs,
        spark=spark,
        overwrite=OVERWRITE,
    )

except AllEntitiesFailedError as error:
    summary = error.summary

    print("\nNotebook status: FAILED")
    print(
        f"status={summary.status}, "
        f"succeeded={summary.succeeded_count}, "
        f"failed={summary.failed_count}"
    )

    raise


# -------------------------------------------------------------------
# Execution summary
# -------------------------------------------------------------------

print("\n=== Entity Results ===")

for record in summary.records:
    print(
        f"{record.entity_name}: "
        f"status={record.status}, "
        f"rows={record.row_count}, "
        f"source={record.source_path}, "
        f"destination={record.destination_path}"
    )


print("\n=== Run Summary ===")
print(
    f"status={summary.status}, "
    f"succeeded={summary.succeeded_count}, "
    f"failed={summary.failed_count}"
)

print("\nOperational Bronze ingestion completed successfully.")