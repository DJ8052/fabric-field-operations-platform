# Silver Validation Rule Mapping Matrix

## Purpose

This Phase 10, Step 3 matrix is the implementation gate for operational Silver validation. It maps every rule in the reconciled Operational Data Contracts exactly once. It specifies behavior; it does not implement it.

Severity behavior is fixed:

- **Critical**: fail the record, exclude it from accepted Silver, write it to quarantine, and log the result.
- **Warning**: keep the record eligible for Silver, attach and log the warning, and do not silently change the source value.
- **Info**: keep the record eligible for Silver and log the defined informational/normalization outcome. Normalization is allowed only when explicitly stated and business meaning is unchanged.

`original_contract_classification` is preserved. Rows marked **Design unresolved** are not permission to skip the rule: implementation is gated until the named decision is approved.

| entity | rule_id | rule_description | original_contract_classification | new_severity | silver_action | error_code |
| --- | --- | --- | --- | --- | --- | --- |
| Region | REG-001 | Reject when `region_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_REGION_CODE_REQUIRED |
| Region | REG-002 | Reject duplicate Region.`region_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_REGION_CODE_DUPLICATE |
| Region | REG-003 | Warn when `region_name` is null or empty; whitespace policy is unresolved. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_REGION_NAME_MISSING |
| Office | OFF-001 | Reject when `office_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_OFFICE_CODE_REQUIRED |
| Office | OFF-002 | Reject when `region_id` does not resolve to Region.`region_id`. | Hard Reject | Critical | Quarantine and log. | ERR_OFFICE_REGION_FK_INVALID |
| Office | OFF-003 | Reject duplicate Office.`office_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_OFFICE_CODE_DUPLICATE |
| Office | OFF-004 | Warn when `office_name` is null or empty; whitespace policy is unresolved. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_OFFICE_NAME_MISSING |
| Employee | EMP-001 | Reject when `employee_number` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_EMPLOYEE_NUMBER_REQUIRED |
| Employee | EMP-002 | Reject when `home_office_id` does not resolve to Office.`office_id`. | Hard Reject | Critical | Quarantine and log. | ERR_EMPLOYEE_HOME_OFFICE_FK_INVALID |
| Employee | EMP-003 | Reject duplicate Employee.`employee_number`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_EMPLOYEE_NUMBER_DUPLICATE |
| Employee | EMP-004 | Warn when an Employee with `employment_status = 'Terminated'` is referenced as a crew lead; complete status/case domain is unresolved. | Warn and Flag | Warning | Retain affected source record(s), attach warning, and log. | WARN_TERMINATED_EMPLOYEE_CREW_LEAD |
| Project | PRJ-001 | Reject when `project_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_PROJECT_CODE_REQUIRED |
| Project | PRJ-002 | Reject duplicate Project.`project_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_PROJECT_CODE_DUPLICATE |
| Project | PRJ-003 | Warn when `project_name` is null or empty; whitespace policy is unresolved. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_PROJECT_NAME_MISSING |
| Job Site | JBS-001 | Reject when `job_site_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_JOB_SITE_CODE_REQUIRED |
| Job Site | JBS-002 | Reject when `project_id` does not resolve to Project.`project_id`. | Hard Reject | Critical | Quarantine and log. | ERR_JOB_SITE_PROJECT_FK_INVALID |
| Job Site | JBS-003 | Reject duplicate Job Site.`job_site_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_JOB_SITE_CODE_DUPLICATE |
| Job Site | JBS-004 | Reject unless `weather_location_code` is `TX-DAL`, `TX-HOU`, or `TX-AUS`. | Hard Reject | Critical | Quarantine and log. | ERR_JOB_SITE_WEATHER_LOCATION_INVALID |
| Crew | CRW-001 | Reject when `crew_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_CREW_CODE_REQUIRED |
| Crew | CRW-002 | Reject when `home_office_id` does not resolve to Office.`office_id`. | Hard Reject | Critical | Quarantine and log. | ERR_CREW_HOME_OFFICE_FK_INVALID |
| Crew | CRW-003 | Reject duplicate Crew.`crew_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_CREW_CODE_DUPLICATE |
| Crew | CRW-004 | When populated, reject unless `crew_lead_employee_id` resolves to Employee with `employment_status = 'Active'`; case policy is unresolved. | Hard Reject | Critical | Quarantine and log. | ERR_CREW_LEAD_NOT_ACTIVE |
| Crew | CRW-005 | Warn when the resolved crew lead's `home_office_id` differs from Crew.`home_office_id`. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_CREW_LEAD_OFFICE_MISMATCH |
| Crew | CRW-006 | Warn when `crew_lead_employee_id` is null or empty. | Warn and Flag | Warning | Retain, attach warning, and log. | WARN_CREW_LEAD_MISSING |
| Activity | ACT-001 | Reject when `activity_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_ACTIVITY_CODE_REQUIRED |
| Activity | ACT-002 | Reject duplicate Activity.`activity_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_ACTIVITY_CODE_DUPLICATE |
| Activity | ACT-003 | Warn when `activity_name` is null or empty; whitespace policy is unresolved. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_ACTIVITY_NAME_MISSING |
| Field Schedule | FSD-001 | Reject unless parsed `scheduled_end_timestamp` is greater than parsed `scheduled_start_timestamp`; parsing/time-zone policy is unresolved. | Hard Reject | Critical | Design unresolved for parsing policy; once approved, quarantine failures and log. | ERR_FIELD_SCHEDULE_WINDOW_INVALID |
| Field Schedule | FSD-002 | Reject unless `scheduled_date` equals the date portion of `scheduled_start_timestamp`. | Hard Reject | Critical | Quarantine and log. | ERR_FIELD_SCHEDULE_DATE_MISMATCH |
| Field Schedule | FSD-003 | Warn unless `planned_crew_hours` equals schedule duration in hours; the former adjustment exception has no source column and is unresolved. | Warn and Flag | Warning | Retain, attach warning, log; design decision required for exceptions. | WARN_FIELD_SCHEDULE_CREW_HOURS_MISMATCH |
| Field Schedule | FSD-004 | Reject unless `planned_labor_hours = planned_crew_hours * planned_crew_size`; schedule staffing is authoritative. | Hard Reject | Critical | Quarantine and log. | ERR_FIELD_SCHEDULE_LABOR_HOURS_INVALID |
| Field Schedule | FSD-005 | Reject unless schedule `project_id` equals the project on its resolved `job_site_id`. | Hard Reject | Critical | Quarantine and log. | ERR_FIELD_SCHEDULE_PROJECT_SITE_MISMATCH |
| Field Schedule | FSD-006 | Reject when a `Completed` row is referenced as a reschedule predecessor. | Hard Reject | Critical | Quarantine affected lineage record(s) and log. | ERR_COMPLETED_SCHEDULE_RESCHEDULED |
| Field Schedule | FSD-007 | Reject when a `Rescheduled` row has no resolving successor. | Hard Reject | Critical | Quarantine affected lineage record(s) and log. | ERR_RESCHEDULE_SUCCESSOR_MISSING |
| Field Schedule | FSD-008 | Detect timestamp edits after rescheduling using a prior immutable snapshot; that source/enforcement architecture is unresolved. | Hard Reject | Critical | Design unresolved; implementation is blocked until comparison state is approved. | ERR_RESCHEDULE_ORIGINAL_TIMESTAMP_CHANGED |
| Field Schedule | FSD-009 | Reject self-reference or any cycle in `rescheduled_from_schedule_id` predecessor traversal. | Hard Reject | Critical | Quarantine affected lineage record(s) and log. | ERR_RESCHEDULE_LINEAGE_CYCLE |
| Field Schedule | FSD-010 | Reject unless `status` is `Scheduled`, `In Progress`, `Completed`, `Delayed`, `Cancelled`, or `Rescheduled`. | Hard Reject | Critical | Quarantine and log. | ERR_FIELD_SCHEDULE_STATUS_INVALID |
| Equipment Type | EQT-001 | Reject when `equipment_type_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_EQUIPMENT_TYPE_CODE_REQUIRED |
| Equipment Type | EQT-002 | Reject duplicate Equipment Type.`equipment_type_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_EQUIPMENT_TYPE_CODE_DUPLICATE |
| Equipment Type | EQT-003 | Warn when `equipment_type_name` is null or empty; whitespace policy is unresolved. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_EQUIPMENT_TYPE_NAME_MISSING |
| Equipment | EQP-001 | Reject when `equipment_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_EQUIPMENT_CODE_REQUIRED |
| Equipment | EQP-002 | Reject when `equipment_type_id` does not resolve to Equipment Type.`equipment_type_id`. | Hard Reject | Critical | Quarantine and log. | ERR_EQUIPMENT_TYPE_FK_INVALID |
| Equipment | EQP-003 | Reject duplicate Equipment.`equipment_code`. | Hard Reject | Critical | Quarantine duplicate-key records and log. | ERR_EQUIPMENT_CODE_DUPLICATE |
| Equipment | EQP-004 | Warn when `equipment_status` is null/empty; domain membership awaits a complete approved domain. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_EQUIPMENT_STATUS_MISSING_OR_DOMAIN_UNRESOLVED |
| Equipment Assignment | EQA-001 | When populated, reject unless parsed `assignment_end_timestamp` is greater than parsed `assignment_start_timestamp`; parsing policy is unresolved. | Hard Reject | Critical | Design unresolved for parsing policy; quarantine deterministic failures and log. | ERR_EQUIPMENT_ASSIGNMENT_WINDOW_INVALID |
| Equipment Assignment | EQA-002 | Reject unless assignment `project_id` equals the project on its resolved `job_site_id`. | Hard Reject | Critical | Quarantine and log. | ERR_EQUIPMENT_ASSIGNMENT_PROJECT_SITE_MISMATCH |
| Equipment Assignment | EQA-003 | Reject overlapping periods for the same `equipment_id`; null end is open-ended and equality at a boundary is non-overlap. | Hard Reject | Critical | Quarantine affected assignments and log. | ERR_EQUIPMENT_ASSIGNMENT_OVERLAP |
| Equipment Assignment | EQA-004 | Log when one assignment end equals another start for the same `equipment_id`; the boundary is valid. | Informational | Info | Retain unchanged and log accepted adjacency. | INFO_EQUIPMENT_ASSIGNMENT_ADJACENT_BOUNDARY |
| Safety Threshold | SFT-001 | Reject when populated `effective_end_date` precedes `effective_start_date`; parsing policy is unresolved. | Hard Reject | Critical | Design unresolved for parsing policy; quarantine deterministic failures and log. | ERR_SAFETY_THRESHOLD_EFFECTIVE_DATES_INVALID |
| Safety Threshold | SFT-002 | Reject overlapping active periods for equal (`activity_id`, `metric_code`, `severity`, `equipment_type_id`), with null end open-ended. | Hard Reject | Critical | Quarantine conflicting rules and log. | ERR_SAFETY_THRESHOLD_ACTIVE_PERIOD_OVERLAP |
| Safety Threshold | SFT-003 | Enforce `IN` for verified `WEATHER_CODE` and `>=` for other generated metrics; complete metric/operator registry is unresolved. | Hard Reject | Critical | Design unresolved beyond verified metrics; quarantine known incompatibilities and log. | ERR_SAFETY_THRESHOLD_OPERATOR_INCOMPATIBLE |
| Safety Threshold | SFT-004 | For `WEATHER_CODE`, reject unless `weather_code_set` is populated and `threshold_value` is null/empty. | Hard Reject | Critical | Quarantine and log. | ERR_SAFETY_THRESHOLD_WEATHER_STRUCTURE_INVALID |
| Safety Threshold | SFT-005 | For non-`WEATHER_CODE`, reject unless `threshold_value` is numeric and `weather_code_set` is empty; unit/bounds registry is unresolved. | Hard Reject | Critical | Design unresolved for unit/bounds; quarantine structural failures and log. | ERR_SAFETY_THRESHOLD_NUMERIC_STRUCTURE_INVALID |
| Safety Threshold | SFT-006 | Reject when `recommended_action_code` is null or empty. | Hard Reject | Critical | Quarantine and log. | ERR_SAFETY_THRESHOLD_ACTION_REQUIRED |
| Safety Threshold | SFT-007 | Reject when `severity = 'CRITICAL'` and `override_flag` is not boolean `true`. | Hard Reject | Critical | Quarantine and log. | ERR_SAFETY_THRESHOLD_CRITICAL_OVERRIDE_REQUIRED |
| Safety Threshold | SFT-008 | Reject simultaneous same-scope rules with different operator, unit, threshold payload, action, or override. | Hard Reject | Critical | Quarantine conflicting rules and log. | ERR_SAFETY_THRESHOLD_ACTIVE_RULE_CONFLICT |
| Cross-Entity | XEN-001 | Reject any unresolved relationship in the 19-FK register; nullable FKs are conditional. | Hard Reject | Critical | Quarantine record with invalid FK and log relationship detail. | ERR_CROSS_ENTITY_FK_INVALID |
| Cross-Entity | XEN-002 | Reject schedule project/site inconsistency. | Hard Reject | Critical | Quarantine and log. | ERR_CROSS_FIELD_SCHEDULE_PROJECT_SITE_MISMATCH |
| Cross-Entity | XEN-003 | Reject assignment project/site inconsistency. | Hard Reject | Critical | Quarantine and log. | ERR_CROSS_EQUIPMENT_ASSIGNMENT_PROJECT_SITE_MISMATCH |
| Cross-Entity | XEN-004 | Reject unresolved, self-referencing, or cyclic reschedule lineage. | Hard Reject | Critical | Quarantine affected lineage record(s) and log. | ERR_CROSS_RESCHEDULE_LINEAGE_INVALID |
| Cross-Entity | XEN-005 | Reject assignment overlap for the same `equipment_id` under EQA-003. | Hard Reject | Critical | Quarantine affected assignments and log. | ERR_CROSS_EQUIPMENT_ASSIGNMENT_OVERLAP |
| Cross-Entity | XEN-006 | Reject threshold active-period overlap under SFT-002. | Hard Reject | Critical | Quarantine conflicting thresholds and log. | ERR_CROSS_SAFETY_THRESHOLD_PERIOD_OVERLAP |
| Cross-Entity | XEN-007 | Reject Job Site weather locations outside `TX-DAL`, `TX-HOU`, `TX-AUS`. | Hard Reject | Critical | Quarantine and log. | ERR_CROSS_WEATHER_LOCATION_INVALID |
| Cross-Entity | XEN-008 | Warn when a populated crew lead resolves to a different home office than the crew. | Warn and Flag | Warning | Retain, attach warning, log; no source change. | WARN_CROSS_CREW_LEAD_OFFICE_MISMATCH |
| Cross-Entity | XEN-009 | Reject duplicate listed entity business keys or duplicate source identifiers for schedule, assignment, or threshold. | Hard Reject | Critical | Quarantine duplicate records and log entity/key. | ERR_CROSS_ENTITY_BUSINESS_KEY_DUPLICATE |
| Cross-Entity | XEN-010 | Reject null/empty values in the explicit Critical value set in the contract; exclude fields governed by missing-value Warning rules, do not trim whitespace, and never fill values. | Hard Reject | Critical | Quarantine and log; do not impute. | ERR_CROSS_ENTITY_REQUIRED_VALUE_MISSING |

## Mapping totals

| Measure | Count |
| --- | ---: |
| Total rules | 66 |
| Original Hard Reject | 54 |
| Original Warn and Flag | 11 |
| Original Informational | 1 |
| New Critical | 54 |
| New Warning | 11 |
| New Info | 1 |

There are no severity reclassifications. Ambiguity is exposed in the rule description and action rather than hidden by a mechanical implementation assumption.

## Implementation status

The local Python validation package implements 65 of the 66 mapped rules. The transactional increment implements `FSD-001`–`FSD-007`, `FSD-009`, `FSD-010`, `EQA-001`–`EQA-004`, `SFT-001`–`SFT-008`, and `XEN-002`–`XEN-006`. `FSD-008` is deferred from Silver Version 1 because a single Bronze batch contains no immutable prior state or change-event evidence for detecting timestamp edits after rescheduling. It is not present in the implemented rule registry and is not silently treated as complete; the rule remains in this matrix pending an approved historical comparison source.

Phase 10 Step 3 — Operational Silver Validation is complete under the approved 65-rule Version 1 boundary. This status is supported by 129 passing local tests, the clean 921-row Fabric baseline, and the isolated negative Fabric acceptance run. The negative run produced 921 rows read, 918 accepted, 3 quarantined, 6 Critical findings, 1 Warning finding, and 2 Info findings; its quarantine and validation outputs were verified through the Fabric SQL analytics endpoint. Bronze and Silver remain Python/PySpark-based. FSD-008 remains deferred pending an approved historical comparison source, and Gold/dbt work remains a later phase.
