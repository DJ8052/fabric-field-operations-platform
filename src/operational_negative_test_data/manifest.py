"""Authoritative scenario and expected-result manifest for negative acceptance."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from operational_silver_validation.rule_registry import get_rule


@dataclass(frozen=True)
class NegativeScenario:
    scenario_id: str
    entity: str
    record_ids: tuple[str, ...]
    rule_ids: tuple[str, ...]
    severity: str
    expected_disposition: str
    mutation: str


NEGATIVE_SCENARIOS = (
    NegativeScenario(
        "warning_region_name_missing",
        "regions",
        ("1",),
        ("REG-003",),
        "Warning",
        "Accept and log",
        "Set region_name to the empty string.",
    ),
    NegativeScenario(
        "info_equipment_assignment_adjacent",
        "equipment_assignments",
        ("1", "81"),
        ("EQA-004",),
        "Info",
        "Accept and log",
        "Set assignment 81 to start exactly when assignment 1 ends.",
    ),
    NegativeScenario(
        "critical_job_site_weather_location",
        "job_sites",
        ("1",),
        ("JBS-004", "XEN-007"),
        "Critical",
        "Quarantine and log",
        "Set weather_location_code to TX-UNKNOWN.",
    ),
    NegativeScenario(
        "critical_equipment_assignment_overlap",
        "equipment_assignments",
        ("2", "82"),
        ("EQA-003", "XEN-005"),
        "Critical",
        "Quarantine and log",
        "Move assignment 82 into assignment 2's active period.",
    ),
)


def _expected_findings() -> tuple[dict[str, str], ...]:
    findings: list[dict[str, str]] = []
    for scenario in NEGATIVE_SCENARIOS:
        for record_id in scenario.record_ids:
            for rule_id in scenario.rule_ids:
                rule = get_rule(rule_id)
                if rule.severity != scenario.severity:
                    raise RuntimeError(
                        f"Scenario {scenario.scenario_id} severity does not match {rule_id}"
                    )
                findings.append({
                    "scenario_id": scenario.scenario_id,
                    "entity": scenario.entity,
                    "record_id": record_id,
                    "rule_id": rule.rule_id,
                    "error_code": rule.error_code,
                    "severity": rule.severity,
                    "silver_action": rule.silver_action,
                    "expected_disposition": scenario.expected_disposition,
                })
    return tuple(findings)


EXPECTED_FINDINGS = _expected_findings()
EXPECTED_SUMMARY = {
    "rows_read": 921,
    "rows_accepted": 918,
    "rows_quarantined": 3,
    "critical_result_count": 6,
    "warning_result_count": 1,
    "info_result_count": 2,
}


def expected_manifest() -> dict[str, Any]:
    """Return a JSON-serializable copy of the acceptance contract."""
    return {
        "manifest_version": 1,
        "dataset_type": "operational_silver_negative_acceptance",
        "scenarios": [
            {**asdict(scenario), "record_ids": list(scenario.record_ids), "rule_ids": list(scenario.rule_ids)}
            for scenario in NEGATIVE_SCENARIOS
        ],
        "expected_findings": [dict(finding) for finding in EXPECTED_FINDINGS],
        "expected_summary": dict(EXPECTED_SUMMARY),
        "deferred_rules": ["FSD-008"],
    }
