"""Configuration for the 12 approved operational source entities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntityConfig:
    """Describe one source CSV accepted by operational Bronze ingestion."""

    name: str
    folder: str
    required_columns: tuple[str, ...]


_CONFIGS = (
    EntityConfig("regions", "regions", ("region_id", "region_code", "region_name")),
    EntityConfig("offices", "offices", ("office_id", "office_code", "office_name", "region_id")),
    EntityConfig("employees", "employees", ("employee_id", "employee_number", "employee_name", "home_office_id", "employment_status")),
    EntityConfig("projects", "projects", ("project_id", "project_code", "project_name", "office_id", "project_manager_employee_id", "field_manager_employee_id", "status")),
    EntityConfig("job_sites", "job_sites", ("job_site_id", "job_site_code", "job_site_name", "project_id", "weather_location_code")),
    EntityConfig("crews", "crews", ("crew_id", "crew_code", "home_office_id", "crew_status")),
    EntityConfig("activities", "activities", ("activity_id", "activity_code", "activity_name")),
    EntityConfig("field_schedules", "field_schedules", ("field_schedule_id", "project_id", "job_site_id", "crew_id", "activity_id", "scheduled_start_timestamp", "scheduled_end_timestamp", "scheduled_date", "planned_crew_hours", "planned_crew_size", "planned_labor_hours", "status", "rescheduled_from_schedule_id")),
    EntityConfig("equipment_types", "equipment_types", ("equipment_type_id", "equipment_type_code", "equipment_type_name")),
    EntityConfig("equipment", "equipment", ("equipment_id", "equipment_code", "equipment_type_id", "equipment_status")),
    EntityConfig("equipment_assignments", "equipment_assignments", ("assignment_id", "equipment_id", "job_site_id", "project_id", "assignment_start_timestamp")),
    EntityConfig("safety_thresholds", "safety_thresholds", ("threshold_id", "activity_id", "metric_code", "comparison_operator", "unit", "threshold_value_or_code_set", "severity", "recommended_action_code", "effective_start_date", "is_active", "override_flag")),
)

ENTITY_CONFIGS = {config.name: config for config in _CONFIGS}


def get_entity_config(entity_name: str) -> EntityConfig:
    """Return an entity configuration or raise a clear error."""
    if not isinstance(entity_name, str) or not entity_name.strip():
        raise ValueError("entity_name must be a non-empty string")
    normalized = entity_name.strip().lower()
    try:
        return ENTITY_CONFIGS[normalized]
    except KeyError as exc:
        approved = ", ".join(ENTITY_CONFIGS)
        raise ValueError(f"Unknown entity {entity_name!r}; approved entities: {approved}") from exc
