#!/usr/bin/env python
"""Generate a Markdown performance report from experiment outputs."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from result_utils import (
    DEFAULT_METRICS,
    aggregate_statistics,
    ensure_dir,
    group_records,
    load_results,
)

# Metrics to highlight in the report.
PRIMARY_METRICS = ["sim_seconds", "avg_bandwidth", "avg_latency"]


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Markdown performance report.")
    parser.add_argument(
        "--input-dir",
        default="results",
        help="Directory containing raw result JSON files (default: results)",
    )
    parser.add_argument(
        "--output",
        default="results/analysis/report.md",
        help="Output Markdown file (default: results/analysis/report.md)",
    )
    parser.add_argument(
        "--metrics",
        nargs="+",
        default=PRIMARY_METRICS,
        help="Metrics to include in report tables (default: sim_seconds avg_bandwidth avg_latency)",
    )
    return parser.parse_args(list(argv))


def best_by_metric(
    summaries: List[dict], metrics: Iterable[str]
) -> Dict[Tuple[str, str], dict]:
    """Return best-performing configurations per benchmark/metric."""
    best: Dict[Tuple[str, str], dict] = {}
    for row in summaries:
        benchmark = row["benchmark"]
        for metric in metrics:
            mean_key = f"{metric}_mean"
            value = row.get(mean_key)
            if not isinstance(value, (int, float)):
                continue
            key = (benchmark, metric)
            current = best.get(key)
            if current is None:
                best[key] = {"row": row, "value": value}
                continue
            better = value < current["value"] if metric != "avg_bandwidth" else value > current["value"]
            if better:
                best[key] = {"row": row, "value": value}
    return best


def format_table(summaries: List[dict], metrics: List[str]) -> str:
    """Convert summary statistics into a Markdown table."""
    headers = ["Benchmark", "Memory Type", "Samples"] + [f"{metric} (mean)" for metric in metrics]
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join([" --- " for _ in headers]) + "|")
    for row in summaries:
        values = [
            row["benchmark"],
            row["memory_type"],
            str(row["samples"]),
        ]
        for metric in metrics:
            value = row.get(f"{metric}_mean")
            values.append(f"{value:.4f}" if isinstance(value, (int, float)) else "n/a")
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def build_report(
    summaries: List[dict],
    metrics: List[str],
    source_dir: Path,
) -> str:
    timestamp = dt.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = [
        "# Memory Technology Performance Report",
        "",
        f"_Generated on {timestamp} from `{source_dir}`._",
        "",
    ]

    if not summaries:
        lines.append("No result files were found; report is empty.")
        return "\n".join(lines)

    lines.append("## Aggregated Metrics")
    lines.append("")
    lines.append(format_table(summaries, metrics))
    lines.append("")

    lines.append("## Highlights")
    lines.append("")
    best_entries = best_by_metric(summaries, metrics)
    for (benchmark, metric), entry in sorted(best_entries.items()):
        row = entry["row"]
        value = entry["value"]
        lines.append(
            f"- **{benchmark}** best `{metric}` with `{row['memory_type']}` ({value:.4f})"
        )
    lines.append("")

    lines.append("## Notes")
    lines.append("- Lower `sim_seconds` and `avg_latency` indicate better performance.")
    lines.append("- Higher `avg_bandwidth` indicates better throughput.")
    lines.append("- Samples column reflects the number of result files ingested per configuration.")
    return "\n".join(lines)


def main(argv: Iterable[str]) -> int:
    args = parse_args(argv)
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)
    metrics = [metric for metric in args.metrics if metric in DEFAULT_METRICS]

    records = load_results(input_dir)
    grouped = group_records(records)
    summaries = aggregate_statistics(grouped, metrics)

    ensure_dir(output_path.parent)
    report = build_report(summaries, metrics, input_dir)
    output_path.write_text(report)
    print(f"Wrote Markdown report to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
