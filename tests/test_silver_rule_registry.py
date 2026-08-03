from __future__ import annotations

import re
from pathlib import Path

from operational_silver_validation.rule_registry import RULE_REGISTRY


MATRIX = Path(__file__).parents[1] / "docs" / "silver-validation-rule-mapping-matrix.md"


def _matrix_metadata() -> dict[str, tuple[str, str, str]]:
    metadata = {}
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        if not re.match(r"^\| (?:Region|Office|Employee|Project|Job Site|Crew|Activity|Field Schedule|Equipment Type|Equipment|Equipment Assignment|Safety Threshold|Cross-Entity) \|", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        metadata[cells[1]] = (cells[4], cells[5], cells[6])
    return metadata


def test_registry_ids_and_error_codes_are_unique() -> None:
    rules = tuple(RULE_REGISTRY.values())
    assert len(rules) == 65
    assert "FSD-008" not in RULE_REGISTRY
    assert len(rules) == len({rule.rule_id for rule in rules})
    assert len(rules) == len({rule.error_code for rule in rules})
    assert {rule.severity for rule in rules} <= {"Critical", "Warning", "Info"}


def test_every_implemented_rule_matches_approved_matrix_metadata() -> None:
    matrix = _matrix_metadata()
    assert len(matrix) == 66
    for rule_id, rule in RULE_REGISTRY.items():
        assert rule_id in matrix
        assert (rule.severity, rule.silver_action, rule.error_code) == matrix[rule_id]
