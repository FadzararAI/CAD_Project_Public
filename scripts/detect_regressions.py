#!/usr/bin/env python
"""Detect performance regressions by comparing baseline and current results."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from result_utils import (
    DEFAULT_METRICS,
    aggregate_statistics,
    group_records,
    load_results,
    write_json,
)

# Metrics where lower values indicate better performance.
LOWER_IS_BETTER = {"sim_seconds", "execution_time", "avg_latency"}
# Metrics where higher values indicate better performance.
HIGHER_IS_BETTER = {"avg_bandwidth"}


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare two result directories and flag regressions."
    )
    parser.add_argument(
        "--baseline",
        required=True,
        help="Directory containing baseline JSON result files",
    )
    parser.add_argument(
        "--current",
        required=True,
        help="Directory containing current JSON result files",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=["sim_seconds", "execution_time", "avg_bandwidth", "avg_latency"],
        help="Metrics to evaluate for regressions",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.05,
        help="Allowed relative degradation (fraction). Default is 0.05 (5%%).",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write a JSON report summarizing regressions",
    )
    return parser.parse_args(list(argv))


def summary_by_key(summary_rows: List[dict], metrics: Iterable[str]) -> Dict[Tuple[str, str], Dict[str, float]]:
    """Create lookup map for summary rows keyed by (memory_type, benchmark)."""
    lookup: Dict[Tuple[str, str], Dict[str, float]] = {}
    for row in summary_rows:
        key = (row["memory_type"], row["benchmark"])
        metric_means = {}
        for metric in metrics:
            value = row.get(f"{metric}_mean")
            if isinstance(value, (int, float)):
                metric_means[metric] = float(value)
        lookup[key] = metric_means
    return lookup


def detect_regressions(
    baseline_dir: Path,
    current_dir: Path,
    metrics: List[str],
    threshold: float,
) -> List[dict]:
    """Return regressions detected between baseline and current results."""
    baseline_records = load_results(baseline_dir)
    current_records = load_results(current_dir)
    if not baseline_records or not current_records:
        return []

    baseline_summary = aggregate_statistics(group_records(baseline_records), metrics)
    current_summary = aggregate_statistics(group_records(current_records), metrics)

    baseline_map = summary_by_key(baseline_summary, metrics)
    current_map = summary_by_key(current_summary, metrics)

    regressions: List[dict] = []

    common_keys = sorted(set(baseline_map.keys()) & set(current_map.keys()))
    for key in common_keys:
        baseline_metrics = baseline_map[key]
        current_metrics = current_map[key]
        for metric in metrics:
            baseline_value = baseline_metrics.get(metric)
            current_value = current_metrics.get(metric)
            if baseline_value in (None, 0):
                continue
            if current_value is None:
                continue

            if metric in LOWER_IS_BETTER:
                relative_change = (current_value - baseline_value) / baseline_value
                is_regression = relative_change > threshold
            elif metric in HIGHER_IS_BETTER:
                relative_change = (baseline_value - current_value) / baseline_value
                is_regression = relative_change > threshold
            else:
                # Fallback: treat higher as worse.
                relative_change = (current_value - baseline_value) / baseline_value
                is_regression = relative_change > threshold

            if is_regression:
                regressions.append(
                    {
                        "memory_type": key[0],
                        "benchmark": key[1],
                        "metric": metric,
                        "baseline": baseline_value,
                        "current": current_value,
                        "relative_change": relative_change,
                    }
                )
    return regressions


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    baseline_dir = Path(args.baseline)
    current_dir = Path(args.current)
    metrics = [metric for metric in args.metrics if metric in DEFAULT_METRICS]

    regressions = detect_regressions(baseline_dir, current_dir, metrics, args.threshold)
    if args.output:
        write_json(Path(args.output), {"regressions": regressions})

    if not regressions:
        print("No regressions detected.")
        return 0

    print("Regressions detected:")
    for entry in regressions:
        memory_type = entry["memory_type"]
        benchmark = entry["benchmark"]
        metric = entry["metric"]
        rel = entry["relative_change"] * 100
        print(
            f"  - {benchmark}/{memory_type}: {metric} degraded by {rel:.2f}% "
            f"(baseline={entry['baseline']:.4f}, current={entry['current']:.4f})"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
