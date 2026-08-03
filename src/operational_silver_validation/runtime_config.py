"""Restrained runtime configuration for local and Fabric notebook execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping

DEVELOPMENT_SOURCE_RUN_ID = "dev-local"
DEFAULT_BRONZE_ROOT = "Files/bronze/operations"
DEFAULT_SILVER_ROOT = "Tables/silver/operations"
DEFAULT_QUARANTINE_ROOT = "Tables/quarantine/operations"
DEFAULT_VALIDATION_RESULTS_ROOT = "Tables/validation/operational_results"


@dataclass(frozen=True)
class SilverRuntimeConfig:
    ingestion_date: str
    source_run_id: str
    silver_run_id: str
    bronze_root: str
    silver_root: str
    quarantine_root: str
    validation_results_root: str


def _value(parameters: Mapping[str, Any], name: str, default: str) -> str:
    supplied = parameters.get(name)
    if supplied is None:
        return default
    if not isinstance(supplied, str) or not supplied.strip():
        raise ValueError(f"{name} must be a non-empty string when supplied")
    return supplied.strip()


def resolve_runtime_config(parameters: Mapping[str, Any] | None = None, *, development_date: date | None = None) -> SilverRuntimeConfig:
    """Resolve pipeline values first, falling back to clearly scoped dev defaults."""
    values = parameters or {}
    ingestion_date = _value(values, "ingestion_date", (development_date or date.today()).isoformat())
    try:
        date.fromisoformat(ingestion_date)
    except ValueError as exc:
        raise ValueError("ingestion_date must use ISO YYYY-MM-DD format") from exc
    source_run_id = _value(values, "source_run_id", DEVELOPMENT_SOURCE_RUN_ID)
    silver_run_id = _value(values, "silver_run_id", f"silver-{source_run_id}-{ingestion_date}")
    return SilverRuntimeConfig(
        ingestion_date=ingestion_date,
        source_run_id=source_run_id,
        silver_run_id=silver_run_id,
        bronze_root=_value(values, "bronze_root", DEFAULT_BRONZE_ROOT),
        silver_root=_value(values, "silver_root", DEFAULT_SILVER_ROOT),
        quarantine_root=_value(values, "quarantine_root", DEFAULT_QUARANTINE_ROOT),
        validation_results_root=_value(values, "validation_results_root", DEFAULT_VALIDATION_RESULTS_ROOT),
    )
