"""Single source of metadata for implemented operational Silver rules."""

from __future__ import annotations

from .models import RuleMetadata


def _rule(rule_id: str, entity: str, severity: str, action: str, code: str) -> RuleMetadata:
    return RuleMetadata(rule_id, entity, severity, action, code)


_Q = "Quarantine and log."
_W = "Retain, attach warning, log; no source change."

_RULES = (
    _rule("REG-001", "regions", "Critical", _Q, "ERR_REGION_CODE_REQUIRED"),
    _rule("REG-002", "regions", "Critical", "Quarantine duplicate-key records and log.", "ERR_REGION_CODE_DUPLICATE"),
    _rule("REG-003", "regions", "Warning", _W, "WARN_REGION_NAME_MISSING"),
    _rule("OFF-001", "offices", "Critical", _Q, "ERR_OFFICE_CODE_REQUIRED"),
    _rule("OFF-002", "offices", "Critical", _Q, "ERR_OFFICE_REGION_FK_INVALID"),
    _rule("OFF-003", "offices", "Critical", "Quarantine duplicate-key records and log.", "ERR_OFFICE_CODE_DUPLICATE"),
    _rule("OFF-004", "offices", "Warning", _W, "WARN_OFFICE_NAME_MISSING"),
    _rule("EMP-001", "employees", "Critical", _Q, "ERR_EMPLOYEE_NUMBER_REQUIRED"),
    _rule("EMP-002", "employees", "Critical", _Q, "ERR_EMPLOYEE_HOME_OFFICE_FK_INVALID"),
    _rule("EMP-003", "employees", "Critical", "Quarantine duplicate-key records and log.", "ERR_EMPLOYEE_NUMBER_DUPLICATE"),
    _rule("EMP-004", "employees", "Warning", "Retain affected source record(s), attach warning, and log.", "WARN_TERMINATED_EMPLOYEE_CREW_LEAD"),
    _rule("PRJ-001", "projects", "Critical", _Q, "ERR_PROJECT_CODE_REQUIRED"),
    _rule("PRJ-002", "projects", "Critical", "Quarantine duplicate-key records and log.", "ERR_PROJECT_CODE_DUPLICATE"),
    _rule("PRJ-003", "projects", "Warning", _W, "WARN_PROJECT_NAME_MISSING"),
    _rule("JBS-001", "job_sites", "Critical", _Q, "ERR_JOB_SITE_CODE_REQUIRED"),
    _rule("JBS-002", "job_sites", "Critical", _Q, "ERR_JOB_SITE_PROJECT_FK_INVALID"),
    _rule("JBS-003", "job_sites", "Critical", "Quarantine duplicate-key records and log.", "ERR_JOB_SITE_CODE_DUPLICATE"),
    _rule("JBS-004", "job_sites", "Critical", _Q, "ERR_JOB_SITE_WEATHER_LOCATION_INVALID"),
    _rule("CRW-001", "crews", "Critical", _Q, "ERR_CREW_CODE_REQUIRED"),
    _rule("CRW-002", "crews", "Critical", _Q, "ERR_CREW_HOME_OFFICE_FK_INVALID"),
    _rule("CRW-003", "crews", "Critical", "Quarantine duplicate-key records and log.", "ERR_CREW_CODE_DUPLICATE"),
    _rule("CRW-004", "crews", "Critical", _Q, "ERR_CREW_LEAD_NOT_ACTIVE"),
    _rule("CRW-005", "crews", "Warning", _W, "WARN_CREW_LEAD_OFFICE_MISMATCH"),
    _rule("CRW-006", "crews", "Warning", "Retain, attach warning, and log.", "WARN_CREW_LEAD_MISSING"),
    _rule("ACT-001", "activities", "Critical", _Q, "ERR_ACTIVITY_CODE_REQUIRED"),
    _rule("ACT-002", "activities", "Critical", "Quarantine duplicate-key records and log.", "ERR_ACTIVITY_CODE_DUPLICATE"),
    _rule("ACT-003", "activities", "Warning", _W, "WARN_ACTIVITY_NAME_MISSING"),
    _rule("EQT-001", "equipment_types", "Critical", _Q, "ERR_EQUIPMENT_TYPE_CODE_REQUIRED"),
    _rule("EQT-002", "equipment_types", "Critical", "Quarantine duplicate-key records and log.", "ERR_EQUIPMENT_TYPE_CODE_DUPLICATE"),
    _rule("EQT-003", "equipment_types", "Warning", _W, "WARN_EQUIPMENT_TYPE_NAME_MISSING"),
    _rule("EQP-001", "equipment", "Critical", _Q, "ERR_EQUIPMENT_CODE_REQUIRED"),
    _rule("EQP-002", "equipment", "Critical", _Q, "ERR_EQUIPMENT_TYPE_FK_INVALID"),
    _rule("EQP-003", "equipment", "Critical", "Quarantine duplicate-key records and log.", "ERR_EQUIPMENT_CODE_DUPLICATE"),
    _rule("EQP-004", "equipment", "Warning", _W, "WARN_EQUIPMENT_STATUS_MISSING_OR_DOMAIN_UNRESOLVED"),
    _rule("FSD-001", "field_schedules", "Critical", "Design unresolved for parsing policy; once approved, quarantine failures and log.", "ERR_FIELD_SCHEDULE_WINDOW_INVALID"),
    _rule("FSD-002", "field_schedules", "Critical", _Q, "ERR_FIELD_SCHEDULE_DATE_MISMATCH"),
    _rule("FSD-003", "field_schedules", "Warning", "Retain, attach warning, log; design decision required for exceptions.", "WARN_FIELD_SCHEDULE_CREW_HOURS_MISMATCH"),
    _rule("FSD-004", "field_schedules", "Critical", _Q, "ERR_FIELD_SCHEDULE_LABOR_HOURS_INVALID"),
    _rule("FSD-005", "field_schedules", "Critical", _Q, "ERR_FIELD_SCHEDULE_PROJECT_SITE_MISMATCH"),
    _rule("FSD-006", "field_schedules", "Critical", "Quarantine affected lineage record(s) and log.", "ERR_COMPLETED_SCHEDULE_RESCHEDULED"),
    _rule("FSD-007", "field_schedules", "Critical", "Quarantine affected lineage record(s) and log.", "ERR_RESCHEDULE_SUCCESSOR_MISSING"),
    _rule("FSD-009", "field_schedules", "Critical", "Quarantine affected lineage record(s) and log.", "ERR_RESCHEDULE_LINEAGE_CYCLE"),
    _rule("FSD-010", "field_schedules", "Critical", _Q, "ERR_FIELD_SCHEDULE_STATUS_INVALID"),
    _rule("EQA-001", "equipment_assignments", "Critical", "Design unresolved for parsing policy; quarantine deterministic failures and log.", "ERR_EQUIPMENT_ASSIGNMENT_WINDOW_INVALID"),
    _rule("EQA-002", "equipment_assignments", "Critical", _Q, "ERR_EQUIPMENT_ASSIGNMENT_PROJECT_SITE_MISMATCH"),
    _rule("EQA-003", "equipment_assignments", "Critical", "Quarantine affected assignments and log.", "ERR_EQUIPMENT_ASSIGNMENT_OVERLAP"),
    _rule("EQA-004", "equipment_assignments", "Info", "Retain unchanged and log accepted adjacency.", "INFO_EQUIPMENT_ASSIGNMENT_ADJACENT_BOUNDARY"),
    _rule("SFT-001", "safety_thresholds", "Critical", "Design unresolved for parsing policy; quarantine deterministic failures and log.", "ERR_SAFETY_THRESHOLD_EFFECTIVE_DATES_INVALID"),
    _rule("SFT-002", "safety_thresholds", "Critical", "Quarantine conflicting rules and log.", "ERR_SAFETY_THRESHOLD_ACTIVE_PERIOD_OVERLAP"),
    _rule("SFT-003", "safety_thresholds", "Critical", "Design unresolved beyond verified metrics; quarantine known incompatibilities and log.", "ERR_SAFETY_THRESHOLD_OPERATOR_INCOMPATIBLE"),
    _rule("SFT-004", "safety_thresholds", "Critical", _Q, "ERR_SAFETY_THRESHOLD_WEATHER_STRUCTURE_INVALID"),
    _rule("SFT-005", "safety_thresholds", "Critical", "Design unresolved for unit/bounds; quarantine structural failures and log.", "ERR_SAFETY_THRESHOLD_NUMERIC_STRUCTURE_INVALID"),
    _rule("SFT-006", "safety_thresholds", "Critical", _Q, "ERR_SAFETY_THRESHOLD_ACTION_REQUIRED"),
    _rule("SFT-007", "safety_thresholds", "Critical", _Q, "ERR_SAFETY_THRESHOLD_CRITICAL_OVERRIDE_REQUIRED"),
    _rule("SFT-008", "safety_thresholds", "Critical", "Quarantine conflicting rules and log.", "ERR_SAFETY_THRESHOLD_ACTIVE_RULE_CONFLICT"),
    _rule("XEN-001", "cross_entity", "Critical", "Quarantine record with invalid FK and log relationship detail.", "ERR_CROSS_ENTITY_FK_INVALID"),
    _rule("XEN-002", "cross_entity", "Critical", _Q, "ERR_CROSS_FIELD_SCHEDULE_PROJECT_SITE_MISMATCH"),
    _rule("XEN-003", "cross_entity", "Critical", _Q, "ERR_CROSS_EQUIPMENT_ASSIGNMENT_PROJECT_SITE_MISMATCH"),
    _rule("XEN-004", "cross_entity", "Critical", "Quarantine affected lineage record(s) and log.", "ERR_CROSS_RESCHEDULE_LINEAGE_INVALID"),
    _rule("XEN-005", "cross_entity", "Critical", "Quarantine affected assignments and log.", "ERR_CROSS_EQUIPMENT_ASSIGNMENT_OVERLAP"),
    _rule("XEN-006", "cross_entity", "Critical", "Quarantine conflicting thresholds and log.", "ERR_CROSS_SAFETY_THRESHOLD_PERIOD_OVERLAP"),
    _rule("XEN-007", "cross_entity", "Critical", _Q, "ERR_CROSS_WEATHER_LOCATION_INVALID"),
    _rule("XEN-008", "cross_entity", "Warning", _W, "WARN_CROSS_CREW_LEAD_OFFICE_MISMATCH"),
    _rule("XEN-009", "cross_entity", "Critical", "Quarantine duplicate records and log entity/key.", "ERR_CROSS_ENTITY_BUSINESS_KEY_DUPLICATE"),
    _rule("XEN-010", "cross_entity", "Critical", "Quarantine and log; do not impute.", "ERR_CROSS_ENTITY_REQUIRED_VALUE_MISSING"),
)

RULE_REGISTRY = {rule.rule_id: rule for rule in _RULES}

if len(RULE_REGISTRY) != len(_RULES):
    raise RuntimeError("Silver rule registry contains duplicate rule IDs")
if len({rule.error_code for rule in _RULES}) != len(_RULES):
    raise RuntimeError("Silver rule registry contains duplicate error codes")


def get_rule(rule_id: str) -> RuleMetadata:
    try:
        return RULE_REGISTRY[rule_id]
    except KeyError as exc:
        raise ValueError(f"Rule {rule_id!r} is not implemented") from exc
