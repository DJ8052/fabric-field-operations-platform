# Fabric notebook source
# Orchestrate master-entity Bronze reads and operational Silver validation writes.

from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
import json

from operational_silver_validation import ALL_ENTITIES, resolve_runtime_config, validate_operational_entities


# Fabric pipeline/notebook parameters may supply any of these lowercase names.
# Blank run IDs are meaningful: source_run_id triggers Bronze monitoring
# discovery, while silver_run_id triggers unique run-ID generation.
parameter_values = {
    name: globals()[name]
    for name in (
        "ingestion_date", "source_run_id", "silver_run_id", "bronze_root",
        "silver_root", "quarantine_root", "validation_results_root",
    )
    if name in globals()
}


def optional_parameter(name: str) -> str:
    value = parameter_values.get(name)
    return value.strip() if isinstance(value, str) else ""


# Resolve ingestion_date and paths with the existing runtime configuration.
# Run IDs are resolved below because blank values have notebook-specific
# discovery/generation semantics that differ from package development defaults.
runtime = resolve_runtime_config({
    name: value
    for name, value in parameter_values.items()
    if name not in {"source_run_id", "silver_run_id"}
    and isinstance(value, str)
    and value.strip()
})

MONITORING_TABLE = "monitoring_operational_ingestion_runs"


def discover_latest_bronze_run(ingestion_date: str) -> str:
    """Return the latest run where all operational entities succeeded."""
    successful_runs = spark.sql(
        f"""
        SELECT
            run_id,
            MAX(completed_at) AS completed_at
        FROM {MONITORING_TABLE}
        WHERE ingestion_date = DATE '{ingestion_date}'
          AND status = 'SUCCEEDED'
        GROUP BY run_id
        HAVING COUNT(DISTINCT entity_name) = {len(ALL_ENTITIES)}
        ORDER BY completed_at DESC, run_id DESC
        LIMIT 1
        """
    ).collect()
    if not successful_runs:
        raise RuntimeError(
            "No successful complete Bronze run was found in "
            f"{MONITORING_TABLE} for ingestion_date={ingestion_date}"
        )
    return str(successful_runs[0]["run_id"])


requested_source_run_id = optional_parameter("source_run_id")
resolved_source_run_id = (
    requested_source_run_id
    if requested_source_run_id
    else discover_latest_bronze_run(runtime.ingestion_date)
)

requested_silver_run_id = optional_parameter("silver_run_id")
resolved_silver_run_id = requested_silver_run_id or (
    f"silver-{resolved_source_run_id}-"
    f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}"
)

runtime = replace(
    runtime,
    source_run_id=resolved_source_run_id,
    silver_run_id=resolved_silver_run_id,
)

print(
    f"ingestion_date={runtime.ingestion_date}, "
    f"source_run_id={runtime.source_run_id}, "
    f"silver_run_id={runtime.silver_run_id}"
)

def is_negative_acceptance_run(
    silver_root: str,
    quarantine_root: str,
    validation_results_root: str,
) -> bool:
    """Identify the explicitly isolated negative-acceptance destinations."""
    configured_roots = tuple(
        root.rstrip("/").lower()
        for root in (silver_root, quarantine_root, validation_results_root)
    )
    return configured_roots == (
        "tables/silver_negative",
        "tables/quarantine_negative",
        "tables/validation_negative/operational_results",
    )


negative_acceptance_run = is_negative_acceptance_run(
    runtime.silver_root,
    runtime.quarantine_root,
    runtime.validation_results_root,
)

spark.sql("CREATE SCHEMA IF NOT EXISTS silver_negative")
spark.sql("CREATE SCHEMA IF NOT EXISTS quarantine_negative")
spark.sql("CREATE SCHEMA IF NOT EXISTS validation_negative")

if negative_acceptance_run:
    silver_schema = "silver_negative"
    quarantine_schema = "quarantine_negative"
    validation_table = "validation_negative.operational_results"

def bronze_path(entity: str) -> str:
    return f"{runtime.bronze_root}/{entity}/ingestion_date={runtime.ingestion_date}/run_{runtime.source_run_id}.csv"


datasets = {}
source_identifiers = {}
source_frames = {}
for entity in ALL_ENTITIES:
    path = bronze_path(entity)
    source_identifiers[entity] = path
    # Bronze CSV values remain strings so validation and quarantine preserve
    # exact source text; typed Silver projection belongs in a later adapter.
    source_frame = spark.read.option("header", True).option("inferSchema", False).csv(path)
    source_frames[entity] = source_frame
    datasets[entity] = [row.asDict(recursive=True) for row in source_frame.collect()]

validation_timestamp = datetime.now(timezone.utc)
output = validate_operational_entities(
    datasets,
    runtime.silver_run_id,
    source_identifiers=source_identifiers,
    clock=lambda: validation_timestamp,
)

for entity_output in output.entities:
    accepted_frame = spark.createDataFrame(
        list(entity_output.accepted_records),
        schema=source_frames[entity_output.entity].schema,
    )
    accepted_writer = accepted_frame.write.format("delta").mode("overwrite")
    if negative_acceptance_run:
        accepted_writer.saveAsTable(f"{silver_schema}.{entity_output.entity}")
    else:
        accepted_writer.save(f"{runtime.silver_root}/{entity_output.entity}")
    if entity_output.quarantine_records:
        quarantine_rows = [
            {
                "run_id": item.run_id,
                "entity": item.entity,
                "record_id": item.record_id,
                "source_identifier": item.source_identifier,
                "source_record_json": json.dumps(item.source_record, default=str, sort_keys=True),
                "critical_rule_ids": json.dumps(
                    [result.rule_id for result in item.critical_violations]
                ),
                "all_rule_ids": json.dumps(
                    [result.rule_id for result in item.all_results]
                ),
            }
            for item in entity_output.quarantine_records
        ]
        quarantine_writer = (
            spark.createDataFrame(quarantine_rows).write.format("delta").mode("append")
        )
        if negative_acceptance_run:
            quarantine_writer.saveAsTable(f"{quarantine_schema}.{entity_output.entity}")
        else:
            quarantine_writer.save(f"{runtime.quarantine_root}/{entity_output.entity}")
    if entity_output.validation_results:
        result_rows = [
            {**asdict(result), "source_record": json.dumps(result.source_record, default=str, sort_keys=True)}
            for result in entity_output.validation_results
        ]
        results_writer = (
            spark.createDataFrame(result_rows).write.format("delta").mode("append")
        )
        if negative_acceptance_run:
            results_writer.saveAsTable(validation_table)
        else:
            results_writer.save(runtime.validation_results_root)
    print(asdict(entity_output.summary))

print(asdict(output.summary))
