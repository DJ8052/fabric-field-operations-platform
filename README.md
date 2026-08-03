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

🚧 In Development
