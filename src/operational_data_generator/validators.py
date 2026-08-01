"""Hard-reject validation for the accepted operational dataset."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any

from .config import TARGET_COUNTS, WEATHER_LOCATIONS
from .entities import SCENARIOS


class ValidationError(ValueError):
    """Raised when accepted source data violates a hard contract rule."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def _unique_required(rows: list[dict[str, Any]], field: str, entity: str) -> set[Any]:
    values = [row.get(field) for row in rows]
    _require(all(value not in (None, "") for value in values), f"{entity}.{field} is required")
    _require(len(values) == len(set(values)), f"duplicate {entity}.{field}")
    return set(values)


def validate_dataset(data: dict[str, list[dict[str, Any]]]) -> None:
    _require(set(data) == set(TARGET_COUNTS), "dataset must contain exactly the 12 approved entities")
    for name, count in TARGET_COUNTS.items():
        _require(len(data[name]) == count, f"{name} expected {count} rows")

    region_ids = _unique_required(data["regions"], "region_id", "region")
    office_ids = _unique_required(data["offices"], "office_id", "office")
    employee_ids = _unique_required(data["employees"], "employee_id", "employee")
    activity_ids = _unique_required(data["activities"], "activity_id", "activity")
    type_ids = _unique_required(data["equipment_types"], "equipment_type_id", "equipment_type")
    project_ids = _unique_required(data["projects"], "project_id", "project")
    site_ids = _unique_required(data["job_sites"], "job_site_id", "job_site")
    crew_ids = _unique_required(data["crews"], "crew_id", "crew")
    equipment_ids = _unique_required(data["equipment"], "equipment_id", "equipment")
    schedule_ids = _unique_required(data["field_schedules"], "field_schedule_id", "field_schedule")
    _unique_required(data["equipment_assignments"], "assignment_id", "equipment_assignment")
    _unique_required(data["safety_thresholds"], "threshold_id", "safety_threshold")

    for name, key in (("regions", "region_code"), ("offices", "office_code"), ("employees", "employee_number"),
                      ("activities", "activity_code"), ("equipment_types", "equipment_type_code"),
                      ("projects", "project_code"), ("job_sites", "job_site_code"),
                      ("crews", "crew_code"), ("equipment", "equipment_code")):
        _unique_required(data[name], key, name)

    _require(all(r["region_id"] in region_ids for r in data["offices"]), "office has orphan region")
    _require(all(r["home_office_id"] in office_ids for r in data["employees"]), "employee has orphan office")
    employees = {r["employee_id"]: r for r in data["employees"]}
    for row in data["projects"]:
        _require(row["office_id"] in office_ids, "project has orphan office")
        _require(row["project_manager_employee_id"] in employee_ids and row["field_manager_employee_id"] in employee_ids, "project has orphan manager")
        _require(row["status"] in {"Planned", "Active", "Closed", "Cancelled"}, "invalid project status")
        _require(date.fromisoformat(row["project_end_date"]) >= date.fromisoformat(row["project_start_date"]), "invalid project dates")
    sites = {r["job_site_id"]: r for r in data["job_sites"]}
    for row in data["job_sites"]:
        _require(row["project_id"] in project_ids, "job site has orphan project")
        _require(row["weather_location_code"] in WEATHER_LOCATIONS, "invalid weather location")
    for row in data["crews"]:
        _require(row["home_office_id"] in office_ids, "crew has orphan office")
        _require(row["crew_lead_employee_id"] in employee_ids and employees[row["crew_lead_employee_id"]]["employment_status"] == "Active", "crew lead must be active")
    _require(all(r["equipment_type_id"] in type_ids for r in data["equipment"]), "equipment has orphan type")

    schedules = {r["field_schedule_id"]: r for r in data["field_schedules"]}
    allowed_statuses = {"Scheduled", "In Progress", "Completed", "Delayed", "Cancelled", "Rescheduled"}
    for row in data["field_schedules"]:
        start, end = datetime.fromisoformat(row["scheduled_start_timestamp"]), datetime.fromisoformat(row["scheduled_end_timestamp"])
        _require(end > start and row["scheduled_date"] == start.date().isoformat(), "invalid schedule timestamps/date")
        _require(row["planned_crew_hours"] == (end - start).total_seconds() / 3600, "crew hours differ from duration")
        _require(row["planned_labor_hours"] == row["planned_crew_hours"] * row["planned_crew_size"], "invalid planned labor hours")
        _require(row["project_id"] in project_ids and row["job_site_id"] in site_ids and row["crew_id"] in crew_ids and row["activity_id"] in activity_ids, "schedule has orphan FK")
        _require(sites[row["job_site_id"]]["project_id"] == row["project_id"], "schedule project/site mismatch")
        _require(row["status"] in allowed_statuses, "invalid schedule status")
        predecessor = row["rescheduled_from_schedule_id"]
        if predecessor != "":
            _require(predecessor in schedule_ids and predecessor != row["field_schedule_id"], "invalid reschedule predecessor")
            _require(schedules[predecessor]["status"] == "Rescheduled", "predecessor must be Rescheduled")
    for row in data["field_schedules"]:
        seen: set[int] = set()
        current = row
        while current["rescheduled_from_schedule_id"] != "":
            predecessor = current["rescheduled_from_schedule_id"]
            _require(predecessor not in seen, "cyclic reschedule lineage")
            seen.add(predecessor)
            current = schedules[predecessor]
    predecessors = {r["rescheduled_from_schedule_id"] for r in data["field_schedules"] if r["rescheduled_from_schedule_id"] != ""}
    _require(all(r["field_schedule_id"] in predecessors for r in data["field_schedules"] if r["status"] == "Rescheduled"), "rescheduled row lacks successor")
    _require(set(SCENARIOS).issubset({r["scenario_id"] for r in data["field_schedules"]}), "missing scenario coverage")

    windows: dict[int, list[tuple[datetime, datetime]]] = defaultdict(list)
    for row in data["equipment_assignments"]:
        start, end = datetime.fromisoformat(row["assignment_start_timestamp"]), datetime.fromisoformat(row["assignment_end_timestamp"])
        _require(end > start, "invalid assignment window")
        _require(row["equipment_id"] in equipment_ids and row["job_site_id"] in site_ids, "assignment has orphan FK")
        _require(row["project_id"] == sites[row["job_site_id"]]["project_id"], "assignment project/site mismatch")
        _require(all(end <= prior_start or start >= prior_end for prior_start, prior_end in windows[row["equipment_id"]]), "overlapping equipment assignment")
        windows[row["equipment_id"]].append((start, end))
    _require(any(r["scenario_id"] == "equipment_relocation" for r in data["equipment_assignments"]), "missing relocation scenario")

    threshold_keys: set[tuple[Any, ...]] = set()
    for row in data["safety_thresholds"]:
        _require(row["activity_id"] in activity_ids, "threshold has orphan activity")
        _require(row["equipment_type_id"] == "" or row["equipment_type_id"] in type_ids, "threshold has orphan type")
        _require(bool(row["recommended_action_code"]), "threshold action required")
        _require(not (row["severity"] == "CRITICAL") or row["override_flag"] is True, "critical threshold must override")
        weather = row["metric_code"] == "WEATHER_CODE"
        _require((weather and row["weather_code_set"] and row["threshold_value"] == "") or (not weather and row["threshold_value"] and row["weather_code_set"] == ""), "incompatible threshold structure")
        key = (row["activity_id"], row["metric_code"], row["severity"], row["equipment_type_id"])
        _require(key not in threshold_keys, "overlapping/ambiguous active threshold")
        threshold_keys.add(key)
