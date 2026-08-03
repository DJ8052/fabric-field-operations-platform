"""Entity-level rules for the first operational Silver master slice."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .common_validations import (
    decimal_equal,
    duplicate_groups,
    invalid_domain_indices,
    is_missing,
    missing_indices,
    parse_decimal,
    parse_iso_date,
    parse_iso_timestamp,
)
from .models import Finding

MASTER_ENTITIES = (
    "regions", "offices", "employees", "projects", "job_sites", "crews",
    "activities", "equipment_types", "equipment",
)

TRANSACTIONAL_ENTITIES = (
    "field_schedules", "equipment_assignments", "safety_thresholds",
)

ALL_ENTITIES = MASTER_ENTITIES + TRANSACTIONAL_ENTITIES

PRIMARY_KEYS = {
    "regions": "region_id", "offices": "office_id", "employees": "employee_id",
    "projects": "project_id", "job_sites": "job_site_id", "crews": "crew_id",
    "activities": "activity_id", "equipment_types": "equipment_type_id",
    "equipment": "equipment_id",
    "field_schedules": "field_schedule_id",
    "equipment_assignments": "assignment_id",
    "safety_thresholds": "threshold_id",
}

BUSINESS_KEY_RULES = {
    "regions": ("region_code", "REG-001", "REG-002"),
    "offices": ("office_code", "OFF-001", "OFF-003"),
    "employees": ("employee_number", "EMP-001", "EMP-003"),
    "projects": ("project_code", "PRJ-001", "PRJ-002"),
    "job_sites": ("job_site_code", "JBS-001", "JBS-003"),
    "crews": ("crew_code", "CRW-001", "CRW-003"),
    "activities": ("activity_code", "ACT-001", "ACT-002"),
    "equipment_types": ("equipment_type_code", "EQT-001", "EQT-002"),
    "equipment": ("equipment_code", "EQP-001", "EQP-003"),
}

WARNING_FIELDS = {
    "regions": ("region_name", "REG-003"),
    "offices": ("office_name", "OFF-004"),
    "projects": ("project_name", "PRJ-003"),
    "activities": ("activity_name", "ACT-003"),
    "equipment_types": ("equipment_type_name", "EQT-003"),
    "equipment": ("equipment_status", "EQP-004"),
}

CRITICAL_VALUE_FIELDS = {
    "regions": ("region_id", "region_code"),
    "offices": ("office_id", "office_code", "region_id"),
    "employees": ("employee_id", "employee_number", "employee_name", "home_office_id", "employment_status"),
    "projects": ("project_id", "project_code", "office_id", "project_manager_employee_id", "field_manager_employee_id", "status"),
    "job_sites": ("job_site_id", "job_site_code", "job_site_name", "project_id", "weather_location_code"),
    "crews": ("crew_id", "crew_code", "home_office_id", "crew_status"),
    "activities": ("activity_id", "activity_code"),
    "equipment_types": ("equipment_type_id", "equipment_type_code"),
    "equipment": ("equipment_id", "equipment_code", "equipment_type_id"),
    "field_schedules": (
        "field_schedule_id", "project_id", "job_site_id", "crew_id", "activity_id",
        "scheduled_start_timestamp", "scheduled_end_timestamp", "scheduled_date",
        "planned_crew_hours", "planned_crew_size", "planned_labor_hours", "status",
    ),
    "equipment_assignments": (
        "assignment_id", "equipment_id", "job_site_id", "project_id",
        "assignment_start_timestamp",
    ),
    "safety_thresholds": (
        "threshold_id", "activity_id", "metric_code", "comparison_operator", "unit",
        "threshold_value_or_code_set", "severity", "recommended_action_code",
        "effective_start_date", "is_active", "override_flag",
    ),
}

TRANSACTIONAL_IDS = {
    "field_schedules": "field_schedule_id",
    "equipment_assignments": "assignment_id",
    "safety_thresholds": "threshold_id",
}

SCHEDULE_STATUSES = {
    "Scheduled", "In Progress", "Completed", "Delayed", "Cancelled", "Rescheduled",
}

VERIFIED_NUMERIC_METRICS = {
    "WIND_GUST_MPH", "HEAT_INDEX_F", "PRECIPITATION_IN",
}


def entity_findings(entity: str, records: Sequence[Mapping[str, Any]]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    if entity in BUSINESS_KEY_RULES:
        key, required_rule, duplicate_rule = BUSINESS_KEY_RULES[entity]
        for index in missing_indices(records, key):
            findings.append(Finding(entity, index, required_rule, f"{entity}.{key} is null or empty"))
    else:
        key = TRANSACTIONAL_IDS[entity]
        duplicate_rule = "XEN-009"
    for group in duplicate_groups(records, key):
        for index in group:
            if entity in BUSINESS_KEY_RULES:
                findings.append(Finding(entity, index, duplicate_rule, f"duplicate {entity}.{key}: {records[index].get(key)!r}"))
            findings.append(Finding(entity, index, "XEN-009", f"duplicate business key {entity}.{key}: {records[index].get(key)!r}"))
    warning = WARNING_FIELDS.get(entity)
    if warning:
        field, rule_id = warning
        for index in missing_indices(records, field):
            findings.append(Finding(entity, index, rule_id, f"{entity}.{field} is null or empty"))
    for field in CRITICAL_VALUE_FIELDS[entity]:
        for index in missing_indices(records, field):
            findings.append(Finding(entity, index, "XEN-010", f"Critical value {entity}.{field} is null or empty"))
    if entity == "job_sites":
        for index in invalid_domain_indices(records, "weather_location_code", ("TX-DAL", "TX-HOU", "TX-AUS")):
            findings.append(Finding(entity, index, "JBS-004", "weather_location_code is outside the approved domain"))
            findings.append(Finding(entity, index, "XEN-007", "weather_location_code is outside the approved domain"))
    elif entity == "field_schedules":
        findings.extend(_field_schedule_findings(records))
    elif entity == "equipment_assignments":
        findings.extend(_equipment_assignment_findings(records))
    elif entity == "safety_thresholds":
        findings.extend(_safety_threshold_findings(records))
    return tuple(findings)


def _field_schedule_findings(records: Sequence[Mapping[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for index, row in enumerate(records):
        start = parse_iso_timestamp(row.get("scheduled_start_timestamp"))
        end = parse_iso_timestamp(row.get("scheduled_end_timestamp"))
        try:
            valid_window = start is not None and end is not None and end > start
        except TypeError:  # Mixed aware/naive timestamps; no timezone coercion is authorized.
            valid_window = False
        if not valid_window:
            findings.append(Finding("field_schedules", index, "FSD-001", "schedule timestamps are malformed or end is not greater than start"))
        scheduled_date = parse_iso_date(row.get("scheduled_date"))
        if start is None or scheduled_date is None or scheduled_date != start.date():
            findings.append(Finding("field_schedules", index, "FSD-002", "scheduled_date does not equal the start timestamp date"))
        if valid_window:
            duration = parse_decimal((end - start).total_seconds())
            hours = duration / parse_decimal(3600) if duration is not None else None
            if hours is None or not decimal_equal(row.get("planned_crew_hours"), hours):
                findings.append(Finding("field_schedules", index, "FSD-003", "planned_crew_hours differs from schedule duration"))
        crew_hours = parse_decimal(row.get("planned_crew_hours"))
        crew_size = parse_decimal(row.get("planned_crew_size"))
        labor_hours = parse_decimal(row.get("planned_labor_hours"))
        if crew_hours is None or crew_size is None or labor_hours is None or not decimal_equal(labor_hours, crew_hours * crew_size):
            findings.append(Finding("field_schedules", index, "FSD-004", "planned_labor_hours does not equal planned_crew_hours multiplied by planned_crew_size"))
        if row.get("status") not in SCHEDULE_STATUSES:
            findings.append(Finding("field_schedules", index, "FSD-010", "status is outside the approved Field Schedule domain"))
    return findings


def _equipment_assignment_findings(records: Sequence[Mapping[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for index, row in enumerate(records):
        start = parse_iso_timestamp(row.get("assignment_start_timestamp"))
        end_value = row.get("assignment_end_timestamp")
        end = None if is_missing(end_value) else parse_iso_timestamp(end_value)
        try:
            valid_end = is_missing(end_value) or (end is not None and start is not None and end > start)
        except TypeError:
            valid_end = False
        if start is None or not valid_end:
            findings.append(Finding("equipment_assignments", index, "EQA-001", "assignment timestamps are malformed or end is not greater than start"))
    return findings


def _is_true(value: Any) -> bool:
    return value is True or value == "True"


def _safety_threshold_findings(records: Sequence[Mapping[str, Any]]) -> list[Finding]:
    findings: list[Finding] = []
    for index, row in enumerate(records):
        start = parse_iso_date(row.get("effective_start_date"))
        end_value = row.get("effective_end_date")
        end = None if is_missing(end_value) else parse_iso_date(end_value)
        if start is None or (not is_missing(end_value) and (end is None or end < start)):
            findings.append(Finding("safety_thresholds", index, "SFT-001", "effective dates are malformed or end precedes start"))
        metric = row.get("metric_code")
        operator = row.get("comparison_operator")
        if (metric == "WEATHER_CODE" and operator != "IN") or (metric in VERIFIED_NUMERIC_METRICS and operator != ">="):
            findings.append(Finding("safety_thresholds", index, "SFT-003", "comparison_operator is incompatible with the verified metric structure"))
        if metric == "WEATHER_CODE":
            if is_missing(row.get("weather_code_set")) or not is_missing(row.get("threshold_value")):
                findings.append(Finding("safety_thresholds", index, "SFT-004", "WEATHER_CODE threshold payload is invalid"))
        else:
            if parse_decimal(row.get("threshold_value")) is None or not is_missing(row.get("weather_code_set")):
                findings.append(Finding("safety_thresholds", index, "SFT-005", "numeric threshold payload is invalid"))
        if is_missing(row.get("recommended_action_code")):
            findings.append(Finding("safety_thresholds", index, "SFT-006", "recommended_action_code is null or empty"))
        if row.get("severity") == "CRITICAL" and not _is_true(row.get("override_flag")):
            findings.append(Finding("safety_thresholds", index, "SFT-007", "CRITICAL threshold does not set override_flag to true"))
    return findings
