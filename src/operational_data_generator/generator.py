"""Orchestrate deterministic accepted operational-data generation."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from . import entities
from .config import RUN_ID
from .validators import validate_dataset
from .writers import write_dataset


def generate_dataset() -> dict[str, list[dict[str, Any]]]:
    data: dict[str, list[dict[str, Any]]] = {}
    data["regions"] = entities.generate_regions()
    data["offices"] = entities.generate_offices(data["regions"])
    data["employees"] = entities.generate_employees(data["offices"])
    data["activities"] = entities.generate_activities()
    data["equipment_types"] = entities.generate_equipment_types()
    data["safety_thresholds"] = entities.generate_safety_thresholds(data["activities"], data["equipment_types"])
    data["projects"] = entities.generate_projects(data["offices"], data["employees"])
    data["job_sites"] = entities.generate_job_sites(data["projects"])
    data["crews"] = entities.generate_crews(data["offices"], data["employees"])
    data["equipment"] = entities.generate_equipment(data["equipment_types"])
    data["field_schedules"] = entities.generate_field_schedules(data["projects"], data["job_sites"], data["crews"], data["activities"])
    data["equipment_assignments"] = entities.generate_equipment_assignments(data["equipment"], data["job_sites"])
    validate_dataset(data)
    return data


def run(output_root: Path, run_id: str = RUN_ID) -> dict[str, Path]:
    dataset = generate_dataset()
    return write_dataset(dataset, output_root, run_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=Path("Files/bronze/operations"))
    parser.add_argument("--run-id", default=RUN_ID)
    args = parser.parse_args()
    paths = run(args.output_root, args.run_id)
    for entity, path in paths.items():
        print(f"{entity}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
