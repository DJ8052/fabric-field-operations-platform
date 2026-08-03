from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from operational_silver_validation import validate_master_entities


FIXED_TIME = datetime(2026, 8, 3, 12, tzinfo=timezone.utc)


def clean_dataset() -> dict[str, list[dict]]:
    return {
        "regions": [{"region_id": 1, "region_code": "REG-001", "region_name": "North"}],
        "offices": [{"office_id": 10, "office_code": "OFF-001", "office_name": "Dallas", "region_id": 1}],
        "employees": [
            {"employee_id": 100, "employee_number": "EMP-0001", "employee_name": "Lead", "home_office_id": 10, "employment_status": "Active"},
            {"employee_id": 101, "employee_number": "EMP-0002", "employee_name": "Manager", "home_office_id": 10, "employment_status": "Active"},
        ],
        "projects": [{"project_id": 20, "project_code": "PRJ-001", "project_name": "Project", "office_id": 10, "project_manager_employee_id": 101, "field_manager_employee_id": 101, "status": "Active"}],
        "job_sites": [{"job_site_id": 30, "job_site_code": "SITE-001", "job_site_name": "Site", "project_id": 20, "weather_location_code": "TX-DAL"}],
        "crews": [{"crew_id": 40, "crew_code": "CREW-001", "home_office_id": 10, "crew_lead_employee_id": 100, "crew_status": "Active"}],
        "activities": [{"activity_id": 50, "activity_code": "ACT-001", "activity_name": "Work"}],
        "equipment_types": [{"equipment_type_id": 60, "equipment_type_code": "ET-001", "equipment_type_name": "Crane"}],
        "equipment": [{"equipment_id": 70, "equipment_code": "EQ-001", "equipment_type_id": 60, "equipment_status": "Available"}],
    }


def run(data: dict) -> object:
    return validate_master_entities(data, "run-1", clock=lambda: FIXED_TIME, timer=lambda: 1.0)


def by_entity(output: object, entity: str):
    return next(item for item in output.entities if item.entity == entity)


def test_clean_records_for_all_master_entities_are_accepted() -> None:
    output = run(clean_dataset())
    assert all(item.summary.rows_quarantined == 0 for item in output.entities)
    assert all(item.summary.rows_accepted == item.summary.rows_read for item in output.entities)


def test_critical_failures_are_quarantined_and_multiple_failures_preserved() -> None:
    data = clean_dataset()
    data["job_sites"][0]["job_site_code"] = ""
    data["job_sites"][0]["project_id"] = 999
    data["job_sites"][0]["weather_location_code"] = "TX-UNKNOWN"
    result = by_entity(run(data), "job_sites")
    assert result.accepted_records == ()
    assert len(result.quarantine_records) == 1
    rule_ids = {item.rule_id for item in result.quarantine_records[0].critical_violations}
    assert {"JBS-001", "JBS-002", "JBS-004", "XEN-001", "XEN-007", "XEN-010"} <= rule_ids


def test_warning_record_remains_accepted_and_source_is_unchanged() -> None:
    data = clean_dataset()
    data["regions"][0]["region_name"] = ""
    original = deepcopy(data["regions"][0])
    result = by_entity(run(data), "regions")
    assert result.accepted_records == (original,)
    assert [item.rule_id for item in result.validation_results] == ["REG-003"]
    assert data["regions"][0] == original


def test_output_records_do_not_share_nested_mutable_source_values() -> None:
    data = clean_dataset()
    data["regions"][0]["source_metadata"] = {"batch": ["original"]}
    output = run(data)
    accepted = by_entity(output, "regions").accepted_records[0]
    accepted["source_metadata"]["batch"].append("output-only")
    assert data["regions"][0]["source_metadata"] == {"batch": ["original"]}


def test_duplicate_keys_quarantine_every_participant() -> None:
    data = clean_dataset()
    duplicate = deepcopy(data["activities"][0])
    duplicate["activity_id"] = 51
    data["activities"].append(duplicate)
    result = by_entity(run(data), "activities")
    assert len(result.quarantine_records) == 2
    assert all({"ACT-002", "XEN-009"} <= {violation.rule_id for violation in row.critical_violations} for row in result.quarantine_records)


def test_crew_lead_status_office_and_missing_rules() -> None:
    data = clean_dataset()
    data["employees"][0]["employment_status"] = "Terminated"
    data["employees"][0]["home_office_id"] = 999
    crew_result = by_entity(run(data), "crews")
    employee_result = by_entity(run(data), "employees")
    assert any(result.rule_id == "CRW-004" and result.severity == "Critical" for result in crew_result.validation_results)
    assert {result.rule_id for result in crew_result.validation_results} >= {"CRW-005", "XEN-008"}
    assert any(result.rule_id == "EMP-004" for result in employee_result.validation_results)
    data = clean_dataset()
    data["crews"][0]["crew_lead_employee_id"] = ""
    crew_result = by_entity(run(data), "crews")
    assert crew_result.accepted_records
    assert [result.rule_id for result in crew_result.validation_results] == ["CRW-006"]
