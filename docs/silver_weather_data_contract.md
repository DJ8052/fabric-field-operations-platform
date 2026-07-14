# Silver Weather Forecast Data Contract

## Purpose

The Silver weather layer converts the semi-structured hourly forecast arrays
stored in Bronze JSON files into a validated, relational dataset.

The Silver dataset preserves source lineage and forecast version history while
providing one analytics-ready row for each hourly forecast observation.

This contract defines the expected grain, key, schema, transformations, and
validation rules for Phase 5.

---

## Source

```text
LH_FieldOps
└── Files
    └── bronze
        └── weather_forecast
            └── location_id=<location_id>
                └── ingestion_date=<YYYY-MM-DD>
                    └── run_<pipeline_run_id>.json