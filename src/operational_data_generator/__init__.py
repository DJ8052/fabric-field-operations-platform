"""Deterministic synthetic operational-data generator."""

from pathlib import Path
from typing import Any

from .validators import ValidationError, validate_dataset


def generate_dataset() -> dict[str, list[dict[str, Any]]]:
    """Generate accepted data without importing the CLI during package startup."""
    from .generator import generate_dataset as _generate_dataset

    return _generate_dataset()


def run(output_root: Path, run_id: str = "accepted_20260101") -> dict[str, Path]:
    """Generate, validate, and write accepted operational CSV files."""
    from .generator import run as _run

    return _run(output_root, run_id)


__all__ = ["ValidationError", "generate_dataset", "run", "validate_dataset"]
