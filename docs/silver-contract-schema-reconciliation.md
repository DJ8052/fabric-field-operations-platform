# Silver Contract–Schema Reconciliation

## Executive summary

Phase 10, Step 3 reconciled the approved Operational Data Contracts to the actual generated CSV/Bronze schemas and produced the Silver validation implementation gate. All 12 source grains remain unchanged. The audit found confirmed name drift (`schedule_id`/`field_schedule_id`, schedule and project status names), contract omissions, and three contract-only Field Schedule fields. It also disproved several suspected discrepancies: `employment_status`, `crew_status`, and `weather_location_code` are present in generated and Bronze-required schemas.

The reconciled contract contains 66 validation rules. Every rule appears exactly once in `silver-validation-rule-mapping-matrix.md`: 54 Critical, 11 Warning, and 1 Info. The verified source model has **19 foreign-key relationships**. The design audit preceded implementation; the current increment now includes the master-entity Silver package and orchestration notebook described below.

## Evidence sources reviewed

- `src/operational_data_generator/entities.py`: generated row dictionaries and exact output column order.
- `src/operational_data_generator/generator.py`: 12-entity orchestration.
- `src/operational_data_generator/writers.py`: emitted CSV headers come from generated row keys.
- `src/operational_data_generator/validators.py`: accepted-dataset domains, relationships, lineage, labor-hour, interval, and threshold checks.
- `src/operational_bronze_ingestion/entity_config.py`: minimum Bronze columns for all 12 entities.
- `src/operational_bronze_ingestion/ingest.py`: header validation and byte-preserving Bronze copy.
- `tests/test_operational_data_generator.py` and `tests/test_ingest.py`: schema, dependency, scenario, lineage, reproducibility, and header assertions.
- `src/operational_data_generator/config.py`, `config/locations.yml`, and existing operational design documents.

No checked-in generated CSV fixture is present. Generator keys are direct header evidence because `writers.py` uses them as `csv.DictWriter` field names.

## Schema audit

“Required” is verified by `EntityConfig.required_columns`; “optional” is emitted but not header-required. The prior-contract column identifies exact, differently named, or omitted fields.

### Region

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `region_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `region_code` | Required | Exact | Retain. |
| `region_name` | Required | Exact | Retain. |
| `region_description` | Optional | Exact | Retain optional. |

### Office

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `office_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `office_code` | Required | Exact | Retain. |
| `office_name` | Required | Exact | Retain. |
| `region_id` | Required FK | Exact | Retain. |
| `office_description` | Optional | Exact | Retain optional. |

### Employee

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `employee_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `employee_number` | Required | Exact | Retain. |
| `employee_name` | Required | Exact | Retain. |
| `home_office_id` | Required FK | Exact | Retain. |
| `employment_status` | Required | Exact; suspected absence disproved | Retain; generator emits `Active`. |
| `termination_date` | Optional | Exact | Retain optional. |
| `employee_role_code` | Optional | Exact | Retain optional. |

### Project

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `project_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `project_code` | Required | Exact | Retain. |
| `project_name` | Required | Exact | Retain. |
| `office_id` | Required FK | Omitted | Add field and relationship. |
| `project_manager_employee_id` | Required FK | Omitted | Add field and relationship. |
| `field_manager_employee_id` | Required FK | Omitted | Add field and relationship. |
| `status` | Required | Different name: `project_status` | Use `status`. |
| `project_start_date` | Optional | Omitted | Add optional. |
| `project_end_date` | Optional | Omitted | Add optional. |
| `priority_code` | Optional | Omitted | Add optional. |
| `project_description` | Optional | Exact | Retain optional. |
| `parent_project_code` | Optional | Exact | Retain; do not infer an FK. |

### Job Site

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `job_site_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `job_site_code` | Required | Exact | Retain. |
| `job_site_name` | Required | Exact | Retain. |
| `project_id` | Required FK | Exact | Retain. |
| `weather_location_code` | Required | Exact; suspected `location_id` disproved | Retain exact name/domain. |
| `job_site_description` | Optional | Exact | Retain optional. |

### Crew

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `crew_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `crew_code` | Required | Exact | Retain. |
| `home_office_id` | Required FK | Exact | Retain. |
| `crew_lead_employee_id` | Optional conditional FK | Exact | Retain conditional check. |
| `crew_status` | Required | Exact; suspected absence disproved | Retain; generator emits `Active`. |
| `crew_description` | Optional | Exact | Retain optional. |

### Activity

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `activity_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `activity_code` | Required | Exact | Retain. |
| `activity_name` | Required | Exact | Retain. |
| `activity_description` | Optional | Exact | Retain optional. |
| `activity_category` | Optional | Exact | Retain optional. |

### Field Schedule

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `field_schedule_id` | Required | Different name: `schedule_id` | Use exact generated/Bronze name. |
| `project_id` | Required FK | Exact | Retain. |
| `job_site_id` | Required FK | Exact | Retain. |
| `crew_id` | Required FK | Exact | Retain. |
| `activity_id` | Required FK | Omitted | Add field and relationship. |
| `scheduled_start_timestamp` | Required | Exact | Retain. |
| `scheduled_end_timestamp` | Required | Exact | Retain. |
| `scheduled_date` | Required | Exact | Retain. |
| `planned_crew_hours` | Required | Exact | Retain. |
| `planned_crew_size` | Required | Omitted | Add; authoritative labor multiplier. |
| `planned_labor_hours` | Required | Exact | Retain. |
| `status` | Required | Different name: `schedule_status` | Use exact generated/Bronze name. |
| `rescheduled_from_schedule_id` | Required column; nullable value; conditional self-FK | Exact | Clarify header/value semantics. |
| `scenario_id` | Optional | Omitted | Add generated test metadata. |

Prior contract fields absent from generated and Bronze schemas:

| Contract-only field | Prior status | Action |
| --- | --- | --- |
| `cancellation_reason_code` | Nullable | Remove from Version 1 schema; no rule depends on it. |
| `approved_adjustment_flag` | Nullable | Remove; FSD-003 exception remains unresolved. |
| `approved_exception_note` | Nullable | Remove; FSD-003 exception remains unresolved. |

Labor-hours evidence: generator and validator both use `planned_labor_hours = planned_crew_hours * planned_crew_size`, and tests require `planned_crew_size`. Crew has no `crew_size`. Field Schedule.`planned_crew_size` is therefore authoritative in Version 1. A nominal comparison is impossible with current fields and no mismatch error is defined.

### Equipment Type

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `equipment_type_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `equipment_type_code` | Required | Exact | Retain. |
| `equipment_type_name` | Required | Exact | Retain. |
| `equipment_type_description` | Optional | Exact | Retain optional. |
| `equipment_category` | Optional | Exact | Retain optional. |

### Equipment

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `equipment_id` | Required | Candidate key only; omitted from lists | Add to Required fields. |
| `equipment_code` | Required | Exact | Retain. |
| `equipment_type_id` | Required FK | Exact | Retain. |
| `equipment_status` | Required | Exact | Retain; domain unresolved. |
| `serial_number` | Optional | Exact | Retain optional. |
| `asset_tag` | Optional | Exact | Retain optional. |
| `equipment_description` | Optional | Exact | Retain optional. |

### Equipment Assignment

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `assignment_id` | Required | Exact | Retain. |
| `equipment_id` | Required FK | Exact | Retain. |
| `job_site_id` | Required FK | Exact | Retain. |
| `project_id` | Required FK | Exact | Retain. |
| `assignment_start_timestamp` | Required | Exact | Retain. |
| `assignment_end_timestamp` | Optional | Exact | Retain conditional check. |
| `assignment_note` | Optional | Exact | Retain optional. |
| `scenario_id` | Optional | Omitted | Add generated test metadata. |

### Safety Threshold

| Actual field | Verified status | Prior contract | Action |
| --- | --- | --- | --- |
| `threshold_id` | Required | Exact | Retain. |
| `activity_id` | Required FK | Exact | Retain. |
| `equipment_type_id` | Optional conditional FK | Exact | Retain conditional check. |
| `metric_code` | Required | Exact | Retain. |
| `comparison_operator` | Required | Exact | Retain. |
| `unit` | Required | Exact | Retain. |
| `threshold_value_or_code_set` | Required | Exact | Retain. |
| `threshold_value` | Optional | Exact | Retain conditional structure. |
| `weather_code_set` | Optional | Exact | Retain conditional structure. |
| `severity` | Required | Exact | Retain. |
| `recommended_action_code` | Required | Exact | Retain. |
| `effective_start_date` | Required | Exact | Retain. |
| `effective_end_date` | Optional | Exact | Retain. |
| `is_active` | Required | Exact | Retain. |
| `override_flag` | Required | Exact | Retain. |

## Contract changes made

- Added generated source identifiers wherever Bronze requires them.
- Reconciled Project.`status`, its three omitted FKs, and other emitted fields.
- Confirmed `weather_location_code`, `employment_status`, and `crew_status` exist.
- Reconciled Field Schedule identifiers/status and added `activity_id`, `planned_crew_size`, and `scenario_id`.
- Added Equipment Assignment.`scenario_id`.
- Removed three nonexistent schedule fields while retaining the resulting unresolved rule conflict.
- Made subjective rules deterministic or explicitly unresolved without changing enforcement classification.
- Corrected warning semantics so warning records remain Silver-eligible.

## Foreign-key recount: 19

1. Office.`region_id` -> Region.`region_id` (required)
2. Employee.`home_office_id` -> Office.`office_id` (required)
3. Project.`office_id` -> Office.`office_id` (required)
4. Project.`project_manager_employee_id` -> Employee.`employee_id` (required)
5. Project.`field_manager_employee_id` -> Employee.`employee_id` (required)
6. Job Site.`project_id` -> Project.`project_id` (required)
7. Crew.`home_office_id` -> Office.`office_id` (required)
8. Crew.`crew_lead_employee_id` -> Employee.`employee_id` (conditional when populated)
9. Field Schedule.`project_id` -> Project.`project_id` (required)
10. Field Schedule.`job_site_id` -> Job Site.`job_site_id` (required)
11. Field Schedule.`crew_id` -> Crew.`crew_id` (required)
12. Field Schedule.`activity_id` -> Activity.`activity_id` (required)
13. Field Schedule.`rescheduled_from_schedule_id` -> Field Schedule.`field_schedule_id` (conditional self-reference)
14. Equipment.`equipment_type_id` -> Equipment Type.`equipment_type_id` (required)
15. Equipment Assignment.`equipment_id` -> Equipment.`equipment_id` (required)
16. Equipment Assignment.`job_site_id` -> Job Site.`job_site_id` (required)
17. Equipment Assignment.`project_id` -> Project.`project_id` (required)
18. Safety Threshold.`activity_id` -> Activity.`activity_id` (required)
19. Safety Threshold.`equipment_type_id` -> Equipment Type.`equipment_type_id` (conditional when populated)

Not counted as FKs: schedule and assignment project/site equality; crew-lead/crew office equality; completed/rescheduled successor and lineage semantics; assignment overlap; threshold period overlap/conflict.

## Locked policies for the first implementation increment

- Null and exact empty string are missing. Whitespace-only strings are preserved, are not trimmed, and are not treated as empty.
- ISO-compatible generated date/timestamp text is parsed explicitly. Malformed required values are Critical; no time-zone conversion is invented; original text is preserved.
- Derived numeric equality uses decimal conversion and absolute tolerance `0.000001`, avoiding binary-float equality.
- Every record participating in a duplicate, overlap, cycle, or conflicting set is quarantined unless an approved rule defines otherwise.
- XEN-010 uses an explicit Critical value set and excludes fields with an explicit missing-value Warning rule. This resolves the prior contradiction between generic required-value rejection and warning-only name/status rules.

## Unresolved architecture decisions

- Whether a future explicitly approved Info rule should normalize whitespace; no trimming is authorized now.
- Complete, case-sensitive Employee, Crew, and Equipment status domains.
- Timestamp/date parsing, malformed-value behavior, and time-zone policy.
- A source mechanism for the prior schedule adjustment/exception clause.
- Immutable prior-state/change-event storage for rescheduled timestamp comparisons.
- Whether to add a nominal crew-size source; Crew currently has none.
- A complete safety metric/operator/unit/bounds registry.
- Quarantine ownership for pair/set rules (both records versus a designated survivor).

## Rule mapping reconciliation

| Classification/severity | Count |
| --- | ---: |
| Original Hard Reject / Critical | 54 |
| Original Warn and Flag / Warning | 11 |
| Original Informational / Info | 1 |
| **Total** | **66** |

The contract and matrix contain the same 66 unique rule IDs exactly once, and all 66 error codes are unique. No rule changes enforcement behavior.

## Implementation boundary

The Phase 10, Step 3 design gate is complete. The reusable Silver package now locally implements the master entities plus deterministic Field Schedule, Equipment Assignment, and Safety Threshold validation. The newly implemented IDs are `FSD-001`–`FSD-007`, `FSD-009`, `FSD-010`, `EQA-001`–`EQA-004`, `SFT-001`–`SFT-008`, and `XEN-002`–`XEN-006`. `FSD-008` is deferred from Silver Version 1 because immutable prior-state or change-event evidence is unavailable in a single Bronze batch. The package therefore implements 65 of 66 mapped rules and does not claim the entire Silver layer is complete. Clean Bronze-to-Silver Fabric validation succeeded with 921 rows accepted and no findings; isolated negative-data Fabric acceptance remains pending. Bronze and Silver remain Python/PySpark-based; Gold dimensional models, tests, lineage, and documentation will use dbt.

The Silver package is distributed as a `.whl` (Python wheel): a versioned, installable archive built from `src/operational_silver_validation`. Following the established Bronze deployment pattern, the wheel is uploaded to and installed in the Fabric Environment attached to the notebook. Fabric then imports `operational_silver_validation` normally. This keeps reusable, unit-tested rule logic out of notebook cells, makes deployments reproducible, and lets the notebook focus on Bronze reads, package invocation, Delta writes, and run summaries.

`src/operational_silver_validation/validation_engine.py` is the single high-level engine. `validate_operational_entities` executes all 12 entities, while `validate_master_entities` remains as the backward-compatible first-increment API. The engine invokes entity and relationship checks in deterministic order, aggregates results, separates accepted and quarantined rows, retains Warning and Info results and multiple violations, and produces typed entity and overall summaries. Entity-specific findings remain in `entity_validations.py`; relationship-specific findings remain in `relationship_validations.py`. `__init__.py` contains public exports only. The notebook contains orchestration only and has no rule metadata or validation calculations. It reads Bronze CSV values without schema inference to preserve source text and overwrites accepted entity output even when no rows are accepted, preventing stale accepted data.

Notebook/pipeline runtime values are resolved by `runtime_config.py`. Fabric may supply lowercase `ingestion_date`, `source_run_id`, `silver_run_id`, and path parameters. Supplied values take precedence. Development execution defaults to today's ISO date and source run `dev-local`; the default Silver run ID is deterministically derived from those values. No historical production run is permanently selected.
