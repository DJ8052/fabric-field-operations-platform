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
- Phase 10, Step 3 design gate is complete; Silver implementation has begun with the master-entity validation foundation.
- Complex Field Schedule lineage, Equipment Assignment overlap, and Safety Threshold overlap/conflict rules remain pending.
- `docs/silver-validation-rule-mapping-matrix.md` remains the implementation authority.
- Bronze and Silver remain Python/PySpark-based. Gold will use dbt for dimensional models, tests, lineage, and documentation.
- As with Bronze, reusable Silver code is built as a Python wheel and installed in the Fabric Environment; notebooks import that package and remain orchestration-focused.

🚧 In Development
