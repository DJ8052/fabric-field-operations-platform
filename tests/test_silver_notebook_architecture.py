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
