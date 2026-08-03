"""Deterministic, Fabric-independent operational validation engine."""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable, Mapping, Sequence

from .entity_validations import ALL_ENTITIES, MASTER_ENTITIES, PRIMARY_KEYS, entity_findings
from .models import EntitySummary, EntityValidationOutput, RunSummary, ValidationResult, ValidationRunOutput
from .quarantine import build_quarantine_record
from .relationship_validations import relationship_findings
from .rule_registry import get_rule


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _record_id(entity: str, record: Mapping[str, Any], index: int) -> str:
    value = record.get(PRIMARY_KEYS[entity])
    return str(value) if value not in (None, "") else f"row:{index}"


def _validate_entities(dataset: Mapping[str, Sequence[Mapping[str, Any]]], run_id: str, entities: tuple[str, ...], *, source_identifiers: Mapping[str, str] | None, clock: Callable[[], datetime], timer: Callable[[], float]) -> ValidationRunOutput:
    missing = [entity for entity in entities if entity not in dataset]
    if missing:
        raise ValueError(f"dataset is missing required entities: {', '.join(missing)}")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be a non-empty string")
    run_started = timer()
    source_identifiers = source_identifiers or {}
    findings = [finding for entity in entities for finding in entity_findings(entity, dataset[entity])]
    findings.extend(relationship_findings(dataset, set(entities)))
    findings.sort(key=lambda item: (entities.index(item.entity), item.record_index, item.rule_id, item.message))
    timestamp = clock()
    by_record: dict[tuple[str, int], list[ValidationResult]] = defaultdict(list)
    for finding in findings:
        record = deepcopy(dict(dataset[finding.entity][finding.record_index]))
        metadata = get_rule(finding.rule_id)
        result = ValidationResult(
            run_id=run_id,
            entity=finding.entity,
            record_id=_record_id(finding.entity, record, finding.record_index),
            rule_id=metadata.rule_id,
            error_code=metadata.error_code,
            severity=metadata.severity,
            silver_action=metadata.silver_action,
            outcome="FAILED" if metadata.severity == "Critical" else "FLAGGED" if metadata.severity == "Warning" else "LOGGED",
            message=finding.message,
            source_identifier=source_identifiers.get(finding.entity, finding.entity),
            source_record=deepcopy(record),
            validation_timestamp=timestamp,
        )
        by_record[(finding.entity, finding.record_index)].append(result)
    outputs: list[EntityValidationOutput] = []
    for entity in entities:
        started = timer()
        accepted: list[dict[str, Any]] = []
        quarantined = []
        entity_results: list[ValidationResult] = []
        for index, source in enumerate(dataset[entity]):
            record = deepcopy(dict(source))
            results = tuple(by_record.get((entity, index), ()))
            entity_results.extend(results)
            if any(result.severity == "Critical" for result in results):
                quarantined.append(build_quarantine_record(
                    run_id=run_id, entity=entity, record_id=_record_id(entity, record, index),
                    source_identifier=source_identifiers.get(entity, entity), source_record=record, results=results,
                ))
            else:
                accepted.append(deepcopy(record))
        critical_count = sum(result.severity == "Critical" for result in entity_results)
        warning_count = sum(result.severity == "Warning" for result in entity_results)
        info_count = sum(result.severity == "Info" for result in entity_results)
        status = "FAILED" if quarantined and not accepted else "PARTIAL_SUCCESS" if quarantined else "SUCCEEDED"
        summary = EntitySummary(entity, len(dataset[entity]), len(accepted), len(quarantined), critical_count, warning_count, info_count, max(0.0, timer() - started), status)
        outputs.append(EntityValidationOutput(entity, tuple(accepted), tuple(quarantined), tuple(entity_results), summary))
    rows_read = sum(item.summary.rows_read for item in outputs)
    rows_accepted = sum(item.summary.rows_accepted for item in outputs)
    rows_quarantined = sum(item.summary.rows_quarantined for item in outputs)
    critical_count = sum(item.summary.critical_result_count for item in outputs)
    warning_count = sum(item.summary.warning_result_count for item in outputs)
    info_count = sum(item.summary.info_result_count for item in outputs)
    status = "FAILED" if rows_quarantined and not rows_accepted else "PARTIAL_SUCCESS" if rows_quarantined else "SUCCEEDED"
    summary = RunSummary(rows_read, rows_accepted, rows_quarantined, critical_count, warning_count, info_count, max(0.0, timer() - run_started), status)
    return ValidationRunOutput(run_id, tuple(outputs), summary)


def validate_master_entities(dataset: Mapping[str, Sequence[Mapping[str, Any]]], run_id: str, *, source_identifiers: Mapping[str, str] | None = None, clock: Callable[[], datetime] = _utc_now, timer: Callable[[], float] = perf_counter) -> ValidationRunOutput:
    """Validate the original master-entity slice; retained as a stable public API."""
    return _validate_entities(dataset, run_id, MASTER_ENTITIES, source_identifiers=source_identifiers, clock=clock, timer=timer)


def validate_operational_entities(dataset: Mapping[str, Sequence[Mapping[str, Any]]], run_id: str, *, source_identifiers: Mapping[str, str] | None = None, clock: Callable[[], datetime] = _utc_now, timer: Callable[[], float] = perf_counter) -> ValidationRunOutput:
    """Validate all 12 implemented operational entities in deterministic order."""
    return _validate_entities(dataset, run_id, ALL_ENTITIES, source_identifiers=source_identifiers, clock=clock, timer=timer)
