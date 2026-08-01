"""Tests for operational Bronze ingestion."""

from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from operational_bronze_ingestion.entity_config import ENTITY_CONFIGS, get_entity_config
from operational_bronze_ingestion.ingest import IngestionError, build_destination_path, ingest_entity


def _source(path: Path, entity: str, rows: int = 2) -> bytes:
    config = get_entity_config(entity)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=config.required_columns, lineterminator="\n")
        writer.writeheader()
        for index in range(rows):
            writer.writerow({column: f"value-{index}" for column in config.required_columns})
    return path.read_bytes()


def test_configuration_contains_all_12_entities() -> None:
    assert tuple(ENTITY_CONFIGS) == ("regions", "offices", "employees", "projects", "job_sites", "crews", "activities", "field_schedules", "equipment_types", "equipment", "equipment_assignments", "safety_thresholds")


def test_build_destination_path() -> None:
    path = build_destination_path(get_entity_config("regions"), "2026-08-01", "run-123")
    assert path == "Files/bronze/operations/regions/ingestion_date=2026-08-01/run_run-123.csv"


def test_local_ingestion_preserves_source_bytes(tmp_path: Path) -> None:
    source = tmp_path / "regions.csv"
    expected = _source(source, "regions")
    root = tmp_path / "bronze"
    result = ingest_entity("regions", source, "2026-08-01", "accepted", bronze_root=str(root))
    target = Path(result.destination_path)
    assert result.row_count == 2
    assert target.read_bytes() == expected


def test_ingestion_rejects_missing_required_column(tmp_path: Path) -> None:
    source = tmp_path / "regions.csv"
    source.write_text("region_id,region_code\n1,REG-001\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="region_name"):
        ingest_entity("regions", source, "2026-08-01", "accepted", bronze_root=str(tmp_path / "bronze"))


def test_ingestion_rejects_empty_csv(tmp_path: Path) -> None:
    source = tmp_path / "regions.csv"
    source.write_text("region_id,region_code,region_name\n", encoding="utf-8")
    with pytest.raises(IngestionError, match="no data rows"):
        ingest_entity("regions", source, "2026-08-01", "accepted", bronze_root=str(tmp_path / "bronze"))


def test_ingestion_does_not_overwrite_by_default(tmp_path: Path) -> None:
    source = tmp_path / "regions.csv"
    _source(source, "regions")
    root = tmp_path / "bronze"
    ingest_entity("regions", source, "2026-08-01", "accepted", bronze_root=str(root))
    with pytest.raises(IngestionError, match="already exists"):
        ingest_entity("regions", source, "2026-08-01", "accepted", bronze_root=str(root))


def test_fabric_filesystem_copy_uses_lightweight_csv_validation() -> None:
    filesystem = MagicMock()
    filesystem.head.return_value = (
        "region_id,region_code,region_name\n"
        "1,REG-001,North Texas\n"
        "2,REG-002,Central Texas\n"
    )
    filesystem.exists.return_value = False
    filesystem.cp.return_value = True
    result = ingest_entity(
        "regions",
        "Files/source/regions.csv",
        "2026-08-01",
        "accepted",
        filesystem=filesystem,
    )
    assert result.row_count == 2
    filesystem.head.assert_called_once_with(
        "Files/source/regions.csv",
        64 * 1024 * 1024,
    )
    filesystem.cp.assert_called_once_with("Files/source/regions.csv", "Files/bronze/operations/regions/ingestion_date=2026-08-01/run_accepted.csv", False)


def test_fabric_ingestion_rejects_truncated_validation_read() -> None:
    filesystem = MagicMock()
    filesystem.head.return_value = "region_id,region_code,region_name\n1,X,Y\n"
    with pytest.raises(IngestionError, match="validation limit"):
        ingest_entity(
            "regions",
            "Files/source/regions.csv",
            "2026-08-01",
            "accepted",
            filesystem=filesystem,
            max_source_bytes=8,
        )
