"""Stable CSV serialization for operational source records."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .config import GENERATION_ORDER, INGESTION_DATE


def write_dataset(dataset: dict[str, list[dict[str, Any]]], output_root: Path, run_id: str) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name in GENERATION_ORDER:
        rows = dataset[name]
        folder = output_root / name / f"ingestion_date={INGESTION_DATE.isoformat()}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"run_{run_id}.csv"
        columns = list(rows[0])
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        paths[name] = path
    return paths
