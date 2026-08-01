"""Contract and reproducibility tests for operational source generation."""

from __future__ import annotations

import hashlib
import statistics
from datetime import datetime
from pathlib import Path

import pytest

from operational_data_generator import generate_dataset, run, validate_dataset
from operational_data_generator.config import GENERATION_ORDER, TARGET_COUNTS, WEATHER_LOCATIONS
from operational_data_generator.entities import SCENARIOS
from operational_data_generator.validators import ValidationError


@pytest.fixture(scope="module")
def dataset() -> dict:
    return generate_dataset()


def test_all_approved_entities_have_target_counts(dataset: dict) -> None:
    assert tuple(dataset) == GENERATION_ORDER
    assert {name: len(rows) for name, rows in dataset.items()} == TARGET_COUNTS


def test_generated_dataset_passes_hard_validation(dataset: dict) -> None:
    validate_dataset(dataset)


def test_project_dependencies_and_required_management_fields(dataset: dict) -> None:
    office_ids = {row["office_id"] for row in dataset["offices"]}
    employee_ids = {row["employee_id"] for row in dataset["employees"]}
    for row in dataset["projects"]:
        assert row["office_id"] in office_ids
        assert row["project_manager_employee_id"] in employee_ids
        assert row["field_manager_employee_id"] in employee_ids
        assert row["status"] and row["project_start_date"] and row["project_end_date"] and row["priority_code"]


def test_field_schedule_contract_and_activity_dependency(dataset: dict) -> None:
    activity_ids = {row["activity_id"] for row in dataset["activities"]}
    required = {"field_schedule_id", "project_id", "job_site_id", "crew_id", "activity_id",
                "scheduled_start_timestamp", "scheduled_end_timestamp", "scheduled_date",
                "planned_crew_hours", "planned_crew_size", "planned_labor_hours", "status",
                "rescheduled_from_schedule_id"}
    for row in dataset["field_schedules"]:
        assert required <= row.keys()
        assert row["activity_id"] in activity_ids


def test_weather_location_and_scenario_coverage(dataset: dict) -> None:
    assert {row["weather_location_code"] for row in dataset["job_sites"]} == set(WEATHER_LOCATIONS)
    assert set(SCENARIOS) <= {row["scenario_id"] for row in dataset["field_schedules"]}
    assert any(row["scenario_id"] == "equipment_relocation" for row in dataset["equipment_assignments"])


def _reschedule_chains(rows: list[dict]) -> list[list[int]]:
    successors = {row["rescheduled_from_schedule_id"]: row["field_schedule_id"]
                  for row in rows if row["rescheduled_from_schedule_id"] != ""}
    child_ids = set(successors.values())
    roots = [row["field_schedule_id"] for row in rows
             if row["status"] == "Rescheduled" and row["field_schedule_id"] not in child_ids]
    chains = []
    for root in roots:
        chain = [root]
        while chain[-1] in successors:
            chain.append(successors[chain[-1]])
        chains.append(chain)
    return chains


def test_reschedule_coverage_is_meaningful_and_immutable(dataset: dict) -> None:
    schedules = {row["field_schedule_id"]: row for row in dataset["field_schedules"]}
    chains = _reschedule_chains(dataset["field_schedules"])
    assert len(chains) >= 4, "At least four distinct reschedule chains are required"
    link_counts = [len(chain) - 1 for chain in chains]
    assert sum(count == 1 for count in link_counts) >= 2, "At least two one-link chains are required"
    assert sum(count >= 2 for count in link_counts) >= 2, "At least two multi-link chains are required"
    for chain in chains:
        timestamps = [schedules[schedule_id]["scheduled_start_timestamp"] for schedule_id in chain]
        assert len(timestamps) == len(set(timestamps)), f"Chain {chain} overwrote an original timestamp"


def _cross_project_interactions(rows: list[dict]) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    overlaps, back_to_back = [], []
    for first in rows:
        for second in rows:
            if first["field_schedule_id"] >= second["field_schedule_id"] or first["crew_id"] != second["crew_id"] or first["project_id"] == second["project_id"]:
                continue
            first_start = datetime.fromisoformat(first["scheduled_start_timestamp"])
            first_end = datetime.fromisoformat(first["scheduled_end_timestamp"])
            second_start = datetime.fromisoformat(second["scheduled_start_timestamp"])
            second_end = datetime.fromisoformat(second["scheduled_end_timestamp"])
            if first_start < second_end and second_start < first_end:
                overlaps.append((first["field_schedule_id"], second["field_schedule_id"]))
            elif first_end == second_start or second_end == first_start:
                back_to_back.append((first["field_schedule_id"], second["field_schedule_id"]))
    return overlaps, back_to_back


def test_crew_conflict_coverage_includes_overlaps_and_back_to_back(dataset: dict) -> None:
    conflicts = [row for row in dataset["field_schedules"] if row["scenario_id"] == "multiple_project_conflict"]
    overlaps, back_to_back = _cross_project_interactions(conflicts)
    assert len(overlaps) >= 3, "At least three cross-project crew overlaps are required"
    assert len(back_to_back) >= 3, "At least three exact back-to-back cross-project cases are required"


def test_crew_and_activity_loads_are_controlled_not_flat(dataset: dict) -> None:
    assert len({row["crew_id"] for row in dataset["field_schedules"]}) == TARGET_COUNTS["crews"], "Every crew must have schedule coverage"
    assert len({row["job_site_id"] for row in dataset["field_schedules"]}) == TARGET_COUNTS["job_sites"], "Every job site must have schedule coverage"
    for field in ("crew_id", "activity_id"):
        counts: dict[int, int] = {}
        for row in dataset["field_schedules"]:
            counts[row[field]] = counts.get(row[field], 0) + 1
        values = list(counts.values())
        assert statistics.pstdev(values) >= 2.0, f"{field} schedule counts are too flat and appear modulo-cycled: {counts}"


def test_high_exposure_equipment_overlaps_high_risk_window(dataset: dict) -> None:
    assignment = next(row for row in dataset["equipment_assignments"] if row["scenario_id"] == "equipment_relocation")
    equipment = next(row for row in dataset["equipment"] if row["equipment_id"] == assignment["equipment_id"])
    equipment_type = next(row for row in dataset["equipment_types"] if row["equipment_type_id"] == equipment["equipment_type_id"])
    schedule = next(row for row in dataset["field_schedules"] if row["scenario_id"] == "high_wind_equipment")
    assert equipment_type["equipment_category"] == "High Exposure"
    assert datetime.fromisoformat(assignment["assignment_start_timestamp"]) < datetime.fromisoformat(schedule["scheduled_end_timestamp"])
    assert datetime.fromisoformat(assignment["assignment_end_timestamp"]) > datetime.fromisoformat(schedule["scheduled_start_timestamp"])


def test_equipment_reassignment_is_nonsequential_and_changes_site(dataset: dict) -> None:
    assignments = dataset["equipment_assignments"]
    by_equipment: dict[int, list[dict]] = {}
    for row in assignments:
        by_equipment.setdefault(row["equipment_id"], []).append(row)
    reassigned = [rows for rows in by_equipment.values() if len(rows) > 1]
    assert len(reassigned) == 40
    assert all(rows[0]["job_site_id"] != rows[1]["job_site_id"] for rows in reassigned), "Reassignment must change job site"
    second_sites = [rows[1]["job_site_id"] for rows in reassigned]
    sequential_steps = sum(second_sites[index] == second_sites[index - 1] + 1 for index in range(1, len(second_sites)))
    assert sequential_steps < len(second_sites) // 3, "Second-site choices follow direct sequential cycling"


def test_validator_rejects_project_site_mismatch(dataset: dict) -> None:
    copy = {name: [row.copy() for row in rows] for name, rows in dataset.items()}
    copy["field_schedules"][0]["project_id"] = 75
    with pytest.raises(ValidationError, match="project/site mismatch"):
        validate_dataset(copy)


def _checksums(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.rglob("*.csv"))}


def test_two_runs_are_byte_identical(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    run(first)
    run(second)
    assert _checksums(first) == _checksums(second)
    assert len(_checksums(first)) == 12
    assert all(b"\r\n" not in path.read_bytes() for path in first.rglob("*.csv"))
