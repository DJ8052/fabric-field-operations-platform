Synthetic Data Generation Plan

Phase 9 — Operational Domain Design | Synthetic Data Generation Plan

Purpose: define exactly how synthetic operational data will be generated — deterministically, not randomly — so that Phase 10 implementation is a mechanical exercise against this spec, not a series of ad hoc decisions.

Deterministic Generation Principles
Fixed random seed. All generation uses a single, documented seed value (e.g., RANDOM_SEED = 20260101). The same seed against the same generation code always produces byte-identical output. This is what "deterministic" means operationally — not merely "realistic-looking."
Stable business keys. Business keys (project_code, crew_code, etc.) are generated once per entity and never regenerated across runs — re-running the generator does not shuffle or reassign keys.
Fixed date ranges. All schedule dates fall within an explicitly stated window (e.g., 2026-01-01 through 2026-12-31), not relative-to-today ranges that would shift output on every run.
Controlled distributions, not uniform-random. E.g., activity types are drawn from a weighted distribution reflecting realistic operational mix (see Scale below), not an even 1/N chance across all activities.
Hand-designed risk scenarios, layered on top of the base distribution — a subset of Field Schedule rows are deliberately constructed to hit each Risk Validation Matrix scenario (normal, high wind, lightning override, etc.), rather than relying on random chance to produce them.
Repeatable outputs from the same configuration — changing the scale parameters (see below) regenerates a consistent dataset; changing nothing regenerates the identical dataset.
Byte-identical reproducibility requires more than a fixed seed. A seed alone controls random draws, but does not guarantee identical output files unless these are also fixed:
Stable row ordering — rows are written in a deterministic sort order (e.g., by business key), never in whatever order they happened to be generated or iterated
Fixed timestamp formatting — a single, explicit format (e.g., ISO8601) applied consistently, not locale- or library-default-dependent
Fixed column ordering — CSV column order is explicitly defined, not derived from dict/object iteration order
Fixed line endings — explicit (e.g., \n), not OS-default
Exclusion of volatile fields — any field that reflects actual runtime (e.g., "file generated at") is excluded from the data itself, or isolated into a separate metadata field that is allowed to vary without affecting whether the business data is byte-identical
Scale (Starting Parameters)
Entity	Target Count	Rationale
Regions	3–4	Enough for Regional Operations page variety without excess
Offices	10–20	Spread across regions
Employees	~150	Enough to cover project managers, field managers, and crew leads without heavy reuse
Projects	50–100	Matches original Phase 9 planning scale
Job Sites	80–150	Some projects span multiple sites (1:1.5 avg ratio)
Crews	30–50	Matches original planning scale
Activities	15–25	A controlled catalog — not one row per project, a fixed reference set
Field Schedules	200+	Matches original planning scale; deliberately includes reschedule chains
Equipment Types	8–12	Cranes, generators, scaffolding, etc.
Equipment	60–100	
Equipment Assignments	~1.5× Equipment count	Some equipment reassigned during the period
Safety Thresholds	30–50	Multiple rules per activity (wind/heat/precip/lightning per relevant activity)
Scenario Groups (Explicit Generation Targets)

Each of the following must be deliberately constructed, not left to chance, to guarantee the Risk Validation Matrix and Dashboard Coverage Matrix both have real data to validate against:

Low-risk normal operations — the majority baseline case
Moderate weather exposure — single-factor moderate scores
High wind + equipment exposure — compounding case (Risk Validation Matrix Scenario 8)
Extreme heat — single-factor case (Scenario 3)
Heavy precipitation — single-factor case (Scenario 4)
Mandatory safety shutdown (lightning override) — the adversarial proof case (Scenario 5) — must exist in the generated dataset, not left to random chance of a weather code landing on 95/96/99
Crew rescheduling conflict — at least one Field Schedule reschedule chain of 2+ links, exercising the immutability/lineage rule from the Data Contracts
Equipment relocation requirement — at least one high-exposure equipment assignment overlapping a high-risk window
Multiple projects competing for the same crew — at least one crew with overlapping or back-to-back Field Schedule rows across different projects in the same period, to exercise the Crew Scheduling page's "which crews need rescheduling" question meaningfully
Weather-Diversity Constraint (carried forward from Task 1/2)

Since only 3 distinct weather forecast sets exist per run (TX-DAL, TX-HOU, TX-AUS), scenario diversity above is engineered through activity type, equipment exposure, safety thresholds, crew size, and schedule timing — not through weather variation. Job sites should be deliberately distributed across all 3 locations, but the scenario groups above must not assume a 4th or 5th distinct weather condition will naturally appear.

Generation Order (Respects Foreign Key Dependencies)
1. Region
2. Office (needs Region)
3. Employee (needs Office)
4. Activity (no dependencies — reference data)
5. Equipment Type (no dependencies — reference data)
6. Safety Threshold (needs Activity, Equipment Type)
7. Project (needs Office, Employee ×2)
8. Job Site (needs Project, existing Weather Location config)
9. Crew (needs Office, Employee for crew lead)
10. Equipment (needs Equipment Type)
11. Field Schedule (needs Project, Job Site, Crew, Activity)
    — reschedule chains generated as a second pass after base
      schedules exist, so rescheduled_from_schedule_id has valid
      targets
12. Equipment Assignment (needs Equipment, Project, Job Site)
Validation Strategy: Accepted Dataset vs. Negative-Test Dataset

Bronze should preserve source-like artifacts, including deliberately invalid records when the goal is to prove Silver's rejection behavior — requiring every Bronze-bound record to pass every hard-reject rule would make it impossible to test the failure path at all.

The standard accepted synthetic dataset must satisfy all hard-reject contract rules in operational-data-contracts.md. This is the dataset used to build out Silver/Gold and populate the dashboards.
A separate, controlled negative-test dataset may intentionally violate selected contract rules (e.g., an orphaned foreign key, an overlapping Equipment Assignment window, a cycle in rescheduled_from_schedule_id) specifically so that Silver's rejection, quarantine, reason-code logging, and monitoring behavior can be validated against a known bad input — the same principle as the deliberately adversarial lightning-override case in the Risk Validation Matrix.
Both outputs must be deterministic (same principles as above) and clearly identified by dataset type or scenario identifier (e.g., a dataset_type tag or a distinct run_id naming convention) so accepted and negative-test data are never accidentally mixed into the same Silver build.
Output Format

Following the same Bronze pattern already established for weather:

Files/bronze/operations/
├── regions/ingestion_date=<date>/run_<run_id>.csv
├── offices/ingestion_date=<date>/run_<run_id>.csv
├── employees/ingestion_date=<date>/run_<run_id>.csv
├── projects/ingestion_date=<date>/run_<run_id>.csv
├── job_sites/ingestion_date=<date>/run_<run_id>.csv
├── crews/ingestion_date=<date>/run_<run_id>.csv
├── activities/ingestion_date=<date>/run_<run_id>.csv
├── field_schedules/ingestion_date=<date>/run_<run_id>.csv
├── equipment_types/ingestion_date=<date>/run_<run_id>.csv
├── equipment/ingestion_date=<date>/run_<run_id>.csv
├── equipment_assignments/ingestion_date=<date>/run_<run_id>.csv
└── safety_thresholds/ingestion_date=<date>/run_<run_id>.csv

All 12 approved source entities are represented — the earlier draft omitted regions, employees, and equipment_types.

CSV chosen over JSON here since these are flat, tabular synthetic records (unlike the nested weather API response) — consistent with treating them as "source-like artifacts" per the original Phase 9 planning.

Status

This plan is ready to drive Phase 10 implementation (synthetic data generation script → Bronze → Silver). It depends on the Data Contracts (Task 3) as the validation authority and the Risk Validation Matrix (Task 5) as the scenario-coverage target.