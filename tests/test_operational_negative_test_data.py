from __future__ import annotations

import csv
import hashlib
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from operational_bronze_ingestion import ENTITY_CONFIGS, ingest_all
from operational_data_generator import generate_dataset
from operational_data_generator.config import GENERATION_ORDER, TARGET_COUNTS
from operational_negative_test_data import (
    EXPECTED_FINDINGS,
    EXPECTED_SUMMARY,
    NEGATIVE_SCENARIOS,
    generate_negative_acceptance_dataset,
    write_negative_acceptance_dataset,
)
from operational_silver_validation import RULE_REGISTRY, validate_operational_entities


FIXED_TIME = datetime(2026, 8, 3, 12, tzinfo=timezone.utc)
ROOT = Path(__file__).parents[1]


def _by_id(dataset: dict, entity: str, key: str, value: int) -> dict:
    return next(row for row in dataset[entity] if row[key] == value)


def _checksums(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.iterdir())
        if path.is_file()
    }


def test_factory_preserves_all_entities_headers_and_clean_source() -> None:
    clean = generate_dataset()
    snapshot = deepcopy(clean)
    negative = generate_negative_acceptance_dataset(lambda: clean)
    assert clean == snapshot
    assert tuple(negative) == GENERATION_ORDER
    assert {name: len(rows) for name, rows in negative.items()} == TARGET_COUNTS
    for name, rows in negative.items():
        assert set(ENTITY_CONFIGS[name].required_columns) <= set(rows[0])
        assert all(tuple(row) == tuple(rows[0]) for row in rows)


def test_scenarios_are_stable_and_each_controlled_mutation_exists_once() -> None:
    dataset = generate_negative_acceptance_dataset()
    assert len({scenario.scenario_id for scenario in NEGATIVE_SCENARIOS}) == len(NEGATIVE_SCENARIOS)
    assert _by_id(dataset, "regions", "region_id", 1)["region_name"] == ""
    assert _by_id(dataset, "job_sites", "job_site_id", 1)["weather_location_code"] == "TX-UNKNOWN"

    assignments = {row["assignment_id"]: row for row in dataset["equipment_assignments"]}
    assert assignments[1]["equipment_id"] == assignments[81]["equipment_id"]
    assert assignments[1]["assignment_end_timestamp"] == assignments[81]["assignment_start_timestamp"]
    assert assignments[2]["equipment_id"] == assignments[82]["equipment_id"]
    assert assignments[2]["assignment_start_timestamp"] < assignments[82]["assignment_end_timestamp"]
    assert assignments[82]["assignment_start_timestamp"] < assignments[2]["assignment_end_timestamp"]
    assert {1, 81}.isdisjoint({2, 82})


def test_manifest_metadata_matches_registry_and_mapping_matrix() -> None:
    matrix = (ROOT / "docs" / "silver-validation-rule-mapping-matrix.md").read_text(encoding="utf-8")
    for finding in EXPECTED_FINDINGS:
        rule = RULE_REGISTRY[finding["rule_id"]]
        assert finding["error_code"] == rule.error_code
        assert finding["severity"] == rule.severity
        assert finding["silver_action"] == rule.silver_action
        matching_rows = [line for line in matrix.splitlines() if f"| {rule.rule_id} |" in line]
        assert len(matching_rows) == 1
        assert rule.error_code in matching_rows[0]
        assert f"| {rule.severity} |" in matching_rows[0]
        assert rule.silver_action in matching_rows[0]


def test_writer_is_deterministic_and_bronze_can_structurally_ingest(tmp_path: Path) -> None:
    dataset = generate_negative_acceptance_dataset()
    first, second = tmp_path / "first", tmp_path / "second"
    first_paths, first_manifest = write_negative_acceptance_dataset(dataset, first)
    write_negative_acceptance_dataset(dataset, second)
    assert _checksums(first) == _checksums(second)
    assert len(first_paths) == 12
    assert first_manifest.name == "expected-results.json"
    for name, path in first_paths.items():
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            assert set(ENTITY_CONFIGS[name].required_columns) <= set(reader.fieldnames or ())
            assert sum(1 for _ in reader) == TARGET_COUNTS[name]
    results = ingest_all(first_paths, "2026-01-01", "negative-acceptance", bronze_root=str(tmp_path / "bronze"))
    assert len(results) == 12
    assert sum(result.row_count for result in results) == 921


def test_negative_dataset_matches_manifest_end_to_end_without_source_changes() -> None:
    dataset = generate_negative_acceptance_dataset()
    snapshot = deepcopy(dataset)
    output = validate_operational_entities(
        dataset,
        "negative-acceptance",
        clock=lambda: FIXED_TIME,
        timer=lambda: 1.0,
    )
    actual = {
        (result.entity, result.record_id, result.rule_id, result.error_code, result.severity)
        for result in output.validation_results
    }
    expected = {
        (item["entity"], item["record_id"], item["rule_id"], item["error_code"], item["severity"])
        for item in EXPECTED_FINDINGS
    }
    assert actual == expected
    for field, value in EXPECTED_SUMMARY.items():
        assert getattr(output.summary, field) == value

    disposition = {
        (entity.entity, record.record_id): "Quarantine"
        for entity in output.entities
        for record in entity.quarantine_records
    }
    accepted = {
        (entity.entity, str(record[next(key for key in record if key.endswith("_id"))]))
        for entity in output.entities
        for record in entity.accepted_records
    }
    assert disposition == {
        ("job_sites", "1"): "Quarantine",
        ("equipment_assignments", "2"): "Quarantine",
        ("equipment_assignments", "82"): "Quarantine",
    }
    assert ("regions", "1") in accepted
    assert ("equipment_assignments", "1") in accepted
    assert ("equipment_assignments", "81") in accepted
    assert dataset == snapshot


def test_bronze_notebook_source_root_is_parameterized_with_clean_default() -> None:
    source = (ROOT / "notebooks" / "NB_Operational_Bronze_Ingestion.py").read_text(encoding="utf-8")
    assert 'DEFAULT_SOURCE_ROOT = "Files/source/operations"' in source
    assert 'globals().get("source_root")' in source
    assert "source_paths(SOURCE_ROOT)" in source or "source_paths()" in source
