# Phase 11.1 — Silver Source Verification

## Status and evidence basis

**Phase 11.1 — Discovery & Requirements Reconciliation: COMPLETE.**

The project owner completed the read-only Fabric notebook `NB_Phase11_Silver_Source_Verification` and independently inspected the SQL analytics endpoint. Its final result was **PHASE 11 SILVER SOURCE VERIFICATION: PASS**. This record reconciles the supplied live observations with the repository; it does not claim an additional Fabric execution during this documentation update. The verification notebook is a deployed Fabric artifact, not a notebook added to this repository by this task.

| Fabric item | Verified name |
| --- | --- |
| Workspace | `WS_FieldOps_Dev` |
| Environment | `ENV_FieldOps_Dev` |
| Lakehouse | `LH_FieldOps` |
| SQL analytics endpoint | `LH_FieldOps` |
| Existing Warehouse | `WH_FieldOps` |

`WH_FieldOps` already exists. Phase 11.3 will verify/configure that Warehouse, not create another Warehouse. Its internal configuration was not established by this Silver inspection.

## Operational Silver source matrix

All twelve operational Delta sources were individually readable through Spark. All expected counts and column sets matched, with zero unexpected verification errors. The SQL endpoint independently exposed all twelve clean entities under `silver`; its final targeted object query returned exactly twelve rows.

| Entity | Spark-readable Delta path | Verified SQL endpoint object | Expected rows | Actual Spark rows |
| --- | --- | --- | ---: | ---: |
| regions | `Tables/silver/operations/regions` | `silver.regions` | 4 | 4 |
| offices | `Tables/silver/operations/offices` | `silver.offices` | 12 | 12 |
| employees | `Tables/silver/operations/employees` | `silver.employees` | 150 | 150 |
| projects | `Tables/silver/operations/projects` | `silver.projects` | 75 | 75 |
| job_sites | `Tables/silver/operations/job_sites` | `silver.job_sites` | 120 | 120 |
| crews | `Tables/silver/operations/crews` | `silver.crews` | 40 | 40 |
| activities | `Tables/silver/operations/activities` | `silver.activities` | 20 | 20 |
| equipment_types | `Tables/silver/operations/equipment_types` | `silver.equipment_types` | 10 | 10 |
| equipment | `Tables/silver/operations/equipment` | `silver.equipment` | 80 | 80 |
| safety_thresholds | `Tables/silver/operations/safety_thresholds` | `silver.safety_thresholds` | 40 | 40 |
| field_schedules | `Tables/silver/operations/field_schedules` | `silver.field_schedules` | 250 | 250 |
| equipment_assignments | `Tables/silver/operations/equipment_assignments` | `silver.equipment_assignments` | 120 | 120 |
| **Total** | **12 readable sources** | **12 exposed objects** | **921** | **921** |

The authoritative conclusion is that the clean sources are both Spark-readable at `Tables/silver/operations/<entity>` and SQL-visible as `silver.<entity>` in `LH_FieldOps`. Earlier uncertainty about clean SQL registration is resolved.

The column comparison uses the implemented source fields reconciled in [Silver contract/schema reconciliation](silver-contract-schema-reconciliation.md) and [operational data contracts](operational-data-contracts.md). Exact names such as `field_schedule_id`, `planned_crew_size`, `status`, `weather_location_code`, and `employment_status` remain unchanged.

The supplied live summary establishes column-set agreement, not deployed Spark/SQL data types, nullability, exact Spark registered names, absolute Delta URIs, or independent SQL data row counts. Those details are not invented here. The twelve rows returned by SQL object discovery are metadata rows, not the 921 operational data rows. Repository code preserves operational CSV fields as strings; that implementation expectation is not relabeled as a live type observation.

## Weather Silver

Registered source `dbo.silver_weather_forecast_hourly` was readable with **4,032 rows** and the expected column set. It was also visible in the SQL endpoint. Weather lineage was observable through `pipeline_run_id`; no specific run IDs or per-run counts were supplied.

Verified columns:

```text
pipeline_run_id, source_system, endpoint_name, location_id, location_name,
ingestion_timestamp_utc, forecast_timestamp_local, forecast_hour_index,
temperature_2m, apparent_temperature, relative_humidity_2m, precipitation,
weather_code, wind_gusts_10m, latitude, longitude, elevation, timezone,
timezone_abbreviation, utc_offset_seconds, temperature_unit,
apparent_temperature_unit, relative_humidity_unit, precipitation_unit,
weather_code_unit, wind_gust_unit, forecast_days, attempt_count, http_status_code
```

## Bronze monitoring and lineage limits

Registered source `dbo.monitoring_operational_ingestion_runs` was readable with **180 rows** and was SQL-visible.

Observed columns:

```text
run_id, ingestion_date, entity_name, source_path, destination_path,
row_count, checksum_sha256, status, error_type, error_message,
started_at, completed_at, duration_seconds
```

Bronze monitoring provides ingestion provenance evidence. It does **not** by itself prove which Bronze ingestion run produced the currently inspected Silver snapshot. No current operational Silver source-run association is asserted.

The SQL endpoint also exposed `dbo.monitoring_pipeline_runs`; its contents, row count, and lineage relationships were not established by the supplied observations.

## Validation-results persistence finding

The repository runtime default `Tables/validation/operational_results` was **not confirmed as an existing live output**:

- `Tables/validation` existed and contained only `schema.json.gz`.
- `Tables/validation/operational_results` did not exist.
- Spark `SHOW TABLES IN validation` returned zero tables.
- Spark `SHOW TABLES IN validation_negative` returned zero tables.

Persisted/registered operational findings were therefore unavailable at those checked locations. This is a Phase 11 source-readiness finding, not a failure of the clean Silver verification: all twelve operational sources, 921 rows, expected counts, and expected column sets passed.

The repository notebook writes validation findings only when results exist. That behavior does not establish why the observed paths/namespaces lack findings or establish a current successful-run ledger.

SQL independently exposed `dbo.validation_negative` as a **USER_TABLE**. This SQL object is distinct from the Spark namespace `validation_negative`. Its contents and relationship to historical validation outputs were not verified. Negative/quarantine artifacts were also SQL-visible, including objects under schemas such as `quarantine_negative`; no further current counts or contents are inferred.

[Phase 10 completion evidence](silver-completion-status.md) and the [negative acceptance plan](silver-negative-fabric-acceptance-plan.md) retain the historical successful acceptance results. Their historical validation-output observations are not a claim that those destinations remain available now.

## SQL endpoint and intermediate-path sync observation

SQL context was independently verified as `DB_NAME() = LH_FieldOps`. Metadata was exposed through `sys.schemas`, `sys.objects`, `sys.columns`, and `sys.types`.

On opening the endpoint, Fabric displayed a sync error for table name `silver.operations`:

```text
Delta table 'Tables\silver\operations\_delta_log' not found.
```

`Tables/silver/operations` is the container level; the actual Delta tables are below it at `Tables/silver/operations/<entity>`. Despite the intermediate-path sync warning, all twelve actual entities were exposed as `silver.<entity>`. This warning is not recorded as failure of those twelve sources. No live repair was attempted.

## Phase 11 sequence and design boundary

| Step | Scope | Status |
| --- | --- | --- |
| 11.1 | Discovery & Requirements Reconciliation | COMPLETE |
| 11.2 | Dimensional Design | NEXT |
| 11.3 | Warehouse Design / Verification / Configuration of existing `WH_FieldOps` | Planned |
| 11.4 | Silver-to-Warehouse Integration | Planned |
| 11.5 | dbt Gold Implementation | Planned |
| 11.6 | dbt Tests, Lineage & Documentation | Planned |
| 11.7 | Reconciliation & Deterministic Acceptance | Planned |

Candidate dimensions remain inputs to Phase 11.2, not final or implemented models:

- `dim_region`, `dim_office`, `dim_employee`, `dim_project`
- `dim_job_site`, `dim_crew`, `dim_activity`, `dim_equipment_type`
- `dim_equipment`, `dim_safety_threshold`, `dim_weather_location`, `dim_date`

Candidate facts remain `fact_field_schedule`, `fact_equipment_assignment`, and `fact_weather_forecast_hourly`.

Phase 11.2 will separately lock business processes, grains, surrogate/business/source keys, attributes, relationships, fact foreign keys, measures and additivity, SCD strategy, unknown-member strategy, date roles, weather grain/version semantics, and publication/reconciliation controls. Source discovery completion does not imply those decisions are final.

Architecture remains Sources → Bronze Lakehouse → Silver Lakehouse → Fabric Warehouse → dbt Gold analytics layer → Semantic Model → Power BI. Bronze and Silver remain Python/PySpark-based. No Warehouse DDL, dbt models, notebook changes, risk-engine implementation, or FSD-008 implementation is part of this documentation reconciliation.

## Phase 11.4 / 11.7 publication requirement

Preserve the post-quarantine referential-integrity risk identified in repository discovery. Silver relationship validation evaluates the incoming dataset before final disposition. In the negative acceptance example, quarantined Job Site `1` leaves these accepted child references:

| Child entity | Record IDs | Orphan relationships |
| --- | --- | ---: |
| Field schedules | `1`, `117`, `137`, `156`, `192`, `242` | 6 |
| Equipment assignments | `15`, `96` | 2 |
| **Total** | | **8** |

This is a known negative-case design risk, not an observed defect in the verified clean snapshot. Phase 11.4/11.7 publication controls must detect these eight orphan relationships, prevent publication of an invalid analytical candidate batch, and preserve the previously published good state. The control is required but not implemented by this task.

## Remaining limitations and next action

Current validation-finding persistence and operational snapshot-to-run attribution remain unresolved as described above. The intermediate-path sync warning is recorded without repair. Detailed deployed type/nullability evidence and Warehouse configuration are not supplied by this verification summary. None of these limitations changes the recorded Phase 11.1 completion status.

**Single next action: Phase 11.2 Dimensional Design**, using the verified sources and explicit limitations above. This is a design step, not dimensional implementation.
