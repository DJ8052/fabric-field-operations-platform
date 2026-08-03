"""Auditable quarantine construction."""

from __future__ import annotations

from copy import deepcopy

from .models import QuarantineRecord, ValidationResult


def build_quarantine_record(*, run_id: str, entity: str, record_id: str, source_identifier: str, source_record: dict, results: tuple[ValidationResult, ...]) -> QuarantineRecord:
    critical = tuple(result for result in results if result.severity == "Critical")
    if not critical:
        raise ValueError("Quarantine requires at least one Critical result")
    return QuarantineRecord(run_id, entity, record_id, source_identifier, deepcopy(source_record), critical, results)
