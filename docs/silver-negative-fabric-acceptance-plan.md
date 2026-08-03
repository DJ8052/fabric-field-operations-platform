# Operational Silver Negative Fabric Acceptance Plan

## Purpose

This workflow proves the three Silver disposition paths with deterministic repository-backed input: Critical findings quarantine and log, Warning findings remain accepted and log, and Info findings remain accepted and log. It does not attempt exhaustive rule coverage and does not include FSD-008.

## Isolation and identifiers

- The notebook's default Lakehouse must have Lakehouse schemas enabled; the three `_negative` schemas are created by the Silver notebook before it writes tables.
- Clean source remains at `Files/source/operations`.
- Negative source is uploaded to `Files/source/operations_negative`.
- Use a distinct Bronze run ID such as `negative-acceptance-v1`.
- Always pass `source_run_id=negative-acceptance-v1` explicitly to Silver. Do not allow latest-run discovery to select acceptance data.
- Use isolated Silver paths because the Silver notebook overwrites accepted entity outputs:
  - `silver_root=Tables/silver_negative`
  - `quarantine_root=Tables/quarantine_negative`
  - `validation_results_root=Tables/validation_negative/operational_results`
- Do not point a normal pipeline at the negative source root or negative Silver roots.

## Scenario inventory

| Scenario | Entity / records | Mutation | Expected rules and error codes | Severity | Disposition |
| --- | --- | --- | --- | --- | --- |
| `warning_region_name_missing` | Region `1` | Blank `region_name` | REG-003 / `WARN_REGION_NAME_MISSING` | Warning | Accepted and logged |
| `info_equipment_assignment_adjacent` | Equipment Assignment `1`, `81` | Assignment 81 starts exactly when assignment 1 ends | EQA-004 / `INFO_EQUIPMENT_ASSIGNMENT_ADJACENT_BOUNDARY` on both | Info | Both accepted and logged |
| `critical_job_site_weather_location` | Job Site `1` | Set `weather_location_code=TX-UNKNOWN` | JBS-004 / `ERR_JOB_SITE_WEATHER_LOCATION_INVALID`; XEN-007 / `ERR_CROSS_WEATHER_LOCATION_INVALID` | Critical | Quarantined and logged |
| `critical_equipment_assignment_overlap` | Equipment Assignment `2`, `82` | Move assignment 82 into assignment 2's period | EQA-003 / `ERR_EQUIPMENT_ASSIGNMENT_OVERLAP`; XEN-005 / `ERR_CROSS_EQUIPMENT_ASSIGNMENT_OVERLAP` on both | Critical | Both quarantined and logged |

The expected total is 921 rows read, 918 accepted, 3 quarantined, 6 Critical results, 1 Warning result, and 2 Info results. The generated `expected-results.json` is the machine-readable acceptance contract and obtains rule metadata from `rule_registry.py`.

## Generate locally

From the repository root:

```powershell
$env:UV_CACHE_DIR='.uv-cache'
uv run --isolated --python 3.12 python scripts/generate_operational_negative_acceptance_data.py
```

The command writes 12 flat CSVs plus `expected-results.json` under `data/negative_acceptance/operations/`. Upload only the 12 CSVs to `Files/source/operations_negative`, retaining their entity filenames. The manifest is evidence for comparison and is not a Bronze input.

## Fabric execution

1. Generate the files locally and compare the printed scenario inventory with `expected-results.json`.
2. Upload all 12 entity CSVs to `Files/source/operations_negative`. Do not replace files under `Files/source/operations`.
3. Run `NB_Operational_Bronze_Ingestion` through the existing pipeline with:
   - `source_root=Files/source/operations_negative`
   - `INGESTION_DATE=<acceptance date>`
   - `RUN_ID=negative-acceptance-v1`
   - `OVERWRITE=False`
4. Confirm all 12 monitoring rows succeeded. If rerunning the same date, use a new versioned run ID; do not enable overwrite merely for convenience.
5. Run `NB_Operational_Silver_Validation` with:
   - `ingestion_date=<same acceptance date>`
   - `source_run_id=negative-acceptance-v1`
   - `silver_run_id=silver-negative-acceptance-v1`
   - `silver_root=Tables/silver_negative`
   - `quarantine_root=Tables/quarantine_negative`
   - `validation_results_root=Tables/validation_negative/operational_results`
6. Capture the notebook summary and query the isolated outputs below.

The Bronze notebook retains its clean default `Files/source/operations`; negative behavior is selected only by the parameter.

## Verification queries

```sql
-- Bronze monitoring: exactly 12 successful entities and 921 rows.
SELECT status, COUNT(*) AS entity_count, SUM(row_count) AS row_count
FROM monitoring_operational_ingestion_runs
WHERE run_id = 'negative-acceptance-v1'
GROUP BY status;

-- Findings: Critical=6, Warning=1, Info=2.
SELECT severity, COUNT(*) AS finding_count
FROM validation_negative.operational_results
WHERE run_id = 'silver-negative-acceptance-v1'
GROUP BY severity;

-- Exact result evidence.
SELECT entity, record_id, rule_id, error_code, severity, outcome
FROM validation_negative.operational_results
WHERE run_id = 'silver-negative-acceptance-v1'
ORDER BY entity, record_id, rule_id;

-- Warning record remains accepted.
SELECT region_id, region_name
FROM silver_negative.regions
WHERE region_id = '1';

-- Info records remain accepted.
SELECT assignment_id, equipment_id, assignment_start_timestamp, assignment_end_timestamp
FROM silver_negative.equipment_assignments
WHERE assignment_id IN ('1', '81');

-- Critical Job Site record is quarantined.
SELECT record_id, critical_rule_ids, all_rule_ids, source_record_json
FROM quarantine_negative.job_sites
WHERE run_id = 'silver-negative-acceptance-v1';

-- Both overlap participants are quarantined.
SELECT record_id, critical_rule_ids, all_rule_ids, source_record_json
FROM quarantine_negative.equipment_assignments
WHERE run_id = 'silver-negative-acceptance-v1'
ORDER BY record_id;
```

Also verify accepted Job Sites contain 119 rows and accepted Equipment Assignments contain 118 rows. All other accepted entity counts equal the clean generator counts.

## Cleanup and retention

Retain the generated manifest, Fabric notebook output, monitoring query results, and validation query results as acceptance evidence. Negative Bronze files and isolated managed Delta tables may be retained under their clearly named schemas according to the project retention policy. If removal is approved later, target only `operations_negative` and the three `_negative` schemas. Never delete or overwrite the clean source or clean Silver tables.

Latest-run discovery is appropriate for manual clean execution but unsafe for this acceptance run. A negative run can be the latest successful Bronze run, so both acceptance and subsequent clean executions should supply explicit `source_run_id` values until a clean run is again known to be latest.
