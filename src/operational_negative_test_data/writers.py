"""Stable flat-file serialization for Bronze negative acceptance input."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from operational_bronze_ingestion import ENTITY_CONFIGS
from operational_data_generator.config import GENERATION_ORDER

from .manifest import expected_manifest


def _columns_and_validate(name: str, rows: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    if not rows:
        raise ValueError(f"{name} must contain at least one row")
    columns = tuple(rows[0])
    missing = [column for column in ENTITY_CONFIGS[name].required_columns if column not in columns]
    if missing:
        raise ValueError(f"{name} is missing Bronze columns: {', '.join(missing)}")
    expected = set(columns)
    if any(set(row) != expected for row in rows):
        raise ValueError(f"{name} rows do not have a consistent schema")
    return columns


def write_negative_acceptance_dataset(
    dataset: Mapping[str, Sequence[Mapping[str, Any]]], output_root: Path
) -> tuple[dict[str, Path], Path]:
    """Write 12 source-root CSVs and their expected-results JSON manifest."""
    if tuple(dataset) != GENERATION_ORDER:
        raise ValueError("dataset entity order does not match the accepted generator")
    output_root.mkdir(parents=True, exist_ok=True)
    paths: dict[str, Path] = {}
    for name in GENERATION_ORDER:
        rows = dataset[name]
        columns = _columns_and_validate(name, rows)
        path = output_root / f"{ENTITY_CONFIGS[name].folder}.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        paths[name] = path
    manifest_path = output_root / "expected-results.json"
    manifest_path.write_text(
        json.dumps(expected_manifest(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return paths, manifest_path
