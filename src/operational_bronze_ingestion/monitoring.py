"""Per-entity operational Bronze monitoring and idempotent Delta persistence."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .entity_config import ENTITY_CONFIGS
from .ingest import (
    DEFAULT_BRONZE_ROOT,
    DEFAULT_MAX_SOURCE_BYTES,
    IngestionError,
    build_destination_path,
    ingest_entity,
)

MONITORING_TABLE_NAME = "monitoring_operational_ingestion_runs"
MONITORING_SCHEMA = """
run_id string,
ingestion_date date,
entity_name string,
source_path string,
destination_path string,
row_count long,
checksum_sha256 string,
status string,
error_type string,
error_message string,
started_at timestamp,
completed_at timestamp,
duration_seconds double
""".strip()
MONITORING_MERGE_CONDITION = " AND ".join(
    (
        "target.run_id = source.run_id",
        "target.ingestion_date = source.ingestion_date",
        "target.entity_name = source.entity_name",
    )
)


@dataclass(frozen=True)
class MonitoringRecord:
    """Monitoring outcome for one entity in one ingestion run."""

    run_id: str
    ingestion_date: date
    entity_name: str
    source_path: str
    destination_path: str
    row_count: int | None
    checksum_sha256: str | None
    status: str
    error_type: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime
    duration_seconds: float

    def as_row(self) -> tuple[Any, ...]:
        """Return values in ``MONITORING_SCHEMA`` column order."""
        return (
            self.run_id,
            self.ingestion_date,
            self.entity_name,
            self.source_path,
            self.destination_path,
            self.row_count,
            self.checksum_sha256,
            self.status,
            self.error_type,
            self.error_message,
            self.started_at,
            self.completed_at,
            self.duration_seconds,
        )


@dataclass(frozen=True)
class IngestionRunSummary:
    """Notebook-level outcome for a complete 12-entity attempt."""

    run_id: str
    ingestion_date: date
    status: str
    succeeded_count: int
    failed_count: int
    records: tuple[MonitoringRecord, ...]


class AllEntitiesFailedError(IngestionError):
    """Raised after monitoring is written when all 12 entities fail."""

    def __init__(self, summary: IngestionRunSummary) -> None:
        super().__init__(
            f"All {summary.failed_count} operational entities failed ingestion"
        )
        self.summary = summary


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_ingestion_date(value: date | str) -> date:
    try:
        return value if isinstance(value, date) else date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise IngestionError(
            "ingestion_date must be a date or ISO date string"
        ) from exc


def _filesystem_bytes(
    filesystem: Any,
    source_path: str,
    max_source_bytes: int,
) -> bytes:
    if (
        not isinstance(max_source_bytes, int)
        or isinstance(max_source_bytes, bool)
        or max_source_bytes <= 0
    ):
        raise IngestionError("max_source_bytes must be a positive integer")
    try:
        content = filesystem.head(source_path, max_source_bytes)
    except Exception as exc:
        raise IngestionError(
            f"Unable to read source CSV for checksum: {source_path}"
        ) from exc
    if isinstance(content, str):
        content = content.encode("utf-8")
    if not isinstance(content, bytes):
        raise IngestionError(
            "filesystem.head must return source content as text or bytes"
        )
    if len(content) >= max_source_bytes:
        raise IngestionError(
            f"Source reached the {max_source_bytes}-byte checksum limit; "
            "increase max_source_bytes"
        )
    return content


def calculate_source_checksum(
    source_path: str | Path,
    *,
    filesystem: Any | None = None,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
) -> str:
    """Calculate SHA-256 from source bytes before the Bronze copy."""
    digest = hashlib.sha256()
    if filesystem is None:
        source = Path(source_path)
        if not source.is_file():
            raise IngestionError(f"Source CSV does not exist: {source}")
        with source.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    else:
        digest.update(
            _filesystem_bytes(
                filesystem,
                str(source_path),
                max_source_bytes,
            )
        )
    return digest.hexdigest()


def _delta_factory() -> Any:
    try:
        from delta.tables import DeltaTable
    except ImportError as exc:
        raise IngestionError(
            "Delta Lake support is required to write operational monitoring"
        ) from exc
    return DeltaTable


def write_monitoring_records(
    spark: Any,
    records: list[MonitoringRecord],
    *,
    table_name: str = MONITORING_TABLE_NAME,
    delta_table_factory: Any | None = None,
) -> None:
    """Upsert monitoring records using the three-column natural key."""
    if spark is None:
        raise IngestionError("spark is required for the monitoring Delta table")
    if not records:
        raise IngestionError("At least one monitoring record is required")
    if not isinstance(table_name, str) or not table_name.strip():
        raise IngestionError("monitoring table_name must be non-empty")
    normalized_table = table_name.strip()
    try:
        frame = spark.createDataFrame(
            [record.as_row() for record in records],
            schema=MONITORING_SCHEMA,
        )
        exists = spark.catalog.tableExists(normalized_table)
        if not exists:
            (
                frame.write.format("delta")
                .mode("overwrite")
                .saveAsTable(normalized_table)
            )
            return
        factory = delta_table_factory or _delta_factory()
        target = factory.forName(spark, normalized_table).alias("target")
        source = frame.alias("source")
        (
            target.merge(source, MONITORING_MERGE_CONDITION)
            .whenMatchedUpdateAll()
            .whenNotMatchedInsertAll()
            .execute()
        )
    except IngestionError:
        raise
    except Exception as exc:
        raise IngestionError(
            f"Unable to upsert monitoring table {normalized_table}"
        ) from exc


def run_ingestion_with_monitoring(
    source_paths: dict[str, str | Path],
    ingestion_date: date | str,
    run_id: str,
    *,
    spark: Any,
    bronze_root: str = DEFAULT_BRONZE_ROOT,
    filesystem: Any | None = None,
    overwrite: bool = False,
    max_source_bytes: int = DEFAULT_MAX_SOURCE_BYTES,
    table_name: str = MONITORING_TABLE_NAME,
    monitoring_writer: Callable[..., None] = write_monitoring_records,
    clock: Callable[[], datetime] = _utc_now,
) -> IngestionRunSummary:
    """Attempt all entities, persist outcomes, and fail only on 12 failures."""
    parsed_date = _parse_ingestion_date(ingestion_date)
    records: list[MonitoringRecord] = []
    for entity_name, config in ENTITY_CONFIGS.items():
        source = str(source_paths.get(entity_name, ""))
        started_at = clock()
        destination = ""
        row_count: int | None = None
        checksum: str | None = None
        status = "FAILED"
        error_type: str | None = None
        error_message: str | None = None
        try:
            destination = build_destination_path(
                config,
                parsed_date,
                run_id,
                bronze_root,
            )
            checksum = calculate_source_checksum(
                source,
                filesystem=filesystem,
                max_source_bytes=max_source_bytes,
            )
            result = ingest_entity(
                entity_name,
                source,
                parsed_date,
                run_id,
                bronze_root=bronze_root,
                filesystem=filesystem,
                overwrite=overwrite,
                max_source_bytes=max_source_bytes,
            )
            destination = result.destination_path
            row_count = result.row_count
            status = "SUCCEEDED"
        except Exception as exc:  # Per-entity isolation boundary.
            error_type = type(exc).__name__
            error_message = str(exc)
        completed_at = clock()
        duration = max(
            0.0,
            (completed_at - started_at).total_seconds(),
        )
        records.append(
            MonitoringRecord(
                run_id=run_id,
                ingestion_date=parsed_date,
                entity_name=entity_name,
                source_path=source,
                destination_path=destination,
                row_count=row_count,
                checksum_sha256=checksum,
                status=status,
                error_type=error_type,
                error_message=error_message,
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
            )
        )
    succeeded = sum(record.status == "SUCCEEDED" for record in records)
    failed = len(records) - succeeded
    summary_status = (
        "SUCCEEDED"
        if failed == 0
        else "PARTIAL_SUCCESS"
        if succeeded > 0
        else "FAILED"
    )
    summary = IngestionRunSummary(
        run_id=run_id,
        ingestion_date=parsed_date,
        status=summary_status,
        succeeded_count=succeeded,
        failed_count=failed,
        records=tuple(records),
    )
    monitoring_writer(
        spark,
        records,
        table_name=table_name,
    )
    if succeeded == 0:
        raise AllEntitiesFailedError(summary)
    return summary
