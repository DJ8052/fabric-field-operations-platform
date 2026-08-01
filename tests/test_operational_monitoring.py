"""Tests for isolated Bronze ingestion monitoring and Delta persistence."""

from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from operational_bronze_ingestion.entity_config import ENTITY_CONFIGS
from operational_bronze_ingestion.monitoring import (
    MONITORING_MERGE_CONDITION,
    MONITORING_SCHEMA,
    MONITORING_TABLE_NAME,
    AllEntitiesFailedError,
    MonitoringRecord,
    run_ingestion_with_monitoring,
    write_monitoring_records,
)


def _sources(root: Path) -> dict[str, Path]:
    root.mkdir()
    paths: dict[str, Path] = {}
    for entity_name, config in ENTITY_CONFIGS.items():
        path = root / f"{entity_name}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=config.required_columns,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerow(
                {
                    column: f"{entity_name}-{column}"
                    for column in config.required_columns
                }
            )
        paths[entity_name] = path
    return paths


class CapturingWriter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, list[MonitoringRecord], str]] = []

    def __call__(
        self,
        spark: object,
        records: list[MonitoringRecord],
        *,
        table_name: str,
    ) -> None:
        self.calls.append((spark, records.copy(), table_name))


def test_successful_entities_create_complete_monitoring_records(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path / "source")
    writer = CapturingWriter()
    spark = object()

    summary = run_ingestion_with_monitoring(
        sources,
        "2026-08-01",
        "success-run",
        spark=spark,
        bronze_root=str(tmp_path / "bronze"),
        monitoring_writer=writer,
    )

    assert summary.status == "SUCCEEDED"
    assert summary.succeeded_count == 12
    assert summary.failed_count == 0
    assert len(writer.calls) == 1
    assert len(writer.calls[0][1]) == 12
    region = next(
        record
        for record in summary.records
        if record.entity_name == "regions"
    )
    assert region.status == "SUCCEEDED"
    assert region.row_count == 1
    assert region.checksum_sha256 == hashlib.sha256(
        sources["regions"].read_bytes()
    ).hexdigest()
    assert region.error_type is None
    assert region.error_message is None
    assert region.started_at.tzinfo == timezone.utc
    assert region.completed_at.tzinfo == timezone.utc
    assert region.completed_at >= region.started_at
    assert region.duration_seconds >= 0


def test_one_failed_entity_is_isolated_and_returns_partial_success(
    tmp_path: Path,
) -> None:
    sources = _sources(tmp_path / "source")
    sources["regions"] = tmp_path / "missing-regions.csv"
    writer = CapturingWriter()

    summary = run_ingestion_with_monitoring(
        sources,
        "2026-08-01",
        "partial-run",
        spark=object(),
        bronze_root=str(tmp_path / "bronze"),
        monitoring_writer=writer,
    )

    assert summary.status == "PARTIAL_SUCCESS"
    assert summary.succeeded_count == 11
    assert summary.failed_count == 1
    failed = [
        record for record in summary.records if record.status == "FAILED"
    ]
    assert len(failed) == 1
    assert failed[0].entity_name == "regions"
    assert failed[0].error_type == "IngestionError"
    assert failed[0].error_message
    assert len(writer.calls[0][1]) == 12
    assert all(
        record.status == "SUCCEEDED"
        for record in summary.records
        if record.entity_name != "regions"
    )


def test_all_failures_are_monitored_before_overall_failure(
    tmp_path: Path,
) -> None:
    sources = {
        entity_name: tmp_path / f"missing-{entity_name}.csv"
        for entity_name in ENTITY_CONFIGS
    }
    writer = CapturingWriter()

    with pytest.raises(AllEntitiesFailedError) as captured:
        run_ingestion_with_monitoring(
            sources,
            "2026-08-01",
            "failed-run",
            spark=object(),
            bronze_root=str(tmp_path / "bronze"),
            monitoring_writer=writer,
        )

    summary = captured.value.summary
    assert summary.status == "FAILED"
    assert summary.succeeded_count == 0
    assert summary.failed_count == 12
    assert len(summary.records) == 12
    assert all(record.status == "FAILED" for record in summary.records)
    assert len(writer.calls) == 1
    assert len(writer.calls[0][1]) == 12


def _record() -> MonitoringRecord:
    instant = datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
    return MonitoringRecord(
        run_id="run-1",
        ingestion_date=instant.date(),
        entity_name="regions",
        source_path="Files/source/operations/regions.csv",
        destination_path=(
            "Files/bronze/operations/regions/"
            "ingestion_date=2026-08-01/run_run-1.csv"
        ),
        row_count=4,
        checksum_sha256="a" * 64,
        status="SUCCEEDED",
        error_type=None,
        error_message=None,
        started_at=instant,
        completed_at=instant,
        duration_seconds=0.0,
    )


def test_monitoring_merge_uses_natural_key_and_upserts() -> None:
    spark = MagicMock()
    frame = MagicMock()
    source = MagicMock()
    factory = MagicMock()
    delta_table = MagicMock()
    target = MagicMock()
    merge = MagicMock()

    spark.createDataFrame.return_value = frame
    spark.catalog.tableExists.return_value = True
    frame.alias.return_value = source
    factory.forName.return_value = delta_table
    delta_table.alias.return_value = target
    target.merge.return_value = merge
    merge.whenMatchedUpdateAll.return_value = merge
    merge.whenNotMatchedInsertAll.return_value = merge

    write_monitoring_records(
        spark,
        [_record()],
        delta_table_factory=factory,
    )

    spark.createDataFrame.assert_called_once_with(
        [_record().as_row()],
        schema=MONITORING_SCHEMA,
    )
    spark.catalog.tableExists.assert_called_once_with(
        MONITORING_TABLE_NAME
    )
    factory.forName.assert_called_once_with(
        spark,
        MONITORING_TABLE_NAME,
    )
    target.merge.assert_called_once_with(
        source,
        MONITORING_MERGE_CONDITION,
    )
    assert MONITORING_MERGE_CONDITION == (
        "target.run_id = source.run_id AND "
        "target.ingestion_date = source.ingestion_date AND "
        "target.entity_name = source.entity_name"
    )
    merge.whenMatchedUpdateAll.assert_called_once_with()
    merge.whenNotMatchedInsertAll.assert_called_once_with()
    merge.execute.assert_called_once_with()


def test_monitoring_writer_creates_delta_table_when_missing() -> None:
    spark = MagicMock()
    frame = MagicMock()
    spark.createDataFrame.return_value = frame
    spark.catalog.tableExists.return_value = False
    frame.write.format.return_value = frame.write
    frame.write.mode.return_value = frame.write

    write_monitoring_records(spark, [_record()])

    frame.write.format.assert_called_once_with("delta")
    frame.write.mode.assert_called_once_with("overwrite")
    frame.write.saveAsTable.assert_called_once_with(
        MONITORING_TABLE_NAME
    )
