#!/usr/bin/env python
"""
Aggregate metrics from experiment result JSON files and emit summary tables.

Outputs include:
  * latest_runs.csv  - raw concatenated metrics per experiment
  * summary_metrics.csv - aggregate statistics (mean/min/max/std) by benchmark/memory
  * summary.txt - human-readable recap of key figures
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, List

from result_utils import (
    DEFAULT_METRICS,
    aggregate_statistics,
    ensure_dir,
    load_results,
    group_records,
    write_json,
)


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    # Default to ../results relative to script location
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "results"
    default_output = default_input / "analysis"

    parser = argparse.ArgumentParser(description="Analyze experiment results.")
    parser.add_argument(
        "--input-dir",
        default=str(default_input),
        help="Directory containing raw result JSON files (default: ../results)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output),
        help="Directory where analysis artifacts are written (default: ../results/analysis)",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=DEFAULT_METRICS,
        help="Metrics to include in the analysis (default: all known metrics)",
    )
    parser.add_argument(
        "--csv",
        default="summary.csv",
        help="Filename for CSV summary (default: summary.csv)",
    )
    parser.add_argument(
        "--json",
        default="summary.json",
        help="Filename for JSON summary (default: summary.json)",
    )
    return parser.parse_args(list(argv))


def write_csv(path: Path, rows: List[dict]) -> None:
    """Dump aggregated statistics to CSV."""
    if not rows:
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)

    records = load_results(input_dir)
    if not records:
        print(f"No result files found in {input_dir}", file=sys.stderr)
        return 1

    grouped = group_records(records)
    summaries = aggregate_statistics(grouped, args.metrics)

    ensure_dir(output_dir)

    json_path = output_dir / args.json
    csv_path = output_dir / args.csv
    write_json(json_path, summaries)
    write_csv(csv_path, summaries)

    print(f"Wrote JSON summary to {json_path}")
    print(f"Wrote CSV summary to {csv_path}")
    print("Top-level aggregates:")
    for row in summaries:
        memory_type = row["memory_type"]
        benchmark = row["benchmark"]
        samples = row["samples"]
        sim = row.get("sim_seconds_mean")
        bandwidth = row.get("avg_bandwidth_mean")
        latency = row.get("avg_latency_mean")
        def _format(value: object) -> str:
            return f"{value:.4f}" if isinstance(value, (int, float)) else "n/a"
        print(
            f"  - {benchmark}/{memory_type}: samples={samples}, "
            f"sim_seconds={_format(sim)} avg_bandwidth={_format(bandwidth)}GB/s "
            f"avg_latency={_format(latency)}ns"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
