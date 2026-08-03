# Operational Data Contracts

## Purpose and authority

This document defines the Version 1 business contracts for the 12 operational source entities. It governs source grain and Silver validation; it is not the Gold dimensional model. Field names and required fields below are reconciled to the generated CSV schema and the operational Bronze ingestion configuration as of Phase 10, Step 3. The evidence and differences from the prior contract are recorded in `silver-contract-schema-reconciliation.md`.

## Contract principles

- Business keys are immutable and may not be reassigned or silently overwritten.
- A required field is a column required by Bronze ingestion. Value-level null/empty behavior is governed by the explicit rules below; fields with a specific Warn and Flag missing-value rule remain warning-only.
- A nullable/optional field is validated conditionally when populated.
- Foreign keys must resolve as listed in the relationship register below.
- Bronze values remain available for lineage. Silver may normalize only where an Info rule explicitly permits a meaning-preserving operation.
- The source grain is unchanged. No Version 2 fields or entities are introduced.
- Every rule retains its original enforcement classification: **Hard Reject**, **Warn and Flag**, or **Informational**.

## Entity contracts

### Region

- Grain: one row per region.
- Business key: `region_code`; candidate primary key: `region_id`.
- Required fields: `region_id`, `region_code`, `region_name`.
- Nullable/optional fields: `region_description`.
- Foreign keys: none.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| REG-001 | `region_code` is not null and, after no normalization, is not the empty string. | Hard Reject |
| REG-002 | No two Region rows have the same `region_code`. | Hard Reject |
| REG-003 | `region_name` is not null and is not the empty string. Whitespace-only handling is an unresolved normalization decision. | Warn and Flag |

### Office

- Grain: one row per office.
- Business key: `office_code`; candidate primary key: `office_id`.
- Required fields: `office_id`, `office_code`, `office_name`, `region_id`.
- Nullable/optional fields: `office_description`.
- Foreign keys: `region_id` -> Region.`region_id`.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| OFF-001 | `office_code` is not null and is not the empty string. | Hard Reject |
| OFF-002 | `region_id` resolves to Region.`region_id`. | Hard Reject |
| OFF-003 | No two Office rows have the same `office_code`. | Hard Reject |
| OFF-004 | `office_name` is not null and is not the empty string. Whitespace-only handling is unresolved. | Warn and Flag |

### Employee

- Grain: one row per employee.
- Business key: `employee_number`; candidate primary key: `employee_id`.
- Required fields: `employee_id`, `employee_number`, `employee_name`, `home_office_id`, `employment_status`.
- Nullable/optional fields: `termination_date`, `employee_role_code`.
- Foreign keys: `home_office_id` -> Office.`office_id`.
- Generated status domain: `Active`. The broader business domain remains unresolved; no additional values are invented here.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| EMP-001 | `employee_number` is not null and is not the empty string. | Hard Reject |
| EMP-002 | `home_office_id` resolves to Office.`office_id`. | Hard Reject |
| EMP-003 | No two Employee rows have the same `employee_number`. | Hard Reject |
| EMP-004 | An Employee whose `employment_status` is `Terminated` is not referenced by Crew.`crew_lead_employee_id`; the full approved status domain and case policy are unresolved. | Warn and Flag |

### Project

- Grain: one row per project.
- Business key: `project_code`; candidate primary key: `project_id`.
- Required fields: `project_id`, `project_code`, `project_name`, `office_id`, `project_manager_employee_id`, `field_manager_employee_id`, `status`.
- Nullable/optional fields: `project_start_date`, `project_end_date`, `priority_code`, `project_description`, `parent_project_code`.
- Foreign keys: `office_id` -> Office.`office_id`; `project_manager_employee_id` -> Employee.`employee_id`; `field_manager_employee_id` -> Employee.`employee_id`.
- Controlled `status` values verified in generator validation: `Planned`, `Active`, `Closed`, `Cancelled`.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| PRJ-001 | `project_code` is not null and is not the empty string. | Hard Reject |
| PRJ-002 | No two Project rows have the same `project_code`. | Hard Reject |
| PRJ-003 | `project_name` is not null and is not the empty string. Whitespace-only handling is unresolved. | Warn and Flag |

### Job Site

- Grain: one row per job site.
- Business key: `job_site_code`; candidate primary key: `job_site_id`.
- Required fields: `job_site_id`, `job_site_code`, `job_site_name`, `project_id`, `weather_location_code`.
- Nullable/optional fields: `job_site_description`.
- Foreign keys: `project_id` -> Project.`project_id`.
- Controlled `weather_location_code` values: `TX-DAL`, `TX-HOU`, `TX-AUS`.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| JBS-001 | `job_site_code` is not null and is not the empty string. | Hard Reject |
| JBS-002 | `project_id` resolves to Project.`project_id`. | Hard Reject |
| JBS-003 | No two Job Site rows have the same `job_site_code`. | Hard Reject |
| JBS-004 | `weather_location_code` is exactly one of `TX-DAL`, `TX-HOU`, or `TX-AUS`. | Hard Reject |

### Crew

- Grain: one row per crew.
- Business key: `crew_code`; candidate primary key: `crew_id`.
- Required fields: `crew_id`, `crew_code`, `home_office_id`, `crew_status`.
- Nullable/optional fields: `crew_lead_employee_id`, `crew_description`.
- Foreign keys: `home_office_id` -> Office.`office_id`; when populated, `crew_lead_employee_id` -> Employee.`employee_id`.
- Generated status domain: `Active`. The broader business domain remains unresolved.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| CRW-001 | `crew_code` is not null and is not the empty string. | Hard Reject |
| CRW-002 | `home_office_id` resolves to Office.`office_id`. | Hard Reject |
| CRW-003 | No two Crew rows have the same `crew_code`. | Hard Reject |
| CRW-004 | When `crew_lead_employee_id` is populated, it resolves to an Employee whose `employment_status` is exactly `Active`; status case policy is unresolved. | Hard Reject |
| CRW-005 | When `crew_lead_employee_id` is populated, the referenced Employee.`home_office_id` equals Crew.`home_office_id`. | Warn and Flag |
| CRW-006 | `crew_lead_employee_id` is null or empty. This is permitted but produces a warning. | Warn and Flag |

### Activity

- Grain: one row per activity.
- Business key: `activity_code`; candidate primary key: `activity_id`.
- Required fields: `activity_id`, `activity_code`, `activity_name`.
- Nullable/optional fields: `activity_description`, `activity_category`.
- Foreign keys: none.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| ACT-001 | `activity_code` is not null and is not the empty string. | Hard Reject |
| ACT-002 | No two Activity rows have the same `activity_code`. | Hard Reject |
| ACT-003 | `activity_name` is not null and is not the empty string. Whitespace-only handling is unresolved. | Warn and Flag |

### Field Schedule

- Grain: one row per schedule occurrence.
- Business key and candidate primary key: `field_schedule_id`.
- Required fields: `field_schedule_id`, `project_id`, `job_site_id`, `crew_id`, `activity_id`, `scheduled_start_timestamp`, `scheduled_end_timestamp`, `scheduled_date`, `planned_crew_hours`, `planned_crew_size`, `planned_labor_hours`, `status`, `rescheduled_from_schedule_id` (column required; value may be empty for a lineage root).
- Nullable/optional generated fields: `scenario_id` (generated scenario/test metadata; not required by Bronze ingestion).
- Foreign keys: `project_id` -> Project.`project_id`; `job_site_id` -> Job Site.`job_site_id`; `crew_id` -> Crew.`crew_id`; `activity_id` -> Activity.`activity_id`; when populated, `rescheduled_from_schedule_id` -> Field Schedule.`field_schedule_id`.
- Controlled `status` values: `Scheduled`, `In Progress`, `Completed`, `Delayed`, `Cancelled`, `Rescheduled`.
- Schema conflict: the prior contract named nonexistent `approved_adjustment_flag`, `approved_exception_note`, and `cancellation_reason_code`. They are not added or invented. The exception mechanism referenced by FSD-003 therefore remains an architecture decision.
- Labor-hours decision: generator code and tests calculate `planned_labor_hours = planned_crew_hours * planned_crew_size`; no `crew_size` column exists in Crew. Therefore Field Schedule.`planned_crew_size` is authoritative. A nominal Crew comparison cannot be implemented until a future architecture decision adds or identifies such a source field; no mismatch error is defined in Version 1.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| FSD-001 | Parsed `scheduled_end_timestamp` is strictly greater than parsed `scheduled_start_timestamp`. Timestamp parsing/time-zone policy is unresolved. | Hard Reject |
| FSD-002 | `scheduled_date` equals the calendar-date portion of `scheduled_start_timestamp`. | Hard Reject |
| FSD-003 | `planned_crew_hours` equals (`scheduled_end_timestamp` - `scheduled_start_timestamp`) in hours. The prior approved-adjustment exception cannot be evaluated because no adjustment/exception column exists; adding an exception mechanism is unresolved. | Warn and Flag |
| FSD-004 | `planned_labor_hours` equals `planned_crew_hours * planned_crew_size`; Field Schedule.`planned_crew_size` is authoritative. | Hard Reject |
| FSD-005 | Field Schedule.`project_id` equals the `project_id` on the Job Site resolved by `job_site_id`. | Hard Reject |
| FSD-006 | A row whose `status` is `Completed` is not referenced by another row's `rescheduled_from_schedule_id`. | Hard Reject |
| FSD-007 | Every row whose `status` is `Rescheduled` is referenced by at least one successor row's `rescheduled_from_schedule_id`, and that successor FK resolves. | Hard Reject |
| FSD-008 | Original schedule timestamps are unchanged after rescheduling. This requires a prior immutable snapshot or change-event source, neither of which exists in a single Bronze CSV; enforcement is deferred from Silver Version 1 pending an approved historical comparison source. | Hard Reject |
| FSD-009 | `rescheduled_from_schedule_id` does not equal the row's `field_schedule_id`, and repeatedly following populated predecessors never revisits a `field_schedule_id`. | Hard Reject |
| FSD-010 | `status` is exactly one of `Scheduled`, `In Progress`, `Completed`, `Delayed`, `Cancelled`, or `Rescheduled`. | Hard Reject |

### Equipment Type

- Grain: one row per equipment type.
- Business key: `equipment_type_code`; candidate primary key: `equipment_type_id`.
- Required fields: `equipment_type_id`, `equipment_type_code`, `equipment_type_name`.
- Nullable/optional fields: `equipment_type_description`, `equipment_category`.
- Foreign keys: none.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| EQT-001 | `equipment_type_code` is not null and is not the empty string. | Hard Reject |
| EQT-002 | No two Equipment Type rows have the same `equipment_type_code`. | Hard Reject |
| EQT-003 | `equipment_type_name` is not null and is not the empty string. Whitespace-only handling is unresolved. | Warn and Flag |

### Equipment

- Grain: one row per equipment asset.
- Business key: `equipment_code`; candidate primary key: `equipment_id`.
- Required fields: `equipment_id`, `equipment_code`, `equipment_type_id`, `equipment_status`.
- Nullable/optional fields: `serial_number`, `asset_tag`, `equipment_description`.
- Foreign keys: `equipment_type_id` -> Equipment Type.`equipment_type_id`.
- Generated status values are `Available` and `In Use`; the prior example also named `Out of Service` and `Retired`, but an approved complete domain is unresolved.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| EQP-001 | `equipment_code` is not null and is not the empty string. | Hard Reject |
| EQP-002 | `equipment_type_id` resolves to Equipment Type.`equipment_type_id`. | Hard Reject |
| EQP-003 | No two Equipment rows have the same `equipment_code`. | Hard Reject |
| EQP-004 | `equipment_status` is not null and is not the empty string; domain membership cannot be evaluated until the complete approved domain is decided. | Warn and Flag |

### Equipment Assignment

- Grain: one row per equipment assignment period.
- Business key and candidate primary key: `assignment_id`.
- Required fields: `assignment_id`, `equipment_id`, `job_site_id`, `project_id`, `assignment_start_timestamp`.
- Nullable/optional fields: `assignment_end_timestamp`, `assignment_note`, `scenario_id`.
- Foreign keys: `equipment_id` -> Equipment.`equipment_id`; `job_site_id` -> Job Site.`job_site_id`; `project_id` -> Project.`project_id`.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| EQA-001 | When `assignment_end_timestamp` is populated, its parsed timestamp is strictly greater than parsed `assignment_start_timestamp`; parsing/time-zone policy is unresolved. | Hard Reject |
| EQA-002 | Equipment Assignment.`project_id` equals the `project_id` on the Job Site resolved by `job_site_id`. | Hard Reject |
| EQA-003 | For rows with the same `equipment_id`, periods overlap when `first_start < second_end` and `second_start < first_end`; open-ended null ends extend indefinitely. No overlapping pair is allowed. | Hard Reject |
| EQA-004 | For rows with the same `equipment_id`, an end timestamp exactly equal to another start timestamp is an accepted adjacent boundary and is logged. | Informational |

### Safety Threshold

- Grain: one row per active or historical safety-threshold rule.
- Business key and candidate primary key: `threshold_id`.
- Required fields: `threshold_id`, `activity_id`, `metric_code`, `comparison_operator`, `unit`, `threshold_value_or_code_set`, `severity`, `recommended_action_code`, `effective_start_date`, `is_active`, `override_flag`.
- Nullable/optional fields: `equipment_type_id`, `effective_end_date`, `threshold_value`, `weather_code_set`.
- Foreign keys: `activity_id` -> Activity.`activity_id`; when populated, `equipment_type_id` -> Equipment Type.`equipment_type_id`.
- Verified generated structures: `WEATHER_CODE` uses operator `IN`, unit `wmo_code`, populated `weather_code_set`, and empty `threshold_value`; generated numeric metrics use `>=`, a populated `threshold_value`, and empty `weather_code_set`. No complete metric/operator/unit registry exists.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| SFT-001 | `effective_end_date` is null/empty or is on or after `effective_start_date`. Date parsing policy is unresolved. | Hard Reject |
| SFT-002 | Active periods do not overlap for equal (`activity_id`, `metric_code`, `severity`, `equipment_type_id`), treating null/empty `equipment_type_id` as the same scope and null/empty `effective_end_date` as open-ended. | Hard Reject |
| SFT-003 | For the verified `WEATHER_CODE` structure, `comparison_operator` equals `IN`; for other generated metrics it equals `>=`. A complete approved metric/operator registry is unresolved. | Hard Reject |
| SFT-004 | When `metric_code` is `WEATHER_CODE`, `weather_code_set` is populated and `threshold_value` is null/empty. | Hard Reject |
| SFT-005 | When `metric_code` is not `WEATHER_CODE`, `threshold_value` is populated and parseable as numeric and `weather_code_set` is null/empty. Unit compatibility and numeric bounds require an unresolved metric/unit registry. | Hard Reject |
| SFT-006 | `recommended_action_code` is not null and is not the empty string. | Hard Reject |
| SFT-007 | When `severity` is exactly `CRITICAL`, `override_flag` is boolean `true`. | Hard Reject |
| SFT-008 | Two simultaneously active rules with equal (`activity_id`, `metric_code`, `severity`, `equipment_type_id`) and different operator, unit, threshold payload, action, or override values are conflicting and are rejected. | Hard Reject |

## Cross-entity validation rules

These retain the prior contract's separate cross-entity rules even when an entity rule covers the same condition. They are separate validation-result obligations and therefore receive distinct IDs.

| Rule ID | Deterministic validation rule | Enforcement |
| --- | --- | --- |
| XEN-001 | Each of the 19 relationships in the foreign-key register resolves; nullable relationships are checked only when populated. | Hard Reject |
| XEN-002 | Field Schedule.`project_id` equals the `project_id` of the Job Site resolved by Field Schedule.`job_site_id`. | Hard Reject |
| XEN-003 | Equipment Assignment.`project_id` equals the `project_id` of the Job Site resolved by Equipment Assignment.`job_site_id`. | Hard Reject |
| XEN-004 | Every populated Field Schedule.`rescheduled_from_schedule_id` resolves, is not a self-reference, and predecessor traversal does not revisit an ID. | Hard Reject |
| XEN-005 | No two Equipment Assignment periods for the same `equipment_id` overlap under the interval definition in EQA-003. | Hard Reject |
| XEN-006 | Safety Threshold active periods do not overlap for equal (`activity_id`, `metric_code`, `severity`, `equipment_type_id`) under SFT-002. | Hard Reject |
| XEN-007 | Job Site.`weather_location_code` is exactly one of `TX-DAL`, `TX-HOU`, or `TX-AUS`. | Hard Reject |
| XEN-008 | When Crew.`crew_lead_employee_id` is populated and resolves, differing Crew.`home_office_id` and Employee.`home_office_id` produces a warning. | Warn and Flag |
| XEN-009 | Within each entity, duplicate values are rejected for these business keys: Region.`region_code`, Office.`office_code`, Employee.`employee_number`, Project.`project_code`, Job Site.`job_site_code`, Crew.`crew_code`, Activity.`activity_code`, Equipment Type.`equipment_type_code`, and Equipment.`equipment_code`; source identifiers are unique for Field Schedule, Equipment Assignment, and Safety Threshold. | Hard Reject |
| XEN-010 | A record is rejected when null or empty in this Critical value set: every entity's primary/source identifier; all required FK columns; Region.`region_code`; Office.`office_code`; Employee.`employee_number`, `employee_name`, `employment_status`; Project.`project_code`, `status`; Job Site.`job_site_code`, `job_site_name`, `weather_location_code`; Crew.`crew_code`, `crew_status`; Activity.`activity_code`; Field Schedule timestamps/date/hour/size/status fields; Equipment Type.`equipment_type_code`; Equipment.`equipment_code`; Equipment Assignment.`assignment_start_timestamp`; and all Safety Threshold required fields. Fields governed by explicit missing-value Warning rules are excluded. Silver does not fill missing values. | Hard Reject |

## Foreign-key relationship register (verified count: 19)

| # | Source relationship | Requirement |
| ---: | --- | --- |
| 1 | Office.`region_id` -> Region.`region_id` | Required |
| 2 | Employee.`home_office_id` -> Office.`office_id` | Required |
| 3 | Project.`office_id` -> Office.`office_id` | Required |
| 4 | Project.`project_manager_employee_id` -> Employee.`employee_id` | Required |
| 5 | Project.`field_manager_employee_id` -> Employee.`employee_id` | Required |
| 6 | Job Site.`project_id` -> Project.`project_id` | Required |
| 7 | Crew.`home_office_id` -> Office.`office_id` | Required |
| 8 | Crew.`crew_lead_employee_id` -> Employee.`employee_id` | Conditional when populated |
| 9 | Field Schedule.`project_id` -> Project.`project_id` | Required |
| 10 | Field Schedule.`job_site_id` -> Job Site.`job_site_id` | Required |
| 11 | Field Schedule.`crew_id` -> Crew.`crew_id` | Required |
| 12 | Field Schedule.`activity_id` -> Activity.`activity_id` | Required |
| 13 | Field Schedule.`rescheduled_from_schedule_id` -> Field Schedule.`field_schedule_id` | Conditional when populated; self-reference |
| 14 | Equipment.`equipment_type_id` -> Equipment Type.`equipment_type_id` | Required |
| 15 | Equipment Assignment.`equipment_id` -> Equipment.`equipment_id` | Required |
| 16 | Equipment Assignment.`job_site_id` -> Job Site.`job_site_id` | Required |
| 17 | Equipment Assignment.`project_id` -> Project.`project_id` | Required |
| 18 | Safety Threshold.`activity_id` -> Activity.`activity_id` | Required |
| 19 | Safety Threshold.`equipment_type_id` -> Equipment Type.`equipment_type_id` | Conditional when populated |

The following are cross-entity consistency checks, not additional foreign keys: schedule project/site consistency; assignment project/site consistency; crew-lead office consistency; completed/rescheduled successor and lineage-chain semantics; assignment interval overlap; and safety-threshold effective-period conflict/overlap.

## Silver validation responsibilities

- Critical failures are excluded from accepted Silver, written to quarantine, and logged.
- Warnings remain eligible for accepted Silver with the source value unchanged and the warning attached/logged.
- Info outcomes remain eligible; only explicitly defined meaning-preserving normalization is permitted.
- Every outcome uses the stable rule ID and error code in `silver-validation-rule-mapping-matrix.md`.
- Bronze source values and lineage are preserved. Missing business values are never invented.

## Locked implementation policies for the first Silver increment

- **Empty strings:** only `null`/Python `None` and the exact empty string `""` are missing. Whitespace-only strings are preserved and are not trimmed or silently treated as empty.
- **Dates and timestamps:** current generated ISO-compatible text is parsed explicitly with Python ISO date/timestamp parsing. A malformed required date or timestamp is Critical. No time-zone conversion is performed, and original text is retained in the source record.
- **Numeric comparison:** derived numeric equality uses decimal conversion from source text and an absolute tolerance of `0.000001`. It does not use exact binary floating-point equality.
- **Multi-record quarantine:** all records participating in duplicate keys, overlaps, cycles, or conflicting sets are quarantined unless a future approved rule explicitly defines a survivor.

## Deferred Version 2 rules

Direct job-site weather requests, observed-weather forecast accuracy, advanced employee-role eligibility, explicit equipment transit/handoff states, and multi-crew/shared-equipment allocation remain deferred. This reconciliation does not add them.
