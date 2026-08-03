"""Typed contracts for local and Fabric operational Silver validation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

SourceRecord = Mapping[str, Any]


@dataclass(frozen=True)
class Finding:
    """Internal rule failure/flag before approved metadata is attached."""

    entity: str
    record_index: int
    rule_id: str
    message: str


@dataclass(frozen=True)
class RuleMetadata:
    rule_id: str
    entity: str
    severity: str
    silver_action: str
    error_code: str


@dataclass(frozen=True)
class ValidationResult:
    run_id: str
    entity: str
    record_id: str
    rule_id: str
    error_code: str
    severity: str
    silver_action: str
    outcome: str
    message: str
    source_identifier: str
    source_record: dict[str, Any]
    validation_timestamp: datetime


@dataclass(frozen=True)
class QuarantineRecord:
    run_id: str
    entity: str
    record_id: str
    source_identifier: str
    source_record: dict[str, Any]
    critical_violations: tuple[ValidationResult, ...]
    all_results: tuple[ValidationResult, ...]


@dataclass(frozen=True)
class EntitySummary:
    entity: str
    rows_read: int
    rows_accepted: int
    rows_quarantined: int
    critical_result_count: int
    warning_result_count: int
    info_result_count: int
    duration_seconds: float
    status: str


@dataclass(frozen=True)
class EntityValidationOutput:
    entity: str
    accepted_records: tuple[dict[str, Any], ...]
    quarantine_records: tuple[QuarantineRecord, ...]
    validation_results: tuple[ValidationResult, ...]
    summary: EntitySummary


@dataclass(frozen=True)
class RunSummary:
    rows_read: int
    rows_accepted: int
    rows_quarantined: int
    critical_result_count: int
    warning_result_count: int
    info_result_count: int
    duration_seconds: float
    status: str


@dataclass(frozen=True)
class ValidationRunOutput:
    run_id: str
    entities: tuple[EntityValidationOutput, ...]
    summary: RunSummary

    @property
    def validation_results(self) -> tuple[ValidationResult, ...]:
        return tuple(result for entity in self.entities for result in entity.validation_results)
