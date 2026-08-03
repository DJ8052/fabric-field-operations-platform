"""Generate deterministic source CSVs for Operational Silver negative acceptance."""

from __future__ import annotations

import argparse
from pathlib import Path

from operational_negative_test_data import (
    NEGATIVE_SCENARIOS,
    generate_negative_acceptance_dataset,
    write_negative_acceptance_dataset,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/negative_acceptance/operations"),
    )
    args = parser.parse_args()
    dataset = generate_negative_acceptance_dataset()
    paths, manifest_path = write_negative_acceptance_dataset(dataset, args.output_root)
    print(f"Wrote {sum(len(rows) for rows in dataset.values())} rows across {len(paths)} CSVs")
    for scenario in NEGATIVE_SCENARIOS:
        print(
            f"{scenario.scenario_id}: entity={scenario.entity}, "
            f"records={','.join(scenario.record_ids)}, rules={','.join(scenario.rule_ids)}"
        )
    print(f"Expected-results manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
