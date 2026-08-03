"""Relationship registry and master-entity relationship checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Mapping, Sequence

from .common_validations import invalid_foreign_key_indices, is_missing, parse_iso_date, parse_iso_timestamp
from .models import Finding


@dataclass(frozen=True)
class ForeignKeyRelationship:
    source_entity: str
    source_field: str
    target_entity: str
    target_field: str
    nullable: bool = False


FOREIGN_KEY_RELATIONSHIPS = (
    ForeignKeyRelationship("offices", "region_id", "regions", "region_id"),
    ForeignKeyRelationship("employees", "home_office_id", "offices", "office_id"),
    ForeignKeyRelationship("projects", "office_id", "offices", "office_id"),
    ForeignKeyRelationship("projects", "project_manager_employee_id", "employees", "employee_id"),
    ForeignKeyRelationship("projects", "field_manager_employee_id", "employees", "employee_id"),
    ForeignKeyRelationship("job_sites", "project_id", "projects", "project_id"),
    ForeignKeyRelationship("crews", "home_office_id", "offices", "office_id"),
    ForeignKeyRelationship("crews", "crew_lead_employee_id", "employees", "employee_id", True),
    ForeignKeyRelationship("field_schedules", "project_id", "projects", "project_id"),
    ForeignKeyRelationship("field_schedules", "job_site_id", "job_sites", "job_site_id"),
    ForeignKeyRelationship("field_schedules", "crew_id", "crews", "crew_id"),
    ForeignKeyRelationship("field_schedules", "activity_id", "activities", "activity_id"),
    ForeignKeyRelationship("field_schedules", "rescheduled_from_schedule_id", "field_schedules", "field_schedule_id", True),
    ForeignKeyRelationship("equipment", "equipment_type_id", "equipment_types", "equipment_type_id"),
    ForeignKeyRelationship("equipment_assignments", "equipment_id", "equipment", "equipment_id"),
    ForeignKeyRelationship("equipment_assignments", "job_site_id", "job_sites", "job_site_id"),
    ForeignKeyRelationship("equipment_assignments", "project_id", "projects", "project_id"),
    ForeignKeyRelationship("safety_thresholds", "activity_id", "activities", "activity_id"),
    ForeignKeyRelationship("safety_thresholds", "equipment_type_id", "equipment_types", "equipment_type_id", True),
)


def foreign_key_failures(dataset: Mapping[str, Sequence[Mapping[str, Any]]], implemented_entities: set[str]) -> tuple[tuple[ForeignKeyRelationship, int], ...]:
    failures: list[tuple[ForeignKeyRelationship, int]] = []
    for relationship in FOREIGN_KEY_RELATIONSHIPS:
        if relationship.source_entity not in implemented_entities:
            continue
        source = dataset.get(relationship.source_entity, ())
        targets = {row.get(relationship.target_field) for row in dataset.get(relationship.target_entity, ())}
        for index in invalid_foreign_key_indices(source, relationship.source_field, targets, nullable=relationship.nullable):
            failures.append((relationship, index))
    return tuple(failures)


def crew_relationship_failures(dataset: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[tuple[str, int], ...]:
    employees = {row.get("employee_id"): row for row in dataset.get("employees", ())}
    failures: list[tuple[str, int]] = []
    for index, crew in enumerate(dataset.get("crews", ())):
        lead_id = crew.get("crew_lead_employee_id")
        if is_missing(lead_id):
            failures.append(("missing", index))
            continue
        lead = employees.get(lead_id)
        if lead is None or lead.get("employment_status") != "Active":
            failures.append(("inactive", index))
        if lead is not None and lead.get("home_office_id") != crew.get("home_office_id"):
            failures.append(("office", index))
    return tuple(failures)


def terminated_lead_employee_indices(dataset: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[int, ...]:
    employees = dataset.get("employees", ())
    index_by_id = {row.get("employee_id"): index for index, row in enumerate(employees)}
    affected: set[int] = set()
    for crew in dataset.get("crews", ()):
        index = index_by_id.get(crew.get("crew_lead_employee_id"))
        if index is not None and employees[index].get("employment_status") == "Terminated":
            affected.add(index)
    return tuple(sorted(affected))


def relationship_findings(dataset: Mapping[str, Sequence[Mapping[str, Any]]], implemented_entities: set[str]) -> tuple[Finding, ...]:
    """Evaluate implemented relationship rules and return rule-addressed findings."""
    findings: list[Finding] = []
    specific_fk_rules = {
        ("offices", "region_id"): "OFF-002",
        ("employees", "home_office_id"): "EMP-002",
        ("job_sites", "project_id"): "JBS-002",
        ("crews", "home_office_id"): "CRW-002",
        ("equipment", "equipment_type_id"): "EQP-002",
    }
    for relationship, index in foreign_key_failures(dataset, implemented_entities):
        message = f"{relationship.source_entity}.{relationship.source_field} does not resolve to {relationship.target_entity}.{relationship.target_field}"
        findings.append(Finding(relationship.source_entity, index, "XEN-001", message))
        specific = specific_fk_rules.get((relationship.source_entity, relationship.source_field))
        if specific:
            findings.append(Finding(relationship.source_entity, index, specific, message))
    if "crews" in implemented_entities:
        for kind, index in crew_relationship_failures(dataset):
            if kind == "missing":
                findings.append(Finding("crews", index, "CRW-006", "crew_lead_employee_id is null or empty"))
            elif kind == "inactive":
                findings.append(Finding("crews", index, "CRW-004", "crew lead does not resolve to an Active employee"))
            else:
                findings.append(Finding("crews", index, "CRW-005", "crew lead home office differs from crew home office"))
                findings.append(Finding("crews", index, "XEN-008", "crew lead home office differs from crew home office"))
        for index in terminated_lead_employee_indices(dataset):
            findings.append(Finding("employees", index, "EMP-004", "Terminated employee is referenced as a crew lead"))
    if "field_schedules" in implemented_entities:
        findings.extend(_field_schedule_relationship_findings(dataset))
    if "equipment_assignments" in implemented_entities:
        findings.extend(_equipment_assignment_relationship_findings(dataset))
    if "safety_thresholds" in implemented_entities:
        findings.extend(_safety_threshold_relationship_findings(dataset))
    return tuple(findings)


def _project_site_mismatches(dataset: Mapping[str, Sequence[Mapping[str, Any]]], entity: str) -> tuple[int, ...]:
    sites = {row.get("job_site_id"): row for row in dataset.get("job_sites", ())}
    return tuple(
        index for index, row in enumerate(dataset.get(entity, ()))
        if row.get("job_site_id") in sites and row.get("project_id") != sites[row.get("job_site_id")].get("project_id")
    )


def _field_schedule_relationship_findings(dataset: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Finding]:
    entity = "field_schedules"
    rows = dataset.get(entity, ())
    findings: list[Finding] = []
    for index in _project_site_mismatches(dataset, entity):
        message = "Field Schedule project_id differs from the resolved Job Site project_id"
        findings.extend((Finding(entity, index, "FSD-005", message), Finding(entity, index, "XEN-002", message)))
    id_to_indices: dict[Any, list[int]] = {}
    for index, row in enumerate(rows):
        id_to_indices.setdefault(row.get("field_schedule_id"), []).append(index)
    successors: dict[Any, list[int]] = {}
    for index, row in enumerate(rows):
        predecessor = row.get("rescheduled_from_schedule_id")
        if not is_missing(predecessor):
            successors.setdefault(predecessor, []).append(index)
            if predecessor not in id_to_indices:
                findings.append(Finding(entity, index, "XEN-004", "reschedule predecessor does not resolve"))
    for predecessor_id, successor_indices in successors.items():
        for predecessor_index in id_to_indices.get(predecessor_id, ()):
            if rows[predecessor_index].get("status") == "Completed":
                affected = {predecessor_index, *successor_indices}
                for index in sorted(affected):
                    findings.append(Finding(entity, index, "FSD-006", "Completed schedule is referenced as a reschedule predecessor"))
    for index, row in enumerate(rows):
        schedule_id = row.get("field_schedule_id")
        if row.get("status") == "Rescheduled" and not successors.get(schedule_id):
            findings.append(Finding(entity, index, "FSD-007", "Rescheduled schedule has no resolving successor"))
        if row.get("rescheduled_from_schedule_id") == schedule_id and not is_missing(schedule_id):
            findings.append(Finding(entity, index, "FSD-009", "reschedule lineage self-references"))
            findings.append(Finding(entity, index, "XEN-004", "reschedule lineage self-references"))
    cycle_ids: set[Any] = set()
    predecessor_by_id = {
        row.get("field_schedule_id"): row.get("rescheduled_from_schedule_id")
        for row in rows if not is_missing(row.get("field_schedule_id"))
    }
    for schedule_id in predecessor_by_id:
        path: list[Any] = []
        positions: dict[Any, int] = {}
        current = schedule_id
        while current in predecessor_by_id and not is_missing(current):
            if current in positions:
                cycle_ids.update(path[positions[current]:])
                break
            positions[current] = len(path)
            path.append(current)
            current = predecessor_by_id[current]
    for schedule_id in sorted(cycle_ids, key=str):
        for index in id_to_indices.get(schedule_id, ()):
            if rows[index].get("rescheduled_from_schedule_id") == schedule_id:
                continue  # Self-reference was already emitted above.
            findings.append(Finding(entity, index, "FSD-009", "reschedule predecessor traversal contains a cycle"))
            findings.append(Finding(entity, index, "XEN-004", "reschedule predecessor traversal contains a cycle"))
    return findings


def _assignment_pairs(rows: Sequence[Mapping[str, Any]]) -> tuple[set[int], set[int]]:
    overlaps: set[int] = set()
    adjacent: set[int] = set()
    for first_index, first in enumerate(rows):
        first_start = parse_iso_timestamp(first.get("assignment_start_timestamp"))
        first_end = None if is_missing(first.get("assignment_end_timestamp")) else parse_iso_timestamp(first.get("assignment_end_timestamp"))
        if first_start is None or (not is_missing(first.get("assignment_end_timestamp")) and first_end is None):
            continue
        try:
            if first_end is not None and first_end <= first_start:
                continue
        except TypeError:
            continue
        for second_index in range(first_index + 1, len(rows)):
            second = rows[second_index]
            if first.get("equipment_id") != second.get("equipment_id"):
                continue
            second_start = parse_iso_timestamp(second.get("assignment_start_timestamp"))
            second_end = None if is_missing(second.get("assignment_end_timestamp")) else parse_iso_timestamp(second.get("assignment_end_timestamp"))
            if second_start is None or (not is_missing(second.get("assignment_end_timestamp")) and second_end is None):
                continue
            try:
                if second_end is not None and second_end <= second_start:
                    continue
            except TypeError:
                continue
            first_limit = first_end or datetime.max.replace(tzinfo=first_start.tzinfo)
            second_limit = second_end or datetime.max.replace(tzinfo=second_start.tzinfo)
            try:
                if first_start < second_limit and second_start < first_limit:
                    overlaps.update((first_index, second_index))
                elif first_end == second_start or second_end == first_start:
                    adjacent.update((first_index, second_index))
            except TypeError:
                continue
    return overlaps, adjacent


def _equipment_assignment_relationship_findings(dataset: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Finding]:
    entity = "equipment_assignments"
    rows = dataset.get(entity, ())
    findings: list[Finding] = []
    for index in _project_site_mismatches(dataset, entity):
        message = "Equipment Assignment project_id differs from the resolved Job Site project_id"
        findings.extend((Finding(entity, index, "EQA-002", message), Finding(entity, index, "XEN-003", message)))
    overlaps, adjacent = _assignment_pairs(rows)
    for index in sorted(overlaps):
        findings.append(Finding(entity, index, "EQA-003", "equipment assignment overlaps another period for the same equipment"))
        findings.append(Finding(entity, index, "XEN-005", "equipment assignment overlaps another period for the same equipment"))
    for index in sorted(adjacent):
        findings.append(Finding(entity, index, "EQA-004", "equipment assignment has an accepted adjacent boundary"))
    return findings


def _is_active(value: Any) -> bool:
    return value is True or value == "True"


def _threshold_scope(row: Mapping[str, Any]) -> tuple[Any, ...]:
    equipment_type = None if is_missing(row.get("equipment_type_id")) else row.get("equipment_type_id")
    return row.get("activity_id"), row.get("metric_code"), row.get("severity"), equipment_type


def _threshold_payload(row: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("comparison_operator"), row.get("unit"), row.get("threshold_value_or_code_set"),
        row.get("threshold_value"), row.get("weather_code_set"),
        row.get("recommended_action_code"), row.get("override_flag"),
    )


def _threshold_conflicts(rows: Sequence[Mapping[str, Any]]) -> tuple[set[int], set[int]]:
    overlaps: set[int] = set()
    conflicts: set[int] = set()
    for first_index, first in enumerate(rows):
        if not _is_active(first.get("is_active")):
            continue
        first_start = parse_iso_date(first.get("effective_start_date"))
        first_end = None if is_missing(first.get("effective_end_date")) else parse_iso_date(first.get("effective_end_date"))
        if first_start is None or (not is_missing(first.get("effective_end_date")) and first_end is None):
            continue
        for second_index in range(first_index + 1, len(rows)):
            second = rows[second_index]
            if not _is_active(second.get("is_active")) or _threshold_scope(first) != _threshold_scope(second):
                continue
            second_start = parse_iso_date(second.get("effective_start_date"))
            second_end = None if is_missing(second.get("effective_end_date")) else parse_iso_date(second.get("effective_end_date"))
            if second_start is None or (not is_missing(second.get("effective_end_date")) and second_end is None):
                continue
            if first_start <= (second_end or date.max) and second_start <= (first_end or date.max):
                overlaps.update((first_index, second_index))
                if _threshold_payload(first) != _threshold_payload(second):
                    conflicts.update((first_index, second_index))
    return overlaps, conflicts


def _safety_threshold_relationship_findings(dataset: Mapping[str, Sequence[Mapping[str, Any]]]) -> list[Finding]:
    entity = "safety_thresholds"
    overlaps, conflicts = _threshold_conflicts(dataset.get(entity, ()))
    findings: list[Finding] = []
    for index in sorted(overlaps):
        findings.append(Finding(entity, index, "SFT-002", "active safety threshold period overlaps another rule in the same scope"))
        findings.append(Finding(entity, index, "XEN-006", "active safety threshold period overlaps another rule in the same scope"))
    for index in sorted(conflicts):
        findings.append(Finding(entity, index, "SFT-008", "simultaneously active same-scope safety rules have conflicting payloads"))
    return findings
