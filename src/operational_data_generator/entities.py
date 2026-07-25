"""
Entity generation functions for the Operational Data Generator.

Each function in this module creates one deterministic operational
source dataset. File writing and validation are handled elsewhere.
"""

from __future__ import annotations

from typing import Any

from .config import NUM_REGIONS


def generate_regions() -> list[dict[str, Any]]:
    """
    Generate deterministic Region records.

    Returns:
        A list of dictionaries, with one dictionary per Region.
    """
    region_names = [
        "North Texas",
        "Central Texas",
        "Gulf Coast",
        "West Texas",
    ]

    if NUM_REGIONS > len(region_names):
        raise ValueError(
            f"NUM_REGIONS cannot exceed {len(region_names)} "
            "without adding more approved region names."
        )

    regions: list[dict[str, Any]] = []

    for index in range(NUM_REGIONS):
        region_number = index + 1

        regions.append(
            {
                "region_id": region_number,
                "region_code": f"REG-{region_number:03d}",
                "region_name": region_names[index],
            }
        )

    return regions