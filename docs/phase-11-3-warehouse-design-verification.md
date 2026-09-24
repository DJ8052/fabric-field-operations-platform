# Phase 11.3 — Warehouse Design / Verification / Configuration

## 1. Status, purpose, and authority

**Status: READY FOR LIVE PROOF — physical design proposed for review; Phase 11.3 is not COMPLETE.** Documentation establishes platform capabilities, but the supplied live evidence does not prove permissions, persistent key recovery, source conversions, or the proposed multi-table promotion behavior in `WH_FieldOps`. No Fabric commands have been executed by this task. No schemas, tables, dbt models, or production DDL have been created. Approval is required before any proposed live proof or implementation.

Target only the existing **`WS_FieldOps_Dev` / `WH_FieldOps`**. Source Lakehouse remains **`LH_FieldOps`**. Preserve Sources → Bronze → Silver → Warehouse / dbt Gold → Semantic Model → Power BI. Python/PySpark continues to own Bronze/Silver; dbt owns Gold analytical transformations, not operational validation or ingestion.

The [Phase 11.2 logical design](phase-11-2-dimensional-design.md) remains authoritative and unchanged: eleven dimensions, three base facts, ten Type 1 entity dimensions, Type 0 dates, persistent integer entity keys, source identifiers retained, no core safety-threshold dimension, no parent-project surrogate, and no base-fact joins. This document resolves physical choices within that design. It does not reinterpret Type 1 as historical ownership or introduce actual work/utilization measures.

Repository review also covered [README](../README.md), [Phase 11.1 evidence](phase-11-1-silver-source-verification.md), [contracts](operational-data-contracts.md), [schema reconciliation](silver-contract-schema-reconciliation.md), [operational ERD](operational-domain-erd.md), [dashboard coverage](dashboard-coverage-matrix.md), [risk specification](risk-engine-specification.md), [risk validation](risk-validation-matrix.md), [synthetic plan](synthetic-data-generation-plan.md), [generator/configuration](../src/operational_data_generator/entities.py), [location configuration](../config/locations.yml), [weather client](../src/weather_ingestion/api_client.py), [weather transformation](../src/weather_transformation/transformer.py), and [weather writer](../src/weather_transformation/delta_writer.py).

`dbt/` contains no project/configuration/models. No `dbt_project.yml`, adapter pin, connection profile, production schema convention, or Warehouse deployment mechanism exists in the inspected repository. [pyproject.toml](../pyproject.toml) defines Python >=3.11 and pytest 9.x development dependencies, not dbt dependencies. Proposed schema names and mechanisms below are new design decisions, not discovered configuration.

Pre-task changes were exactly `M README.md` and `?? docs/phase-11-2-dimensional-design.md`. Both are preserved byte-for-byte; this phase adds only this document. README still reflects the last reviewed phase until this physical design/live-proof gate is resolved.

## 2. Supplied live Warehouse evidence — 2026-09-24

This is an owner-supplied verification record, not an independent execution or captured query transcript from this task.

| Evidence | Observation | What it establishes / does not establish |
| --- | --- | --- |
| `Phase11_3_WH_FieldOps_Inventory` | `DB_NAME()` = `WH_FieldOps`; `SESSION_USER` identified the executing Fabric user | Correct existing Warehouse context; does not establish an automation principal's permissions |
| Schema/object inventory | 15 schemas; Fabric/system objects including `queryinsights` and `sys`; no Field Operations dimensional tables | Existing system inventory; not 15 user-created application schemas |
| `Phase11_3_WH_FieldOps_Capability_Verification` | Version string `Microsoft Azure SQL Data Warehouse (RTM) - 12.0.2000.8`, build `Sep 16 2026 10:25:05` | Reported engine banner; not proof of generic SQL Server feature parity |
| Filtered user schema / identity / PK-UNIQUE inventories | 0 / 0 / 0 rows | No corresponding user objects were found; not evidence that those capabilities are unsupported |
| `Phase11_3_WH_FieldOps_DataType_Verification` | `bigint`, `bit`, `date`, `datetime2`, `decimal`, `int`, `numeric`, `nvarchar`, `varchar` exposed by `sys.types` | Catalog type visibility only; persisted Warehouse storage restrictions still apply |
| End state | No user-created Field Operations tables; no objects created during Steps 1–3 | Read-only verification boundary maintained |

Observed catalog examples: bigint length 8 / precision 19 / scale 0; bit length 1 / precision 1; date length 3 / precision 10; datetime2 length 8 / precision 27 / scale 7; decimal/numeric length 17 / precision 38 / scale 38; int length 4 / precision 10; nvarchar/varchar maximum length 8000. These are **not** target definitions. In particular, they do not authorize persisted NVARCHAR or DATETIME2(7).

Source evidence remains twelve SQL-visible `LH_FieldOps.silver.<entity>` objects and Spark paths `Tables/silver/operations/<entity>`, totaling 921 rows: 4 regions, 12 offices, 150 employees, 75 projects, 120 sites, 40 crews, 20 activities, 10 equipment types, 80 assets, 40 rules, 250 schedules, 120 assignments. Weather `LH_FieldOps.dbo.silver_weather_forecast_hourly` had 4,032 rows; Bronze monitoring `LH_FieldOps.dbo.monitoring_operational_ingestion_runs` had 180. No operational snapshot-to-Bronze-run association is proven. Missing current clean validation-results persistence remains a readiness finding; it is not a new failure of Silver verification.

## 3. Official platform evidence

All URLs below were retrieved **2026-09-24**. Statements apply to **Fabric Warehouse**, not Fabric SQL database or generic SQL Server. Documentation support is distinct from successful live use under the intended principal.

| ID | Official Microsoft URL | Verified capability / design implication |
| --- | --- | --- |
| M01 | [Warehouse identity](https://learn.microsoft.com/en-us/fabric/data-warehouse/identity) | BIGINT IDENTITY is supported. Distributed allocation produces positive unique generated values, with gaps and no ordering guarantee; custom seed/increment is unsupported. Adding identity to an existing column is not supported. Use native allocation only in a durable registry. |
| M02 | [IDENTITY_INSERT](https://learn.microsoft.com/en-us/sql/t-sql/statements/set-identity-insert-transact-sql?view=fabric) | Fabric-specific section permits explicit identity insertion, one enabled table per session, with an explicit column list. Negative sentinel insertion is supported (also illustrated by M01); explicit values require independent duplicate checks. |
| M03 | [DBCC CHECKIDENT](https://learn.microsoft.com/en-us/sql/t-sql/database-console-commands/dbcc-checkident-transact-sql?view=fabric) | Fabric reseeding scans distributed ranges; run after explicit identity insertion. Custom reseed values and SQL Server NORESEED semantics are not supported. Requires table ownership or ALTER permission; schedule without concurrent registry writes. |
| M04 | [Warehouse constraints](https://learn.microsoft.com/en-us/fabric/data-warehouse/table-constraints) | PK and UNIQUE require NONCLUSTERED NOT ENFORCED; FK requires NOT ENFORCED. Add through ALTER TABLE, not inline CREATE TABLE. Default constraints are unsupported. They do not enforce source quality or publication validity. |
| M05 | [Persisted data types](https://learn.microsoft.com/en-us/fabric/data-warehouse/data-types) | BIGINT, INT, BIT, DECIMAL, FLOAT, DATE, DATETIME2, VARCHAR and VARBINARY are available. DATETIME2 fractional precision is at most 6. Persisted NVARCHAR/NCHAR, DATETIMEOFFSET, DATETIME, TINYINT and native JSON are unsuitable/unsupported; choose documented alternatives. |
| M06 | [Warehouse tables and schemas](https://learn.microsoft.com/en-us/fabric/data-warehouse/tables) | Custom schemas are supported with CREATE SCHEMA. Computed columns, sequence objects, unique indexes, triggers and manually partitioned tables are not available. Use stored derived values and validation rather than these mechanisms. |
| M07 | [T-SQL surface area](https://learn.microsoft.com/en-us/fabric/data-warehouse/tsql-surface-area) | MERGE is generally available. ALTER TABLE has limitations; ALTER COLUMN is preview. No synonyms or recursive queries. This design avoids relying on preview schema alteration, synonyms, recursive calendar generation, or triggers. |
| M08 | [Warehouse transactions](https://learn.microsoft.com/en-us/fabric/data-warehouse/transactions) | Explicit multi-table commit/rollback and snapshot isolation are supported. Write conflicts can occur at table level. Changing isolation does not enable serializable semantics. No distributed transactions or savepoints. These support a proposed single-connection promotion, not an already verified publication control. |
| M09 | [Collation](https://learn.microsoft.com/en-us/fabric/data-warehouse/collation) | Default is Latin1_General_100_BIN2_UTF8; a case-insensitive UTF-8 option also exists. Existing item collation cannot be changed. Inspect this Warehouse and source endpoint rather than assuming defaults. |
| M10 | [Cross-database queries](https://learn.microsoft.com/en-us/fabric/data-warehouse/query-warehouse) | Same-workspace SQL uses three-part names and can read Lakehouse SQL endpoint tables for Warehouse loading. This does not prove a coherent multi-entity business snapshot of independently overwritten Silver tables. |
| M11 | [Microsoft dbt setup](https://learn.microsoft.com/en-us/fabric/data-warehouse/tutorial-setup-dbt) | Microsoft documents dbt-fabric, ODBC and Entra authentication. Adapter operations can use CTAS/drop/create. Inspect the selected version's compiled behavior; no tutorial profile, dbo schema, or thread count is adopted as repository configuration. |
| M12 | [Warehouse security](https://learn.microsoft.com/en-us/fabric/data-warehouse/security) | Fabric item/workspace access and granular SQL permissions both matter. Connectivity alone is insufficient evidence of write/DDL rights or restricted consumer access. |
| M13 | [CREATE SCHEMA reference](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-schema-transact-sql?view=sql-server-ver17) | Fabric-specific permission note requires CREATE SCHEMA plus Admin/Member/Contributor workspace membership. Deployment and restricted runtime responsibilities should be separated. |
| M14 | [Effective SQL permissions](https://learn.microsoft.com/en-us/sql/relational-databases/system-functions/sys-fn-my-permissions-transact-sql?view=sql-server-ver17) | The function reference includes Fabric Warehouse and supports querying the current principal's database permissions. Use it as SQL evidence alongside Fabric role/item evidence, not a replacement for those checks. |

M02/M03 URLs select the Fabric Warehouse view; their Microsoft reference pages also contain other platform sections. Only the Fabric section informs this design. No official evidence reviewed contradicts a locked Phase 11.2 logical decision. Storage type restrictions resolve previously open physical choices. If live evidence requires changing grain, identity, or relationship semantics, stop and reopen the logical design rather than changing it implicitly.

## 4. Proposed physical organization

| Schema in existing WH_FieldOps | Purpose / proposed objects | Lifetime / write owner |
| --- | --- | --- |
| `gold` | Eleven `dim_*` and three `fact_*` published tables with the exact logical names | Stable tables; only controlled publisher writes after approval |
| `stg` | `operations_<entity>` for all twelve accepted sources, `weather_forecast_hourly`, `weather_location_config` | Frozen, publication-tagged extraction/reference evidence; Phase 11.4 capture process writes |
| `candidate` | Eleven dimensions and three facts with the same base names; publication-tagged candidate rows | dbt Gold transformation outputs; inaccessible to normal consumers |
| `ctl` | `entity_key_registry`, `publication_manifest`, `publication_source`, `validation_outcome`, `publication_state`, `load_attempt` | Durable technical identity, evidence, state and audit; explicitly controlled writers |

`gold` identifies the published analytical contract; using dbo would obscure that boundary. `candidate` separates unapproved Type 1 changes from published data. `ctl` prevents key mappings from being disposable dbt model outputs. `stg` is Warehouse landing evidence, not a new Silver layer or a relocation of Silver validation. No application schemas currently exist by supplied inventory; all four names are proposals.

Retain safety rules in frozen `stg.operations_safety_thresholds` with their source fields and manifest association; no `gold.dim_safety_threshold` or risk fact. Rule parsing/representation checks may be analytical validation; applicability/scoring remain outside this phase. The Phase 11.4 layout must preserve exact original values, not truncate fields to Gold widths before profiling. Bounded VARCHARs below apply to analytical targets; landing storage lengths must be profiled separately, with references to original accepted artifacts when necessary.

All fifteen governed rule fields remain available: `threshold_id`, `activity_id`, `equipment_type_id`, `metric_code`, `comparison_operator`, `unit`, `threshold_value_or_code_set`, `threshold_value`, `weather_code_set`, `severity`, `recommended_action_code`, `effective_start_date`, `effective_end_date`, `is_active`, `override_flag`. Preserve original payloads and empty/null distinctions in extraction evidence. Validate required activity and populated optional equipment-type references against accepted parents. The selected rule set is linked by `_publication_id`; its effective dates and flags are rule input, not Type 2 history or a new fact measure.

Do not introduce Synapse distribution clauses, user-defined partitioning, clustered/unique indexes, or a second Warehouse. Keep normal tables and explicit columns. No physical ERD is duplicated: Phase 11.2's ERD remains valid with a `gold.` prefix and the unchanged FK names below. Technical manifest/registry relationships are audit links, not new business dimensions or fact-grain components.

## 5. Data types, sizes, identity comparisons, and table notation

An in-memory profile of the repository's deterministic clean generator found actual primary/FK ID text up to 3 bytes, scenario identifiers up to 25, names up to 23, descriptions/notes up to 44, code/number/status group up to 18, and timestamp text 19 (whole seconds). These are fixture observations, **not contractual maxima or live Silver profiles**. Three configured location codes have 6 characters. Contracts generally provide no maximum string length.

| Choice | Basis and explicit sizing assumption |
| --- | --- |
| Source IDs and run identifiers: VARCHAR(128) | Preserve text identity and allow future opaque identifiers. 128 UTF-8 bytes is a reviewed sizing assumption, not a source limit; no integer coercion. |
| Business codes/numbers and scenarios: VARCHAR(64) | Room beyond deterministic codes/scenarios; assumption, not an approved new business domain. Weather location codes use VARCHAR(32). |
| Names: VARCHAR(256); descriptions/notes: VARCHAR(1024) | Fixture maxima 23/44 bytes plus deliberate headroom for human descriptions. Both require live profiling and overflow rejection. |
| Status/units: VARCHAR(32); roles/categories/actions: VARCHAR(64) | Existing values fit; broader status domains remain unresolved. These widths must not be mistaken for allowed-value registries. |
| Timezone: VARCHAR(128); abbreviation: VARCHAR(32) | IANA zone/name storage allowance; abbreviation remains version metadata. |
| Planned hours: DECIMAL(19,6) | Decimal arithmetic aligns with Silver's 0.000001 equality tolerance; 13 integer digits is ample for fixture workload. Reject source values that overflow or lose nonzero precision. |
| Derived bounded hours: DECIMAL(28,12) | Allows microsecond timestamp subtraction and a documented 12-decimal hours result. Compute using wide decimal arithmetic; round only this derived division to 12 places (absolute rounding error <=0.0000000000005 hour), not source timestamps or supplied measures. |
| Forecast readings/coordinates: FLOAT(53); codes/humidity/counts: INT | Transformer uses optional Python floats for continuous values and integers for humidity/code/index. Confirm deployed types and numeric round trips; no invented unit conversion or decimal precision claim. |
| Timestamps: DATETIME2(6) | Maximum documented persisted fractional precision. Preserve naive operational/local weather values; normalize only already-UTC ingestion values before dropping their UTC offset representation. If meaningful source precision exceeds 6 or operational offsets appear, stop for explicit policy; no silent truncation/timezone conversion. |
| Dates: DATE; calendar keys: INT; flags: BIT | Date key can encode real supported dates as YYYYMMDD; -1/-2 are outside that domain. Flags are explicitly parsed, not truthiness of nonempty text. |

Use UTF-8 string storage; VARCHAR(n) limits **bytes**, not characters. Live profiling must use byte lengths and conversion round trips, including non-ASCII examples. Do not use VARCHAR(8000), NVARCHAR or DATETIME2(7) merely because sys.types exposed them. Do not assume a UUID source/run identifier: strings avoid an unnecessary UNIQUEIDENTIFIER cross-endpoint representation dependency.

Keep case and whitespace exactly. For identity resolution/uniqueness, require case-sensitive UTF-8 comparison **and equal byte lengths**, or equivalent verified byte-exact comparison. Binary collation alone must not be assumed to preserve trailing-space distinctions under SQL equality. Registry and source lookups use the same predicate. Metadata UNIQUE declarations on text identities are withheld until these semantics are proven; integer SK comparisons are straightforward. This is an implementation requirement of the existing no-normalization policy, not a new source restriction.

### Column specification conventions

Each column below has its complete persisted type, including chosen variable length/precision. `N` means physically NOT NULL. `R` means physically NULL allowed **only for reserved dimension rows**; a real member requires a nonmissing source value. `O` means nullable on real rows. `W` means nullable on real rows under existing Silver warning policy. All R/O/W columns are physically nullable; application gates enforce real-member contracts. This permits two reserved rows with NULL source/business identifiers without weakening publication checks.

Key-role notation: `SK` surrogate key, `BK` business key, `SID` source identifier, `SF` retained source relationship identifier, `FK <table>` resolved integer relationship, `G` fact-grain component, `DD` degenerate identifier. Columns not marked as keys are descriptive, measure or audit values as stated. Source column names are identical unless a derivation is shown. Real-member missing values mean NULL/exact empty string, never trimmed whitespace.

All ten entity-dimension descriptive and relationship columns use **Type 1 overwrite**; their SK/SID/BK mappings are immutable and conflicts block. All `dim_date` calendar attributes are **Type 0**. Facts follow their snapshot/version semantics, not SCD. Thus SCD behavior applies to every listed column without repeating it in each row.

**Common physical column, included once in every one of the fourteen gold tables and their candidate counterparts:**

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `_publication_id` | VARCHAR(64) | N | Technical candidate manifest ID generated outside the business sources; in gold denotes the coherent publication containing this row. Audit reference to ctl.publication_manifest; not a business grain component or forecast run ID. |

Candidate tables may retain multiple complete versions: physical uniqueness there is `_publication_id` plus the corresponding Gold key/grain. Gold contains exactly one operational snapshot, a retained weather-version set, and one coherent publication identifier across all fourteen tables, including reserved rows. Reusing a candidate ID requires identical frozen inputs/code; changed inputs require a new ID. Retained weather rows receive the current publication tag without altering their source run/ingestion provenance. Source manifests for earlier publications are retained.

## 6. Physical dimension specifications

### gold.dim_region — silver.regions; one region; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `region_key` | BIGINT | N | Registry mapping; SK |
| `region_id` | VARCHAR(128) | R | Source region identity; SID |
| `region_code` | VARCHAR(64) | R | Immutable region business code; BK |
| `region_name` | VARCHAR(256) | W | Current region label |
| `region_description` | VARCHAR(1024) | O | Region description |

### gold.dim_office — silver.offices; one office; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `office_key` | BIGINT | N | Registry mapping; SK |
| `office_id` | VARCHAR(128) | R | Source office identity; SID |
| `office_code` | VARCHAR(64) | R | Immutable office business code; BK |
| `office_name` | VARCHAR(256) | W | Current office label |
| `region_id` | VARCHAR(128) | R | Source owning region; SF |
| `office_description` | VARCHAR(1024) | O | Office description |
| `region_key` | BIGINT | N | Accepted region_id lookup; FK dim_region |

### gold.dim_employee — silver.employees; one employee; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `employee_key` | BIGINT | N | Registry mapping; SK |
| `employee_id` | VARCHAR(128) | R | Source employee identity; SID |
| `employee_number` | VARCHAR(64) | R | Immutable employee number; BK |
| `employee_name` | VARCHAR(256) | R | Current employee name |
| `home_office_id` | VARCHAR(128) | R | Source home office; SF |
| `employment_status` | VARCHAR(32) | R | Current source status; no expanded domain invented |
| `termination_date` | DATE | O | Optional source termination date |
| `employee_role_code` | VARCHAR(64) | O | Source role label; not an eligibility rule |
| `home_office_key` | BIGINT | N | Accepted home_office_id lookup; FK dim_office |

### gold.dim_project — silver.projects; one project; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `project_key` | BIGINT | N | Registry mapping; SK |
| `project_id` | VARCHAR(128) | R | Source project identity; SID |
| `project_code` | VARCHAR(64) | R | Immutable project code; BK |
| `project_name` | VARCHAR(256) | W | Current project name |
| `office_id` | VARCHAR(128) | R | Accountable office; SF |
| `project_manager_employee_id` | VARCHAR(128) | R | Source project manager; SF |
| `field_manager_employee_id` | VARCHAR(128) | R | Source field manager; SF |
| `status` | VARCHAR(32) | R | Source project status |
| `project_start_date` | DATE | O | Project start attribute, not a schedule role |
| `project_end_date` | DATE | O | Project end attribute |
| `priority_code` | VARCHAR(64) | O | Source priority label |
| `project_description` | VARCHAR(1024) | O | Project description |
| `parent_project_code` | VARCHAR(64) | O | Source parent label only; not an FK |
| `office_key` | BIGINT | N | Accepted office_id lookup; FK dim_office |
| `project_manager_employee_key` | BIGINT | N | Accepted project_manager_employee_id lookup; FK dim_employee |
| `field_manager_employee_key` | BIGINT | N | Accepted field_manager_employee_id lookup; FK dim_employee |

### gold.dim_job_site — silver.job_sites; one site; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `job_site_key` | BIGINT | N | Registry mapping; SK |
| `job_site_id` | VARCHAR(128) | R | Source site identity; SID |
| `job_site_code` | VARCHAR(64) | R | Immutable site code; BK |
| `job_site_name` | VARCHAR(256) | R | Source site name |
| `project_id` | VARCHAR(128) | R | Source owning project; SF |
| `weather_location_code` | VARCHAR(32) | R | Configured forecast area code |
| `job_site_description` | VARCHAR(1024) | O | Site description |
| `project_key` | BIGINT | N | Accepted project_id lookup; FK dim_project |
| `weather_location_key` | BIGINT | N | Exact configured code lookup; FK dim_weather_location |

### gold.dim_crew — silver.crews; one crew; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `crew_key` | BIGINT | N | Registry mapping; SK |
| `crew_id` | VARCHAR(128) | R | Source crew identity; SID |
| `crew_code` | VARCHAR(64) | R | Immutable crew code; BK |
| `home_office_id` | VARCHAR(128) | R | Source home office; SF |
| `crew_lead_employee_id` | VARCHAR(128) | O | Optional source crew lead; SF |
| `crew_status` | VARCHAR(32) | R | Source status |
| `crew_description` | VARCHAR(1024) | O | Crew description; no invented crew name/size |
| `home_office_key` | BIGINT | N | Accepted home_office_id lookup; FK dim_office |
| `crew_lead_employee_key` | BIGINT | N | Accepted employee lookup or -1 for absent lead; FK dim_employee |

### gold.dim_activity — silver.activities; one activity; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `activity_key` | BIGINT | N | Registry mapping; SK |
| `activity_id` | VARCHAR(128) | R | Source activity identity; SID |
| `activity_code` | VARCHAR(64) | R | Immutable activity code; BK |
| `activity_name` | VARCHAR(256) | W | Activity label |
| `activity_description` | VARCHAR(1024) | O | Activity description |
| `activity_category` | VARCHAR(64) | O | Source category |

### gold.dim_equipment_type — silver.equipment_types; one type; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `equipment_type_key` | BIGINT | N | Registry mapping; SK |
| `equipment_type_id` | VARCHAR(128) | R | Source type identity; SID |
| `equipment_type_code` | VARCHAR(64) | R | Immutable type code; BK |
| `equipment_type_name` | VARCHAR(256) | W | Type label |
| `equipment_type_description` | VARCHAR(1024) | O | Type description |
| `equipment_category` | VARCHAR(64) | O | Source category |

### gold.dim_equipment — silver.equipment; one asset; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `equipment_key` | BIGINT | N | Registry mapping; SK |
| `equipment_id` | VARCHAR(128) | R | Source asset identity; SID |
| `equipment_code` | VARCHAR(64) | R | Immutable asset code; BK |
| `equipment_type_id` | VARCHAR(128) | R | Source asset classification; SF |
| `equipment_status` | VARCHAR(32) | W | Warning-eligible source status |
| `serial_number` | VARCHAR(128) | O | Source serial; not an alternate identity assumption |
| `asset_tag` | VARCHAR(128) | O | Source asset tag |
| `equipment_description` | VARCHAR(1024) | O | Asset description |
| `equipment_type_key` | BIGINT | N | Accepted equipment_type_id lookup; FK dim_equipment_type |

### gold.dim_weather_location — versioned locations.yml; one configured identity; Type 1

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `weather_location_key` | BIGINT | N | Registry mapping; SK |
| `location_id` | VARCHAR(32) | R | Config location_id; SID and BK |
| `location_name` | VARCHAR(256) | R | Config location_name; current requested-area label |
| `requested_latitude` | FLOAT(53) | R | Config latitude, not weather response/site coordinate |
| `requested_longitude` | FLOAT(53) | R | Config longitude |
| `requested_timezone` | VARCHAR(128) | R | Config timezone |
| `is_configured_active` | BIT | R | Config active flag; false does not remove referenced history |

Exact identity map: TX-DAL → Dallas, TX-HOU → Houston, TX-AUS → Austin. Populate from captured configuration revision; validate all site/weather IDs against it. Retain prior configured members/evidence if required by retained weather versions. Missing forecast coverage is not missing location identity. No guessed geography/name matching.

### gold.dim_date — generated calendar; one date; Type 0

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `date_key` | INT | N | Year*10000 + month*100 + day, or -1/-2; deterministic PK |
| `calendar_date` | DATE | R | Real calendar date; BK |
| `calendar_year` | INT | R | Calendar year |
| `calendar_quarter` | INT | R | Quarter 1–4 |
| `calendar_month` | INT | R | Month 1–12 |
| `day_of_month` | INT | R | Day 1–31 |
| `iso_weekday` | INT | R | Monday=1 through Sunday=7; independent of session DATEFIRST |
| `iso_week` | INT | R | ISO week number |
| `iso_week_year` | INT | R | ISO week-year, including year-boundary differences |
| `is_weekend` | BIT | R | True for ISO weekdays 6 and 7; no holiday/fiscal inference |

Generation uses deterministic nonrecursive calendar logic in the future Gold implementation. Cover full calendar years from minimum through maximum referenced dates, including optional project/termination/rule dates, retained forecast targets and UTC ingestion dates. Union with existing coverage; never shrink, regenerate based on today, or change prior calendar values. No separate scheduled-start key, time-of-day dimension, or project date FK is introduced. New dates are staged and promoted with the complete candidate.

## 7. Physical fact specifications

Each also includes the common `_publication_id` column. All source IDs remain text. Each target integer FK references the same-named parent key in `gold`; candidate lookups additionally require equal publication IDs. No extra fact-row identity is proposed.

### gold.fact_field_schedule — silver.field_schedules

Unique grain: `field_schedule_id` in the selected accepted operational snapshot; source fields retained in full.

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `field_schedule_id` | VARCHAR(128) | N | Source occurrence; G, DD |
| `project_id` | VARCHAR(128) | N | Source owning project; SF |
| `job_site_id` | VARCHAR(128) | N | Source site; SF |
| `crew_id` | VARCHAR(128) | N | Source crew; SF |
| `activity_id` | VARCHAR(128) | N | Source activity; SF |
| `scheduled_start_timestamp` | DATETIME2(6) | N | Source local/unspecified-zone start |
| `scheduled_end_timestamp` | DATETIME2(6) | N | Source local/unspecified-zone end |
| `scheduled_date` | DATE | N | Source scheduled date; must equal start calendar date |
| `planned_crew_hours` | DECIMAL(19,6) | N | Supplied additive planned crew-hours; warning mismatch does not authorize replacement |
| `planned_crew_size` | INT | N | Supplied planned persons; non-additive headcount |
| `planned_labor_hours` | DECIMAL(19,6) | N | Supplied additive planned person-hours; reconcile multiplication within 0.000001 |
| `status` | VARCHAR(32) | N | Source schedule status; no actual-work inference |
| `rescheduled_from_schedule_id` | VARCHAR(128) | O | Source predecessor DD; NULL = root; conditional accepted-source relationship |
| `scenario_id` | VARCHAR(64) | O | Synthetic fixture DD; not a risk result/join key |
| `project_key` | BIGINT | N | Accepted project_id lookup; FK dim_project |
| `job_site_key` | BIGINT | N | Accepted job_site_id lookup; FK dim_job_site |
| `crew_key` | BIGINT | N | Accepted crew_id lookup; FK dim_crew |
| `activity_key` | BIGINT | N | Accepted activity_id lookup; FK dim_activity |
| `scheduled_date_key` | INT | N | scheduled_date as YYYYMMDD; FK dim_date, default start role |
| `scheduled_end_date_key` | INT | N | End calendar date as YYYYMMDD; FK dim_date |
| `schedule_occurrence_count` | INT | N | Gold constant 1, explicitly supplied; additive per occurrence |

No nullable required relationship may map to -1. Predecessor verification is not an analytical fact self-join or expansion. Roots and successors both remain occurrences; semantic status filters are explicit. Project dates and personnel/office descriptions remain dimensional.

### gold.fact_equipment_assignment — silver.equipment_assignments

Unique grain: `assignment_id` in the same selected operational snapshot.

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `assignment_id` | VARCHAR(128) | N | Source assignment occurrence; G, DD |
| `equipment_id` | VARCHAR(128) | N | Source assigned asset; SF |
| `job_site_id` | VARCHAR(128) | N | Source site; SF |
| `project_id` | VARCHAR(128) | N | Source project; SF |
| `assignment_start_timestamp` | DATETIME2(6) | N | Source interval start |
| `assignment_end_timestamp` | DATETIME2(6) | O | Source end; NULL remains open/unknown |
| `assignment_note` | VARCHAR(1024) | O | Source interval note |
| `scenario_id` | VARCHAR(64) | O | Synthetic fixture DD |
| `equipment_key` | BIGINT | N | Accepted equipment_id lookup; FK dim_equipment |
| `job_site_key` | BIGINT | N | Accepted job_site_id lookup; FK dim_job_site |
| `project_key` | BIGINT | N | Accepted project_id lookup; FK dim_project |
| `assignment_start_date_key` | INT | N | Start calendar date; FK dim_date |
| `assignment_end_date_key` | INT | N | End calendar date or -1 for open end; FK dim_date |
| `assignment_occurrence_count` | INT | N | Gold constant 1; additive assignment count |
| `bounded_assignment_hours` | DECIMAL(28,12) | O | Valid comparable end-start in hours; NULL for open end; additive bounded source wall-clock duration, not utilization |

No use of load time as a substitute end, no zero for unknown duration, and no day/hour expansion. Reject malformed/nonpositive bounded intervals. Source timestamps stay precise; only the new duration division has the explicit numeric representation rule from section 5.

### gold.fact_weather_forecast_hourly — dbo.silver_weather_forecast_hourly

Unique grain: (`pipeline_run_id`, `location_id`, `forecast_timestamp_local`). Preserve distinct runs; no latest-row collapse. Same-key source corrections are reconciled with captured evidence; prior runs are retained unless an explicit future retention decision authorizes removal.

| Column | SQL type | Null | Source / meaning / key role |
| --- | --- | --- | --- |
| `pipeline_run_id` | VARCHAR(128) | N | Source run; G, DD, not sortable issue-time policy |
| `source_system` | VARCHAR(64) | N | Source provenance |
| `endpoint_name` | VARCHAR(64) | N | Source request endpoint |
| `location_id` | VARCHAR(32) | N | Configured source location; G, SF |
| `location_name` | VARCHAR(256) | N | Run-recorded source label, not overwritten from current configuration |
| `ingestion_timestamp_utc` | DATETIME2(6) | N | Source UTC ingestion instant; not forecast issue time |
| `forecast_timestamp_local` | DATETIME2(6) | N | Source local hourly target; G |
| `forecast_hour_index` | INT | N | Source array position; not established lead time |
| `temperature_2m` | FLOAT(53) | O | Nullable source temperature; non-additive |
| `apparent_temperature` | FLOAT(53) | O | Nullable apparent temperature; non-additive, not assumed heat index |
| `relative_humidity_2m` | INT | O | Nullable source humidity; non-additive |
| `precipitation` | FLOAT(53) | O | Nullable source hourly value; totals remain conditional on interval/unit policy |
| `weather_code` | INT | O | Nullable categorical source weather code; non-additive |
| `wind_gusts_10m` | FLOAT(53) | O | Nullable gust reading; non-additive |
| `latitude` | FLOAT(53) | O | Source response latitude; not requested/site latitude |
| `longitude` | FLOAT(53) | O | Source response longitude |
| `elevation` | FLOAT(53) | O | Optional source response elevation |
| `timezone` | VARCHAR(128) | N | Source response timezone |
| `timezone_abbreviation` | VARCHAR(32) | O | Optional run-recorded timezone label |
| `utc_offset_seconds` | INT | N | Source response offset metadata; not a universal operational conversion rule |
| `temperature_unit` | VARCHAR(32) | N | Source temperature unit |
| `apparent_temperature_unit` | VARCHAR(32) | N | Source apparent-temperature unit |
| `relative_humidity_unit` | VARCHAR(32) | N | Source humidity unit |
| `precipitation_unit` | VARCHAR(32) | N | Source precipitation unit |
| `weather_code_unit` | VARCHAR(32) | N | Source code unit |
| `wind_gust_unit` | VARCHAR(32) | N | Source gust unit |
| `forecast_days` | INT | N | Source request horizon; repeated metadata, not additive |
| `attempt_count` | INT | N | Source attempts; repeated hourly, not request-count measure |
| `http_status_code` | INT | N | Source HTTP result; not additive |
| `weather_location_key` | BIGINT | N | Exact location_id/config lookup; FK dim_weather_location |
| `forecast_date_key` | INT | N | Local target calendar date; FK dim_date |
| `ingestion_date_key` | INT | N | UTC ingestion calendar date; FK dim_date |

Source transformer optional conversions justify O flags; runtime proof must check actual NULLs/types and UTC serialization. Required source strings must not become literal 'None' placeholders through upstream conversion. Missing measurements remain NULL. Do not silently resolve duplicate local hours by appending forecast_hour_index to the grain.

## 8. Persistent surrogate-key mechanism

**Recommendation: one durable `ctl.entity_key_registry` with native BIGINT IDENTITY allocation; gold/candidate entity SKs are ordinary BIGINT columns populated from it, not IDENTITY columns.** Keys are globally unique positive integers in the registry but used in dimension-specific roles. The namespace plus immutable business identifier defines identity; source ID is an independently checked correspondence. There is no hash dimension key.

This retains Phase 11.2's native-allocation recommendation while separating allocation lifetime from disposable dbt candidate tables. Identity directly on each dimension is possible, but ordinary identity behavior alone cannot preserve mappings across drop/recreate, absent members, or recovery. Making every dimension both allocator and rebuildable output creates competing lifetimes; a separate registry is required by the selected approach.

### Registry columns (technical design, not a created object)

| Column | SQL type | Null | Meaning / role |
| --- | --- | --- | --- |
| `entity_key` | BIGINT IDENTITY | N | Durable allocated positive SK; proposed metadata PK |
| `entity_name` | VARCHAR(64) | N | Controlled namespace: exact entity dimension name, excluding dim_date |
| `business_key` | VARCHAR(128) | N | Lossless business identifier; weather uses location_id |
| `source_id` | VARCHAR(128) | N | Corresponding immutable source ID; weather uses location_id |
| `first_candidate_id` | VARCHAR(64) | N | Candidate that first caused allocation; audit manifest reference, not publication claim |
| `allocated_at_utc` | DATETIME2(6) | N | Explicit allocation audit time |

Natural/source uniqueness is per entity with byte-exact comparison from section 5. The registry includes no mutable labels or status. No reserved -1/-2 rows are needed there; those belong to each dimensional output. Allocate only after candidate real-member identity/null/type checks. Registry mappings may be retained for failed candidates; they never establish source readiness or make an absent parent valid.

| Lifecycle | Required behavior |
| --- | --- |
| Existing business entity | Match exact namespace/business key, verify exact source_id pairing, reuse entity_key. Resolve source FKs through accepted candidate parent source IDs, not directly through historical registry existence. |
| New entity | Under the sole authorized registry writer, insert distinct validated unmapped identities while omitting entity_key. Requery by exact identity to obtain assigned keys; never assume allocation order, contiguous values, MAX(key), or one scalar identity for a batch. |
| Type 1 change | Update candidate descriptive/relationship attributes with the same key. Registry identity remains unchanged. |
| Absent entity | Retain registry mapping indefinitely. Current operational dimensions omit absent real members; accepted children referring to them fail. Weather history may require retained configured locations. |
| Identity conflict | If either source ID or business key is paired differently from the durable mapping, block candidate and require reviewed identity resolution. Do not mutate the mapping to make a load pass. |
| Failed candidate | Keep published data unchanged. Committed allocations may remain; retries reuse them. Rolled-back allocations may leave gaps; never reclaim gaps or rely on their sequence. |
| dbt incremental build | Read immutable registry mappings; a separate controlled allocation step precedes candidate key lookups. Incremental maintenance does not own allocation implicitly. |
| dbt full refresh | Registry is excluded from all model rebuilds. Recreate only isolated candidate outputs with explicit integer keys; published tables stay available until approved promotion. Prevent arbitrary dbt drop/recreate of gold/ctl through permissions and deployment policy. |
| Recovery/rebuild | Restore a consistent registry checkpoint containing all published key mappings and retained allocations, then rebuild candidates using those exact integers. If registry evidence is missing/inconsistent, stop; do not reconstruct keys by rerunning identity. |
| Explicit registry restore | Controlled explicit key insertion uses IDENTITY_INSERT, OFF, then DBCC CHECKIDENT RESEED before allocation resumes. Check identity/business/source uniqueness independently, compare restored mappings to manifest evidence, and prove next allocation cannot collide. |

Concurrency is a required **single-writer orchestration contract**, not a claim that NOT ENFORCED UNIQUE or snapshot isolation serializes insert-if-missing. Registry allocation and publication use restricted credentials and nonoverlapping writer runs; all other sessions lack mutation access. Persistent audit state is not itself a mutex. Live proof must demonstrate the selected orchestration/credential boundary before concurrent deployment. On a transient failure, restart the complete allocation transaction and requery mappings; do not replay partially successful insert statements blindly.

## 9. Sentinel-member design

Gold/candidate SK columns are nonidentity BIGINT (date key INT), so explicitly supplying -1 and -2 requires **no IDENTITY_INSERT and no reseed** during routine dimension builds. Each dimension contains exactly two reserved rows per candidate/publication. -1 means Unknown; -2 means Not applicable, reserved for approved use. Seed source/business IDs as NULL, display labels as Unknown/Not applicable where appropriate, other unsupported business values as NULL, and dimension parent keys as the matching reserved parent key.

The official identity mechanism also supports negative sentinel insertion if identity-bearing dimensions were chosen: explicit inserts with IDENTITY_INSERT enabled for one table/session, then disable it and reseed as M02/M03 require. That alternative was evaluated but is **not** this routine load path. Explicit insertion remains relevant to registry disaster recovery. Reseeding does not remove duplicate rows or enforce business identity.

No real required FK uses -1/-2 as a repair. Absent optional crew lead uses -1; open assignment end date uses -1 with NULL timestamp/duration. Missing warning-only attributes retain the real member key. NULL/exact empty optional source text can become analytical NULL only with original extraction evidence retained. All constants/audit values are supplied explicitly; no DEFAULT constraint is assumed.

## 10. Constraints, dbt tests, and blocking validation

Three separate responsibilities:

1. **Warehouse metadata:** after proof/validation, propose PK NONCLUSTERED NOT ENFORCED on every Gold integer dimension key, the registry entity_key, and technical manifest/state keys. Propose FK NOT ENFORCED on the fourteen Gold tables' integer relationships listed in Phase 11.2. Use ALTER TABLE separately from table creation. These are optimizer/documentation assertions, never integrity enforcement.
2. **dbt tests:** unique/nonmissing grain, accepted-value/null rules, relationship resolution, registry consistency, arithmetic reconciliation, date coverage and source mappings on candidate data. `unique_key` configuration is not an allocating or enforcing constraint. Tests fail the build but do not by themselves create a cross-model transaction.
3. **Publication gate:** require durable success of all mandatory candidate checks tied to frozen inputs and transformation version. Any failure blocks the entire candidate regardless of metadata declarations or upstream success.

| Key/relationship | Proposed declaration / gate |
| --- | --- |
| Dimension SK / registry entity_key | Metadata PK as above plus independent unique/NOT NULL tests |
| Dimension source ID and business key | **No blanket UNIQUE metadata on nullable dimension identities**: two sentinel NULL rows exist. Test exact nonmissing uniqueness and one-to-one mapping only for real members; enforce immutable identity in registry. |
| Registry namespace + business key / source ID | Exact-match uniqueness tests and serialized writer. Defer optional UNIQUE metadata until SQL equality and trailing-space behavior match the contract; no unique-index workaround. |
| Schedule / assignment source grain | Unique nonempty text ID in gold; uniqueness per publication in candidate. Defer optional text PK/UNIQUE declarations pending exact-match proof. A single numeric fact surrogate is not introduced to mask duplicates. |
| Weather composite grain | Unique full three-part key in gold; candidate includes publication_id for storage only. Defer optional composite UNIQUE metadata pending identifier-comparison proof. |
| Integer dimension FKs | Metadata FK where declared, plus exact-one parent and nonreserved eligibility gate |
| All 19 operational source relationships | Revalidate accepted candidate source IDs before surrogate assignment; nullable references checked only when populated. Includes schedule predecessor and both safety-rule scope relationships outside core facts. |
| Supplemental relationships | Weather code/config, all date roles, publication manifest, and source-ID/business-key registry consistency checked explicitly |

No filtered unique index, enforced PK/FK, CHECK/trigger-based validation, or source-key self-FK is relied upon. Candidate tables carry no optimizer relationship assertions until data passes. Check source-key duplicates before lookups to prevent join expansion. Gold metadata remains valid across publication boundaries through a complete transaction; external writers must not bypass it.

## 11. Type 1 and fact load strategy

**Prefer staged UPDATE/INSERT with explicit typed columns and separate reconciliation over MERGE for the initial physical implementation.** Native MERGE is supported (M07); it is not rejected as unavailable. Its source cardinality still must be unique, and it can encounter snapshot write conflicts (M08). At this scale, separate steps make mapping conflicts, changes, inserts and absence dispositions easier to audit. No lock hint or serializable isolation assumption is used.

Build the complete candidate first: allocate/reuse registry keys, create region/activity/type/location/date members, then office, employee, project/crew/equipment, site, and facts in dependency order. Reserved parents precede reserved child relationships. Existing real-member keys stay stable while all current attributes, including office/employee-role keys, come from the accepted snapshot. Capture source changes through full comparison/rebuild; no incremental watermark exists in current operational sources and none is invented.

After validation, the preferred small-baseline promotion updates existing published dimension attributes, inserts new members, removes absent operational members only as part of the coherent model replacement, replaces both operational fact snapshots, reconciles weather inserts/corrections while retaining previous run keys, and extends the date table. Stage deletions and child/parent operations in dependency order. All actions and publication-state changes share one transaction. Full candidate replacement is also a recovery path using the same explicit keys; it is not a new key-allocation event.

Ten Type 1 entity dimensions contain current attributes; there are no valid_from/valid_to/current-row fields. `_publication_id` is audit state, not an SCD version. Dates remain Type 0. Role-playing employees use one physical dimension; both manager keys stay inside project and crew lead stays inside crew. Project hierarchy remains a nullable code attribute.

## 12. Technical support objects and publication design

The following are proposed minimum durable control structures, not created tables. `N`/`O` denote nonnullable/nullable; all identifiers are explicit values supplied by orchestration, not invented Silver fields.

| Object / grain | Proposed fields with types and nullability | Purpose |
| --- | --- | --- |
| `ctl.publication_manifest` / one candidate | `publication_id VARCHAR(64) N`; `status VARCHAR(32) N`; `created_at_utc DATETIME2(6) N`; `validated_at_utc DATETIME2(6) O`; `published_at_utc DATETIME2(6) O`; `previous_publication_id VARCHAR(64) O`; `transform_version VARCHAR(128) N`; `key_policy_version VARCHAR(32) N`; `config_revision VARCHAR(128) N`; `input_fingerprint VARCHAR(64) N` | Frozen candidate identity and lifecycle; fingerprint is audit checksum, not a dimension SK |
| `ctl.publication_source` / candidate + source name | `publication_id VARCHAR(64) N`; `source_name VARCHAR(256) N`; `source_version VARCHAR(256) O`; `snapshot_reference VARCHAR(1024) N`; `row_count BIGINT N`; `content_checksum VARCHAR(64) N`; `schema_checksum VARCHAR(64) N`; `captured_at_utc DATETIME2(6) N`; `source_run_id VARCHAR(128) O`; `lineage_status VARCHAR(32) N` | Captured data/config evidence and honest unknown run attribution; a candidate may have many weather runs retained in its captured rows |
| `ctl.validation_outcome` / candidate + check + record token | `publication_id VARCHAR(64) N`; `check_code VARCHAR(64) N`; `entity_name VARCHAR(64) N`; `record_token VARCHAR(512) N`; `severity VARCHAR(16) N`; `outcome VARCHAR(16) N`; `affected_count BIGINT N`; `expected_value VARCHAR(256) O`; `actual_value VARCHAR(256) O`; `message VARCHAR(2048) O`; `checked_at_utc DATETIME2(6) N` | Durable pass/fail summary and row-level failures; record token uses explicit scalar/composite encoding or a summary token, no ambiguous concatenation |
| `ctl.publication_state` / exactly one named model | `model_name VARCHAR(64) N`; `current_publication_id VARCHAR(64) O`; `published_at_utc DATETIME2(6) O` | One precreated state row for `field_operations`; NULL before first success; updated in same transaction as gold data |
| `ctl.load_attempt` / candidate + attempt number | `publication_id VARCHAR(64) N`; `attempt_number INT N`; `started_at_utc DATETIME2(6) N`; `finished_at_utc DATETIME2(6) O`; `status VARCHAR(32) N`; `error_code VARCHAR(64) O`; `error_message VARCHAR(2048) O` | Durable execution/retry diagnostics independent of a rolled-back promotion |

Control-field widths are explicit operational assumptions; reject/trap overflow and retain a longer external diagnostic artifact reference in snapshot evidence if required, never silently truncate source business data. Technical statuses are proposed controlled values: manifest CAPTURED, BUILT, VALIDATED, REJECTED, PUBLISHED; attempt RUNNING, SUCCEEDED, FAILED; validation PASS/FAIL with existing severity meanings. No status alone proves inputs unchanged: fingerprint, version, checks and source rows must agree.

### Proposed promotion protocol (not implemented)

1. Phase 11.4 captures a consistent accepted input set into isolated publication-tagged stg rows. Require a producer coordination/freeze or immutable-version capture with before/after checks that proves the set belongs together; SQL read access alone is insufficient. Record all twelve entities, weather extraction/retained version evidence and configuration. Preserve original values and known/unknown run attribution.
2. Allocate keys through the protected registry writer, then build a complete candidate. Keep all earlier published data untouched. Once validated, make that candidate immutable to builders until promotion completes; a single controlled run/permission boundary prevents time-of-check/time-of-use changes.
3. Evaluate all logical D01–D15 requirements and physical gates below. Record successful checks even with zero findings. Reject duplicate grains, identity conflicts, unresolved populated parents, lossy conversion, inconsistent source sets, measure/count mismatches or missing evidence. Preserve accepted Silver warnings rather than reclassifying them arbitrarily.
4. One dedicated publisher connection begins an explicit Warehouse transaction. It verifies the expected previous publication and frozen candidate identity, applies all fourteen table changes using explicit columns/keys, and updates the state row and PUBLISHED manifest status together. It must not distribute these statements across dbt worker sessions or pipeline activities with independent transactions.
5. Commit only if the complete operation succeeds. On failure explicitly roll back the whole transaction; record failed-attempt diagnostics afterward in a separate transaction. On uncertain client outcome, reconnect and inspect publication_state before retrying. If the candidate is already current, reconcile success instead of publishing twice.
6. Gate semantic refresh and publication concurrency. A single SQL transaction/query can observe a coherent snapshot, but unrelated reader statements that straddle a commit are not automatically one consumer snapshot. For the initial design, prevent further promotion during a semantic refresh and verify its publication tag before/after; the actual semantic mode remains a later decision. Do not claim SQL commit alone atomically refreshes Power BI/Direct Lake caches.

This selects a supported **transactional DML approach** rather than a multi-view rename/swap or physical version selector as the initial design. Platform support is documented, but actual rollback, visibility, timeout and permission behavior still require controlled live proof. Performance at much larger data volumes may require a separately reviewed publication method; never change grain or identity to work around it. No publication implementation occurs in this phase.

### Eight-orphan rejection must use accepted parents

Quarantined Job Site 1 leaves accepted schedules **1, 117, 137, 156, 192, 242** and assignments **15, 96** referencing it: exactly **8** missing-parent relationships. The source/candidate gate must reject all eight even if registry or prior gold contains that site. No unknown-member substitution, filtering those children out, or joining to prior published parents is permitted. Prior good facts, Type 1 dimensions, publication state, counts/totals and existing mappings remain unchanged. Failure diagnostics remain available outside the aborted promotion. This is future Phase 11.4/11.7 acceptance, not a new Fabric test result.

## 13. Silver access, dbt, and security boundaries

Preferred future access: same-workspace three-part SQL references from WH_FieldOps to `[LH_FieldOps].[silver].[<entity>]` and `[LH_FieldOps].[dbo].[silver_weather_forecast_hourly]`. Validate authorization, collation, schemas/types, SQL sync and captured counts first. Do not use the incorrect intermediate `silver.operations` object, treat Delta directory names as SQL schemas, query negative/quarantine outputs as clean sources, or write through the Lakehouse SQL endpoint.

Phase 11.4 should persist a replayable source set in stg before dbt transformation; a mutable cross-database view alone is not a frozen snapshot. If endpoint fidelity/availability fails, review an authorized Fabric copy/extraction mechanism that preserves the same contracts; no new movement mechanism is implemented here. Bronze monitoring may inform provenance but cannot fabricate missing Silver lineage.

| Phase | Responsibility / deliverable boundary |
| --- | --- |
| 11.3 | Physical columns/types, schema/key/constraint/publication-support design; approved controlled capability proofs only. No production integration or models. |
| 11.4 | Consistent accepted Silver capture, manifests, landing objects, source profiling/lineage and publication orchestration implementation under later approval |
| 11.5 | dbt Gold candidate transformations, explicit casting, calendar and dimensional key lookups; controlled Type 1/forecast behavior following this design |
| 11.6 | dbt tests, source/model lineage and documentation; compiled adapter behavior and schema routing validation |
| 11.7 | Deterministic reconciliation and positive/negative publication acceptance, concurrency/failure/recovery tests and semantic-consumption consistency |

Recommend `dbt-fabric` for later Warehouse execution, but no version/profile/runtime is installed or selected by this task. Later pin compatible dbt-core/adapter/Python/ODBC versions, inspect generated SQL and custom-schema naming, and confirm builds route exclusively to candidate outputs. Do not assume setting schema to candidate yields that exact schema without inspecting adapter/project naming behavior. Future `full_refresh: false` on protected resources is only one guard; registry/gold must also be outside ordinary model ownership and protected by permissions. No ordinary dbt run across multiple models is assumed to be one transaction. A publisher is a separate controlled deployment/load responsibility.

Proposed access responsibilities: deployer provisions approved schemas/objects; capture identity reads verified Silver and writes stg; builder reads frozen inputs/mappings and writes candidate; allocator/publisher controls registry, publication metadata and gold DML; consumers read gold only. Control evidence may need narrower write grants per responsibility. Actual principals, workspace/item grants, capacity/network/ODBC configuration and secret storage are unverified. Use Entra-based access consistent with M11/M12, keep secrets outside repository, and verify effective permissions under the intended runtime identity. Broad workspace roles can defeat schema isolation; do not treat a SQL DENY as proof of isolation for privileged principals. No unsupported CREATE USER recipe or invented row-level business security policy is proposed.

## 14. Physical acceptance gates and live-proof plan

All tests here are **proposed, not run**. Existing read-only Steps 1–3 are evidence, not a substitute for these proofs. Do not run any query or create even a disposable proof object until the owner approves its scope. These are review specifications, not production deployment instructions.

| Gate | Exact required proof / PASS | Failure consequence |
| --- | --- | --- |
| P01 — context/access | Reconfirm WH_FieldOps, executing principal, actual Warehouse/source collations, and authorized object-level read/provisioning rights | Hold completion; never create a replacement Warehouse to change collation |
| P02 — source fidelity | Profile all required columns for byte lengths, NULLs, types/precision and round-trip casts. Check 921 operational baseline rows, per-entity counts, 4,032 designated weather rows, weather composite uniqueness, exact location mappings and UTC/local serialization | Stop before target load on truncation, loss, ambiguous times or source-contract mismatch |
| P03 — physical types | Disposable table stores BIGINT, INT, BIT, DATE, DATETIME2(6), DECIMAL(19,6), DECIMAL(28,12), FLOAT(53), chosen UTF-8 strings/lengths. Include non-ASCII and 6-digit fractional values; retrieve equal values | Do not infer support from sys.types or silently round/change source semantics |
| P04 — identity/sentinels/recovery | Disposable identity registry allocates positive distinct integers, preserves mappings on replay/attribute change and dimension rebuild; explicit -1/-2 identity insertion works in that disposable identity table; OFF + reseed; restore positive key mappings and allocate without collision | Hold key mechanism; logical integer strategy is not replaced without review |
| P05 — constraints/comparison | ALTER metadata PK/UNIQUE NONCLUSTERED NOT ENFORCED and FK NOT ENFORCED accepted on clean disposable objects; inspect metadata. Gate detects separate duplicate/orphan fixtures without relying on those declarations. Exact identity predicate distinguishes case and trailing whitespace | Hold metadata assertions/identity implementation until byte-exact matching is proven |
| P06 — atomic DML | Two-session test changes two tables plus publication marker in one explicit transaction; rollback leaves all old values; commit exposes all new values in one reader transaction; no mixed state. Simulated disconnection resolves through durable marker | Hold publication design completion; SQL docs alone are not a deployed proof |
| P07 — protected key lifecycle | Chosen writer credential/orchestration prevents overlapping allocation/promotion, forbids builder registry/gold drop/write, and restores a checkpoint with identical mappings before new allocation | Blocks deployment; NOT ENFORCED constraints are not a lock |
| P08 — complete physical reconciliation | Candidate has 11 dimensions, 3 facts, all mapped columns/valid sizes, one publication ID; dimension baselines 511 operational +3 locations excluding sentinels/calendar; schedule totals 250/2000/10912 and statuses 197/44/9; assignments 120/1200; weather versions retained | Blocks publication; no row dropping or latest collapse |
| P09 — negative publication | Exact eight post-disposition orphans rejected with prior good facts/dimensions/publication unchanged; all diagnostic outcomes retained | Blocks Phase 11.7 acceptance |
| P10 — dbt/consumer boundary | Selected adapter compilation and future isolated rebuild preserve registry keys, route schemas correctly, and do not publish per-model. Consumer refresh observes one publication | Required before implementation is exposed to consumers |

P01–P06 are the next physical capability/fidelity evidence needed to close Phase 11.3. P07's concrete runtime selection must be reviewed before implementation; its operational proof and P08–P10 full-model executions belong to later implementation/acceptance, not authorization to start them now. The present phase status remains READY FOR LIVE PROOF, with no claim that an atomic publication control exists.

### Next proposed test: P01 read-only context, collation and access evidence

Purpose: close missing actual-collation and Warehouse-to-Lakehouse access evidence before approving a disposable write proof. The following is the exact proposed query batch for the existing WH_FieldOps connection. It is documentation-only SQL, does not create/alter data or objects, and requires **no cleanup**. It has not been executed.

```sql
-- PROPOSED READ-ONLY PROOF; OWNER APPROVAL REQUIRED BEFORE EXECUTION.
SELECT DB_NAME() AS warehouse_name, SESSION_USER AS executing_user;
SELECT name, collation_name FROM sys.databases;
SELECT permission_name
FROM fn_my_permissions(NULL, 'DATABASE')
WHERE permission_name IN ('CREATE SCHEMA', 'CREATE TABLE', 'ALTER', 'CONTROL');
SELECT COUNT_BIG(*) AS regions_rows FROM [LH_FieldOps].[silver].[regions];
SELECT COUNT_BIG(*) AS field_schedules_rows FROM [LH_FieldOps].[silver].[field_schedules];
SELECT COUNT_BIG(*) AS equipment_assignments_rows FROM [LH_FieldOps].[silver].[equipment_assignments];
SELECT COUNT_BIG(*) AS weather_rows FROM [LH_FieldOps].[dbo].[silver_weather_forecast_hourly];
```

PASS: expected Warehouse/principal, actual UTF-8 collation identified, permission results recorded and checked alongside Fabric role membership, and successful cross-item reads. If the original baseline remains selected, counts should be 4 / 250 / 120 / 4032. Changed source counts require a new manifest/context, not an automatic regression claim. An empty permission result, permission-function availability error, or missing source access means the gate remains unproven; obtain approved permission evidence rather than infer rights. SQL permission output alone cannot prove required workspace role membership. This batch samples access only; P02 must profile all sources and it does not prove snapshot coherence.

### Subsequent proposed controlled proof objects — separate approval required

No production DDL is provided. The exact test scope proposed for review is one new schema **`proof_phase113`** and four tiny tables **`key_registry`**, **`dimension_copy`**, **`fact_copy`**, **`publication_marker`**, all inside existing WH_FieldOps. Abort if that schema already exists; never drop or reuse an unknown existing object. No real source records are needed. A later approved proof script must be reviewed before execution.

- `key_registry`: identity BIGINT key, VARCHAR(64) test business code. Insert A and B, record the generated values, rebuild the ordinary-BIGINT dimension_copy with those values, change A's label, and verify unchanged keys. Explicitly insert -1/-2 in the proof identity table only; turn IDENTITY_INSERT off, reseed, insert C and confirm uniqueness/positive generated key. Restore the recorded positive mappings into a clean proof registry during the controlled recovery portion, reseed, and show a new D cannot collide. Never infer a particular next number.
- `dimension_copy`: ordinary BIGINT key, VARCHAR(64) code, VARCHAR(256) label, DATE, DATETIME2(6), DECIMAL(19,6), DECIMAL(28,12), FLOAT(53), BIT test fields. Exercise explicit -1/-2, Unicode, NULLs and precise round trips. PK metadata on its integer key; UNIQUE metadata tested on a separate clean test-code set. Use case/trailing-space probes such as A/a/A-with-trailing-space outside declared text uniqueness promises.
- `fact_copy`: INT row ID, BIGINT dimension key, INT version marker. Seed one valid row. Separately present duplicate/orphan candidate fixtures to an explicit validation query; do not insert known-invalid rows into metadata-constrained published test tables or rely on optimizer behavior with violated constraints.
- `publication_marker`: one INT model key and INT current version. Seed version 1. Session A begins a transaction updating dimension label, fact marker and publication marker to version 2; before commit, Session B reads all three together in one transaction and must see the old committed set (or supported blocking, never a mixed set). Roll back A and verify version 1 remains. Repeat with commit and a fresh B transaction; expect the entire version 2 set. Inject an error before commit and demonstrate full rollback. On an uncertain connection outcome, reconnect and read the marker before retrying.

This proof **writes disposable test objects/data** and is not authorized by this document. PASS requires the full P03–P06 assertions and a recorded cleanup outcome, not just successful CREATE TABLE. Any failure stops production design implementation and leaves an explicit unresolved finding.

Cleanup after the separately approved proof: ensure both sessions have ended/rolled back open transactions and IDENTITY_INSERT is OFF; drop the proof FK/constraints as needed, then only `proof_phase113.fact_copy`, `dimension_copy`, `publication_marker`, `key_registry`, and finally the empty `proof_phase113` schema. Confirm the schema/object inventory matches its pre-proof state and that no gold/stg/candidate/ctl objects were created. Preserve result evidence before cleanup. Cleanup must never touch dbo/system objects or any object not created by that approved proof.

## 15. Remaining questions and completion decision

| Open question | Boundary / required resolution |
| --- | --- |
| Actual collation, cross-item access and effective principals | P01 live metadata/permission proof; no assumed defaults or replacement Warehouse |
| Source sizing, NULLs, microseconds, UTC round trips and exact key comparison | P02/P03/P05 profiling and adversarial conversion checks; current sizes are assumptions with fail-on-loss gates |
| Native allocation, explicit insertion/reseed and recoverability in this item | P04 controlled proof; stable keys require durable registry plus restore process, not identity alone |
| Single-transaction rollback and reader visibility through chosen client | P06 controlled two-session proof; cannot mark coherent publication implemented |
| Runtime serialization, protection and recovery evidence retention | Select orchestration/credentials, approved registry backup/export/checkpoint mechanism and evidence retention before deployment; test P07 later. Do not assume an unspecified Fabric backup alone covers external manifests. |
| dbt version/materializations/schema routing | No existing project; select/pin and review compiled SQL in Phase 11.5/11.6. Generic adapter support does not prove key-safe rebuilds. |
| Coherent Silver snapshot and always-written validation ledger | Phase 11.4 design/implementation prerequisite; current missing findings and run attribution remain unresolved |
| Reporting/risk/temporal and rule policies | Same Phase 11.2 boundaries: forecast applicability, operational timezone/DST, precipitation semantics, heat-index definition, threshold registry/precedence, history/retention and semantic roles are not invented here |

The proposed physical model is reviewable without changing logical grains or SCD strategy. Nevertheless **Phase 11.3 is not COMPLETE** because the local capability/fidelity proofs above are outstanding. Failure of a physical capability requires reporting and revisiting that mechanism; any conflict with an approved logical identity/grain/relationship requires stopping for design review. No Phase 11.4 work has begun.

**Single recommended next action:** review this physical specification and approve the P01 read-only live-proof batch above. No Fabric execution or implementation should occur before that approval.

## 16. Repository validation record

The pre-existing Phase 11.2 README/design changes remain unchanged. This phase introduces only this Markdown document; no production SQL, dbt configuration/model, test, notebook, code, or synthetic data file was modified. Validation on 2026-09-24:

- Documentation audit: **86 checks passed**, including 16 local links, 14 official Microsoft evidence URLs, 26 Markdown tables, 175 physical columns across 14 core tables including common audit columns, all 24 integer FK roles/types, logical-to-physical field coverage, fixture type/size/null compatibility, and unchanged pre-task files. This is a local specification audit, not live SQL compilation or a Warehouse proof.
- Final existing test suite: `uv --cache-dir .uv-cache run --offline --isolated --python 3.12 --extra dev python -m pytest -q` — **129 passed in 5.03s**, no failures or skips reported. Supported Python 3.12 required approved access outside the sandbox after interpreter access was denied; no Fabric connection was involved.
- `git diff --check` and the new document's unstaged/no-index whitespace check passed. The in-memory generator profile/audit wrote no synthetic source files; disposable local audit scripts were removed afterward.
- Preservation evidence: README SHA-256 `8870F6D81FA743F9F7A683BE1811CD4DA2E7B5E39D2D0568476D9C9D3A7A215E`; Phase 11.2 document SHA-256 `3AB465BCA71FDD9918531F5188BABE498BFD23ABE302002E9326620D55472895`, matching task-start values.
- Expected final status: pre-existing `M README.md`, pre-existing `?? docs/phase-11-2-dimensional-design.md`, and new `?? docs/phase-11-3-warehouse-design-verification.md`. No staging, commit, push, Fabric execution or Phase 11.4 implementation occurred.

**Correction to earlier validation bookkeeping:** Phase 11.2 section 20 reports 104 operational source columns. Counting the actual generator/contracts gives **94**: regions 4, offices 5, employees 7, projects 12, job_sites 6, crews 6, activities 5, equipment_types 5, equipment 7, field_schedules 14, equipment_assignments 8, safety_thresholds 15. All 94 have a disposition here (79 mapped to core tables and 15 retained rule fields), plus all 29 Weather Silver columns. This is an arithmetic error in the earlier audit summary, not missing source mappings or a change to the approved logical design. The Phase 11.2 file is deliberately not edited in this task.
