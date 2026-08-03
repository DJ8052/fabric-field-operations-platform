from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

import pytest

from operational_silver_validation import RULE_REGISTRY, validate_operational_entities
from operational_data_generator import generate_dataset
from test_silver_master_entities import clean_dataset

FIXED_TIME = datetime(2026, 8, 3, 12, tzinfo=timezone.utc)


def schedule(schedule_id: int = 1, **changes) -> dict:
    row = {
        "field_schedule_id": str(schedule_id), "project_id": "20", "job_site_id": "30",
        "crew_id": "40", "activity_id": "50",
        "scheduled_start_timestamp": "2026-02-01T07:00:00",
        "scheduled_end_timestamp": "2026-02-01T15:00:00", "scheduled_date": "2026-02-01",
        "planned_crew_hours": "8", "planned_crew_size": "5", "planned_labor_hours": "40",
        "status": "Scheduled", "rescheduled_from_schedule_id": "", "scenario_id": "normal_operations",
    }
    row.update(changes)
    return row


def assignment(assignment_id: int = 1, **changes) -> dict:
    row = {
        "assignment_id": str(assignment_id), "equipment_id": "70", "job_site_id": "30",
        "project_id": "20", "assignment_start_timestamp": "2026-02-01T06:00:00",
        "assignment_end_timestamp": "2026-02-01T16:00:00", "assignment_note": "planned",
    }
    row.update(changes)
    return row


def threshold(threshold_id: int = 1, **changes) -> dict:
    row = {
        "threshold_id": str(threshold_id), "activity_id": "50", "equipment_type_id": "",
        "metric_code": "WIND_GUST_MPH", "comparison_operator": ">=", "unit": "mph",
        "threshold_value_or_code_set": "35", "threshold_value": "35", "weather_code_set": "",
        "severity": "HIGH", "recommended_action_code": "DELAY_WORK",
        "effective_start_date": "2026-01-01", "effective_end_date": "",
        "is_active": "True", "override_flag": "False",
    }
    row.update(changes)
    return row


def operational_dataset() -> dict[str, list[dict]]:
    data = clean_dataset()
    # Notebook CSV reads preserve source text, so align FK values as strings.
    for rows in data.values():
        for row in rows:
            for key, value in tuple(row.items()):
                if key.endswith("_id") and value != "":
                    row[key] = str(value)
    data["field_schedules"] = [schedule()]
    data["equipment_assignments"] = [assignment()]
    data["safety_thresholds"] = [threshold()]
    return data


def run(data: dict):
    return validate_operational_entities(data, "transactional", clock=lambda: FIXED_TIME, timer=lambda: 1.0)


def entity_output(output, entity: str):
    return next(item for item in output.entities if item.entity == entity)


def rules(output, entity: str) -> list[str]:
    return [result.rule_id for result in entity_output(output, entity).validation_results]


def test_valid_transactional_records_are_accepted() -> None:
    output = run(operational_dataset())
    for entity in ("field_schedules", "equipment_assignments", "safety_thresholds"):
        assert entity_output(output, entity).summary.rows_accepted == 1


def test_generated_accepted_dataset_has_no_silver_quarantine() -> None:
    output = run(generate_dataset())
    assert output.summary.rows_quarantined == 0


@pytest.mark.parametrize("end", ["2026-02-01T07:00:00", "2026-02-01T06:59:59", "not-a-timestamp"])
def test_schedule_invalid_window_is_critical(end: str) -> None:
    data = operational_dataset()
    data["field_schedules"][0]["scheduled_end_timestamp"] = end
    result = entity_output(run(data), "field_schedules")
    assert "FSD-001" in rules(run(data), "field_schedules")
    assert result.summary.rows_quarantined == 1


def test_schedule_date_and_hours_rules() -> None:
    data = operational_dataset()
    data["field_schedules"][0]["scheduled_date"] = "2026-02-02"
    assert "FSD-002" in rules(run(data), "field_schedules")
    data = operational_dataset()
    data["field_schedules"][0]["planned_crew_hours"] = "7.999"
    data["field_schedules"][0]["planned_labor_hours"] = "39.995"
    result = entity_output(run(data), "field_schedules")
    assert "FSD-003" in [item.rule_id for item in result.validation_results]
    assert result.summary.rows_accepted == 1
    data["field_schedules"][0]["planned_labor_hours"] = "39"
    result = entity_output(run(data), "field_schedules")
    assert "FSD-004" in [item.rule_id for item in result.validation_results]
    assert result.summary.rows_quarantined == 1


def test_schedule_project_site_status_and_successor_rules() -> None:
    data = operational_dataset()
    data["field_schedules"][0]["project_id"] = "999"
    assert {"FSD-005", "XEN-002"} <= set(rules(run(data), "field_schedules"))
    data = operational_dataset()
    data["field_schedules"][0]["status"] = "Unknown"
    assert "FSD-010" in rules(run(data), "field_schedules")
    data = operational_dataset()
    data["field_schedules"][0]["status"] = "Rescheduled"
    assert "FSD-007" in rules(run(data), "field_schedules")


def test_completed_predecessor_quarantines_both_lineage_records() -> None:
    data = operational_dataset()
    data["field_schedules"] = [
        schedule(1, status="Completed"),
        schedule(2, rescheduled_from_schedule_id="1"),
    ]
    result = entity_output(run(data), "field_schedules")
    assert result.summary.rows_quarantined == 2
    assert all("FSD-006" in {item.rule_id for item in row.critical_violations} for row in result.quarantine_records)


def test_valid_lineage_chain_has_no_lineage_results() -> None:
    data = operational_dataset()
    data["field_schedules"] = [schedule(1, status="Rescheduled"), schedule(2, rescheduled_from_schedule_id="1")]
    assert not ({"FSD-006", "FSD-007", "FSD-009", "XEN-004"} & set(rules(run(data), "field_schedules")))


@pytest.mark.parametrize(
    "rows, expected_count",
    [
        ([schedule(1, rescheduled_from_schedule_id="1")], 1),
        ([schedule(1, rescheduled_from_schedule_id="2"), schedule(2, rescheduled_from_schedule_id="1")], 2),
        ([schedule(1, rescheduled_from_schedule_id="3"), schedule(2, rescheduled_from_schedule_id="1"), schedule(3, rescheduled_from_schedule_id="2")], 3),
    ],
)
def test_lineage_cycles_quarantine_all_cycle_members(rows: list[dict], expected_count: int) -> None:
    data = operational_dataset()
    data["field_schedules"] = rows
    result = entity_output(run(data), "field_schedules")
    assert result.summary.rows_quarantined == expected_count
    assert {"FSD-009", "XEN-004"} <= set(rules(run(data), "field_schedules"))


def test_fsd_008_remains_explicitly_unimplemented() -> None:
    assert "FSD-008" not in RULE_REGISTRY


@pytest.mark.parametrize("end", ["2026-02-01T06:00:00", "2026-01-31T23:00:00", "bad"])
def test_assignment_invalid_period_is_critical(end: str) -> None:
    data = operational_dataset()
    data["equipment_assignments"][0]["assignment_end_timestamp"] = end
    assert "EQA-001" in rules(run(data), "equipment_assignments")


def test_assignment_open_period_and_project_site_behavior() -> None:
    data = operational_dataset()
    data["equipment_assignments"][0]["assignment_end_timestamp"] = ""
    assert entity_output(run(data), "equipment_assignments").summary.rows_accepted == 1
    data["equipment_assignments"][0]["project_id"] = "999"
    assert {"EQA-002", "XEN-003"} <= set(rules(run(data), "equipment_assignments"))


def test_assignment_nonoverlap_overlap_and_open_overlap() -> None:
    data = operational_dataset()
    data["equipment_assignments"] = [assignment(1), assignment(2, assignment_start_timestamp="2026-02-02T06:00:00", assignment_end_timestamp="2026-02-02T16:00:00")]
    assert "EQA-003" not in rules(run(data), "equipment_assignments")
    data["equipment_assignments"][1].update(assignment_start_timestamp="2026-02-01T12:00:00", assignment_end_timestamp="2026-02-01T18:00:00")
    result = entity_output(run(data), "equipment_assignments")
    assert result.summary.rows_quarantined == 2
    assert {"EQA-003", "XEN-005"} <= set(rules(run(data), "equipment_assignments"))
    data["equipment_assignments"][0]["assignment_end_timestamp"] = ""
    assert entity_output(run(data), "equipment_assignments").summary.rows_quarantined == 2


def test_adjacent_assignment_boundary_is_info_and_remains_accepted() -> None:
    data = operational_dataset()
    data["equipment_assignments"] = [assignment(1), assignment(2, assignment_start_timestamp="2026-02-01T16:00:00", assignment_end_timestamp="2026-02-02T02:00:00")]
    result = entity_output(run(data), "equipment_assignments")
    assert result.summary.rows_accepted == 2
    assert result.summary.info_result_count == 2
    assert set(rules(run(data), "equipment_assignments")) == {"EQA-004"}


def test_safety_effective_dates_and_nonoverlap() -> None:
    data = operational_dataset()
    data["safety_thresholds"][0]["effective_end_date"] = "2025-12-31"
    assert "SFT-001" in rules(run(data), "safety_thresholds")
    data = operational_dataset()
    data["safety_thresholds"] = [threshold(1, effective_end_date="2026-01-31"), threshold(2, effective_start_date="2026-02-01")]
    assert "SFT-002" not in rules(run(data), "safety_thresholds")


@pytest.mark.parametrize("equipment_type", ["", "60"])
def test_safety_overlap_scope_and_open_end(equipment_type: str) -> None:
    data = operational_dataset()
    data["safety_thresholds"] = [threshold(1, equipment_type_id=equipment_type), threshold(2, equipment_type_id=equipment_type, effective_start_date="2026-02-01")]
    result = entity_output(run(data), "safety_thresholds")
    assert result.summary.rows_quarantined == 2
    assert {"SFT-002", "XEN-006"} <= set(rules(run(data), "safety_thresholds"))


def test_weather_and_numeric_threshold_structures() -> None:
    data = operational_dataset()
    data["safety_thresholds"] = [threshold(1, metric_code="WEATHER_CODE", comparison_operator="IN", unit="wmo_code", threshold_value_or_code_set="95|96|99", threshold_value="", weather_code_set="95|96|99", severity="CRITICAL", override_flag="True")]
    assert entity_output(run(data), "safety_thresholds").summary.rows_accepted == 1
    for changes, expected in (
        ({"comparison_operator": ">="}, "SFT-003"),
        ({"weather_code_set": "", "threshold_value": "95"}, "SFT-004"),
    ):
        invalid = deepcopy(data)
        invalid["safety_thresholds"][0].update(changes)
        assert expected in rules(run(invalid), "safety_thresholds")
    data = operational_dataset()
    assert entity_output(run(data), "safety_thresholds").summary.rows_accepted == 1
    data["safety_thresholds"][0]["threshold_value"] = "not-numeric"
    assert "SFT-005" in rules(run(data), "safety_thresholds")
    data = operational_dataset()
    data["safety_thresholds"][0]["weather_code_set"] = "95"
    assert "SFT-005" in rules(run(data), "safety_thresholds")


def test_safety_action_override_and_conflicting_rules() -> None:
    data = operational_dataset()
    data["safety_thresholds"][0]["recommended_action_code"] = ""
    assert "SFT-006" in rules(run(data), "safety_thresholds")
    data = operational_dataset()
    data["safety_thresholds"][0].update(severity="CRITICAL", override_flag="False")
    assert "SFT-007" in rules(run(data), "safety_thresholds")
    data = operational_dataset()
    data["safety_thresholds"] = [threshold(1), threshold(2, threshold_value_or_code_set="40", threshold_value="40", recommended_action_code="STOP_WORK")]
    result = entity_output(run(data), "safety_thresholds")
    assert result.summary.rows_quarantined == 2
    assert {"SFT-002", "SFT-008", "XEN-006"} <= set(rules(run(data), "safety_thresholds"))


def test_transactional_engine_is_deterministic_and_summaries_are_accurate() -> None:
    data = operational_dataset()
    data["field_schedules"][0]["planned_crew_hours"] = "7"
    first = run(data)
    second = run(data)
    assert first == second
    assert first.summary.rows_read == sum(item.summary.rows_read for item in first.entities)
    assert first.summary.warning_result_count >= 1
