from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from operational_silver_validation import resolve_runtime_config, validate_master_entities
from operational_silver_validation.relationship_validations import FOREIGN_KEY_RELATIONSHIPS
from test_silver_master_entities import clean_dataset


FIXED_TIME = datetime(2026, 8, 3, 12, tzinfo=timezone.utc)


def _run(data: dict):
    return validate_master_entities(data, "repeatable", clock=lambda: FIXED_TIME, timer=lambda: 5.0)


def test_full_foreign_key_registry_contains_19_relationships() -> None:
    assert len(FOREIGN_KEY_RELATIONSHIPS) == 19
    assert sum(relationship.nullable for relationship in FOREIGN_KEY_RELATIONSHIPS) == 3


def test_notebook_facing_public_imports_and_runtime_parameters() -> None:
    supplied = resolve_runtime_config({
        "ingestion_date": "2026-08-03",
        "source_run_id": "pipeline-source",
        "silver_run_id": "pipeline-silver",
        "bronze_root": "Files/custom-bronze",
    })
    assert supplied.ingestion_date == "2026-08-03"
    assert supplied.source_run_id == "pipeline-source"
    assert supplied.silver_run_id == "pipeline-silver"
    assert supplied.bronze_root == "Files/custom-bronze"


def test_development_runtime_defaults_do_not_select_historical_production_run() -> None:
    from datetime import date

    defaults = resolve_runtime_config(development_date=date(2026, 8, 3))
    assert defaults.ingestion_date == "2026-08-03"
    assert defaults.source_run_id == "dev-local"
    assert defaults.silver_run_id == "silver-dev-local-2026-08-03"


def test_results_are_deterministic_for_same_input_and_configuration() -> None:
    data = clean_dataset()
    data["regions"][0]["region_name"] = ""
    first = _run(data)
    second = _run(data)
    assert asdict(first) == asdict(second)


def test_accepted_quarantine_and_summary_counts_are_consistent() -> None:
    data = clean_dataset()
    data["equipment"][0]["equipment_type_id"] = 999
    output = _run(data)
    equipment = next(item for item in output.entities if item.entity == "equipment")
    assert equipment.summary.rows_read == 1
    assert equipment.summary.rows_accepted == 0
    assert equipment.summary.rows_quarantined == 1
    assert equipment.summary.critical_result_count == 2
    assert equipment.summary.warning_result_count == 0
    assert equipment.summary.info_result_count == 0
    assert equipment.summary.status == "FAILED"
    assert output.summary.rows_read == sum(item.summary.rows_read for item in output.entities)
    assert output.summary.rows_quarantined == 1
    assert output.summary.status == "PARTIAL_SUCCESS"
