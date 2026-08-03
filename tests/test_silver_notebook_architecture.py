from __future__ import annotations

import re
from pathlib import Path


NOTEBOOK = Path(__file__).parents[1] / "notebooks" / "NB_Operational_Silver_Validation.py"


def test_notebook_preserves_bronze_text_and_clears_empty_accepted_output() -> None:
    source = NOTEBOOK.read_text(encoding="utf-8")
    assert '.option("inferSchema", False)' in source
    assert "schema=source_frames[entity_output.entity].schema" in source
    assert "if entity_output.accepted_records" not in source


def test_notebook_has_no_rule_metadata_or_historical_run_constants() -> None:
    source = NOTEBOOK.read_text(encoding="utf-8")
    assert re.search(r"(?:REG|OFF|EMP|PRJ|JBS|CRW|ACT|FSD|EQT|EQP|EQA|SFT|XEN)-\d{3}", source) is None
    assert re.search(r"(?:ERR|WARN|INFO)_[A-Z0-9_]+", source) is None
    assert "accepted_20260101" not in source


def test_notebook_supports_pipeline_ids_and_manual_bronze_discovery() -> None:
    source = NOTEBOOK.read_text(encoding="utf-8")
    assert 'MONITORING_TABLE = "monitoring_operational_ingestion_runs"' in source
    assert "HAVING COUNT(DISTINCT entity_name) = {len(ALL_ENTITIES)}" in source
    assert "if requested_source_run_id" in source
    assert "else discover_latest_bronze_run(runtime.ingestion_date)" in source
    assert "requested_silver_run_id or" in source
    assert "silver-{resolved_source_run_id}-" in source


def test_notebook_registers_negative_acceptance_delta_outputs() -> None:
    source = NOTEBOOK.read_text(encoding="utf-8")
    for schema in ("silver_negative", "quarantine_negative", "validation_negative"):
        assert f'spark.sql("CREATE SCHEMA IF NOT EXISTS {schema}")' in source
    assert 'silver_schema = "silver_negative"' in source
    assert 'quarantine_schema = "quarantine_negative"' in source
    assert 'validation_table = "validation_negative.operational_results"' in source
    assert source.count(".saveAsTable(") == 3
    assert ".write.save(" not in source
    assert '.option("path", f"{runtime.silver_root}/{entity_output.entity}")' in source
    assert '.option("path", f"{runtime.quarantine_root}/{entity_output.entity}")' in source
    assert '.option("path", runtime.validation_results_root)' in source
