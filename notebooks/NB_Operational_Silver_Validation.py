# Fabric notebook source
# Orchestrate master-entity Bronze reads and operational Silver validation writes.

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import json

from operational_silver_validation import ALL_ENTITIES, resolve_runtime_config, validate_operational_entities


# Fabric pipeline/notebook parameters may supply any of these lowercase names.
# Missing values use development defaults from runtime_config; no historical
# production run is permanently selected by this notebook.
runtime = resolve_runtime_config({
    name: globals()[name]
    for name in (
        "ingestion_date", "source_run_id", "silver_run_id", "bronze_root",
        "silver_root", "quarantine_root", "validation_results_root",
    )
    if name in globals()
})

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
    accepted_frame.write.format("delta").mode("overwrite").save(f"{runtime.silver_root}/{entity_output.entity}")
    if entity_output.quarantine_records:
        quarantine_rows = [
            {
                "run_id": item.run_id,
                "entity": item.entity,
                "record_id": item.record_id,
                "source_identifier": item.source_identifier,
                "source_record_json": json.dumps(item.source_record, default=str, sort_keys=True),
                "critical_rule_ids": [result.rule_id for result in item.critical_violations],
                "all_rule_ids": [result.rule_id for result in item.all_results],
            }
            for item in entity_output.quarantine_records
        ]
        spark.createDataFrame(quarantine_rows).write.format("delta").mode("append").save(f"{runtime.quarantine_root}/{entity_output.entity}")
    if entity_output.validation_results:
        result_rows = [
            {**asdict(result), "source_record": json.dumps(result.source_record, default=str, sort_keys=True)}
            for result in entity_output.validation_results
        ]
        spark.createDataFrame(result_rows).write.format("delta").mode("append").save(runtime.validation_results_root)
    print(asdict(entity_output.summary))

print(asdict(output.summary))
