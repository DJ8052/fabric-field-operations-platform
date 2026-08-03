"""Entity-level rules for the first operational Silver master slice."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .common_validations import duplicate_groups, invalid_domain_indices, missing_indices
from .models import Finding

MASTER_ENTITIES = (
    "regions", "offices", "employees", "projects", "job_sites", "crews",
    "activities", "equipment_types", "equipment",
)

PRIMARY_KEYS = {
    "regions": "region_id", "offices": "office_id", "employees": "employee_id",
    "projects": "project_id", "job_sites": "job_site_id", "crews": "crew_id",
    "activities": "activity_id", "equipment_types": "equipment_type_id",
    "equipment": "equipment_id",
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
}


def entity_findings(entity: str, records: Sequence[Mapping[str, Any]]) -> tuple[Finding, ...]:
    findings: list[Finding] = []
    key, required_rule, duplicate_rule = BUSINESS_KEY_RULES[entity]
    for index in missing_indices(records, key):
        findings.append(Finding(entity, index, required_rule, f"{entity}.{key} is null or empty"))
    for group in duplicate_groups(records, key):
        for index in group:
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
    return tuple(findings)
