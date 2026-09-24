# Enterprise Field Operations Intelligence Platform

## Overview

The Field Operations Intelligence Platform is an enterprise-style analytics engineering project demonstrating how operational data can be ingested from REST APIs into Microsoft Fabric using Medallion Architecture, transformed with dbt, orchestrated through Microsoft Fabric Pipelines, and presented through semantic models and Power BI.

This project is being developed using software engineering practices including Git, GitHub, version control, incremental development, and documentation-first design.

---

## Business Scenario

Many organizations collect operational data from multiple systems but struggle to produce consistent, trustworthy reporting.

This project demonstrates how an organization can build a modern analytics platform that:

- Ingests operational data from public REST APIs
- Stores raw data in a Bronze layer
- Cleans and standardizes data in a Silver layer
- Produces business-ready Gold models
- Applies analytics engineering using dbt
- Serves trusted semantic models to Power BI

---

## Technology Stack

- Microsoft Fabric
- OneLake
- Lakehouse
- Warehouse
- Microsoft Fabric Pipelines
- PySpark
- Python
- dbt
- SQL
- Git
- GitHub
- Power BI

---

## Repository Structure

(To be completed during project development.)

---

## Project Status

- Phase 10, Step 2 is complete.
- Phase 10 Step 3 — Operational Silver Validation is complete. All 12 operational entities implement 65 of 66 mapped Version 1 rules, and both the clean baseline and deterministic negative acceptance workflow passed in Microsoft Fabric.
- The verified negative Fabric run produced 921 rows read, 918 accepted, 3 quarantined, 6 Critical findings, 1 Warning finding, and 2 Info findings; quarantine and validation outputs were verified through the SQL analytics endpoint.
- FSD-008 remains explicitly deferred because immutable prior-state/change-event evidence is not available in a single Bronze batch. Its future implementation is outside the completed Version 1 boundary.
- `docs/silver-validation-rule-mapping-matrix.md` remains the implementation authority.
- Bronze and Silver remain Python/PySpark-based. Gold will use dbt for dimensional models, tests, lineage, and documentation.
- As with Bronze, reusable Silver code is built as a Python wheel and installed in the Fabric Environment; notebooks import that package and remain orchestration-focused.

### Phase 11 — Warehouse & Analytics Engineering

Phase 11.1 — Discovery & Requirements Reconciliation is **COMPLETE**. The user-reported live verification confirmed 12 readable operational Delta sources, 921 rows, matching expected counts and column sets, and all 12 SQL endpoint objects as `silver.<entity>`. Weather Silver contained 4,032 rows; Bronze monitoring contained 180 rows. Current validation-results persistence findings and lineage limits are recorded separately from historical Phase 10 acceptance evidence.

The verified environment is workspace `WS_FieldOps_Dev`, environment `ENV_FieldOps_Dev`, Lakehouse and SQL analytics endpoint `LH_FieldOps`. Warehouse `WH_FieldOps` already exists.

| Step | Scope | Status |
| --- | --- | --- |
| 11.1 | Discovery & Requirements Reconciliation | COMPLETE |
| 11.2 | Dimensional Design | COMPLETE |
| 11.3 | Warehouse Design / Verification / Configuration of existing `WH_FieldOps` | NEXT |
| 11.4 | Silver-to-Warehouse Integration | Planned |
| 11.5 | dbt Gold Implementation | Planned |
| 11.6 | dbt Tests, Lineage & Documentation | Planned |
| 11.7 | Reconciliation & Deterministic Acceptance | Planned |

See the [Phase 11.1 Silver source verification record](docs/phase-11-1-silver-source-verification.md) and the [Phase 11.2 dimensional design](docs/phase-11-2-dimensional-design.md). Phase 11.2 defines three base facts, eleven dimensions, persistent integer surrogate keys, Type 1 entity dimensions, a static date dimension, and publication controls that reject invalid candidate batches while preserving the prior good state. Safety thresholds remain a separate rule input. Physical platform verification, source publication dependencies, and risk-engine policies remain later work; Warehouse DDL and dbt models have not been implemented.

🚧 In Development
