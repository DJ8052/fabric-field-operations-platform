"""Relationship registry and master-entity relationship checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .common_validations import invalid_foreign_key_indices, is_missing
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
    return tuple(findings)
