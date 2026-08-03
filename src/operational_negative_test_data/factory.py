"""Build isolated negative acceptance data from the accepted generator output."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from typing import Any, Callable

from operational_data_generator import generate_dataset


Dataset = dict[str, list[dict[str, Any]]]


def _record(dataset: Dataset, entity: str, key: str, value: int) -> dict[str, Any]:
    matches = [row for row in dataset[entity] if row.get(key) == value]
    if len(matches) != 1:
        raise RuntimeError(f"Expected exactly one {entity}.{key}={value}, found {len(matches)}")
    return matches[0]


def generate_negative_acceptance_dataset(
    base_factory: Callable[[], Dataset] = generate_dataset,
) -> Dataset:
    """Deep-copy accepted data and apply only the approved acceptance mutations."""
    dataset = deepcopy(base_factory())

    _record(dataset, "regions", "region_id", 1)["region_name"] = ""
    _record(dataset, "job_sites", "job_site_id", 1)["weather_location_code"] = "TX-UNKNOWN"

    adjacent_first = _record(dataset, "equipment_assignments", "assignment_id", 1)
    adjacent_second = _record(dataset, "equipment_assignments", "assignment_id", 81)
    if adjacent_first["equipment_id"] != adjacent_second["equipment_id"]:
        raise RuntimeError("Accepted generator no longer pairs assignments 1 and 81")
    adjacent_start = datetime.fromisoformat(adjacent_first["assignment_end_timestamp"])
    adjacent_second["assignment_start_timestamp"] = adjacent_start.isoformat(timespec="seconds")
    adjacent_second["assignment_end_timestamp"] = (adjacent_start + timedelta(hours=10)).isoformat(timespec="seconds")

    overlap_first = _record(dataset, "equipment_assignments", "assignment_id", 2)
    overlap_second = _record(dataset, "equipment_assignments", "assignment_id", 82)
    if overlap_first["equipment_id"] != overlap_second["equipment_id"]:
        raise RuntimeError("Accepted generator no longer pairs assignments 2 and 82")
    overlap_start = datetime.fromisoformat(overlap_first["assignment_start_timestamp"]) + timedelta(hours=5)
    overlap_second["assignment_start_timestamp"] = overlap_start.isoformat(timespec="seconds")
    overlap_second["assignment_end_timestamp"] = (overlap_start + timedelta(hours=10)).isoformat(timespec="seconds")

    return dataset
