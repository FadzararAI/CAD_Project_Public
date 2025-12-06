#!/usr/bin/env python
"""
Create comparison plots for experiment metrics using aggregated JSON outputs.

Produces PNG figures grouped by benchmark, with memory types on the x-axis and
one figure per metric.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def find_latest_runs(input_dir: Path) -> Path | None:
    candidate = input_dir / "analysis" / "latest_runs.csv"
    if candidate.is_file():
        return candidate
    # Fall back to raw JSON aggregation if the CSV is missing.
    return None


def load_results(input_dir: Path) -> pd.DataFrame:
    csv_path = find_latest_runs(input_dir)
    if csv_path:
        return pd.read_csv(csv_path)

    from result_utils import load_results as load_json_results  # type: ignore

    records = load_json_results(input_dir)
    if not records:
        return pd.DataFrame()

    # Convert ResultRecord objects to dicts for DataFrame
    rows = []
    for rec in records:
        row = {
            "memory_type": rec.memory_type,
            "benchmark": rec.benchmark,
        }
        row.update(rec.metrics)
        rows.append(row)
    return pd.DataFrame(rows)


def metrics_to_plot(df: pd.DataFrame) -> List[str]:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    for col in ["memory_type", "benchmark"]:
        if col in numeric_cols:
            numeric_cols.remove(col)
    return numeric_cols


def sanitize(name: str) -> str:
    return name.replace(":", "_").replace("/", "_")


def make_plots(df: pd.DataFrame, output_dir: Path) -> List[Path]:
    created: List[Path] = []
    if df.empty:
        return created

    output_dir.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    metrics = metrics_to_plot(df)
    for benchmark in sorted(df["benchmark"].unique()):
        subset = df[df["benchmark"] == benchmark]
        for metric in metrics:
            metric_data = subset.dropna(subset=[metric])
            if metric_data.empty:
                continue

            plt.figure(figsize=(8, 5))
            sns.barplot(
                data=metric_data,
                x="memory_type",
                y=metric,
                ci="sd",
                estimator="mean",
            )
            plt.title(f"{benchmark} – {metric}")
            plt.xlabel("Memory type")
            plt.ylabel(metric.replace("_", " ").title())

            filename = sanitize(f"{benchmark}_{metric}.png")
            output_path = output_dir / filename
            plt.tight_layout()
            plt.savefig(output_path)
            plt.close()

            created.append(output_path)
    return created


def parse_args() -> argparse.Namespace:
    # Default to ../results relative to script location
    script_dir = Path(__file__).resolve().parent
    default_input = script_dir.parent / "results"
    default_output = default_input / "analysis" / "plots"

    parser = argparse.ArgumentParser(description="Generate comparison plots")
    parser.add_argument(
        "--input-dir",
        default=str(default_input),
        help="Directory containing experiment outputs",
    )
    parser.add_argument(
        "--output-dir",
        default=str(default_output),
        help="Directory for generated figures",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    df = load_results(input_dir)
    if df.empty:
        print(f"No results available under {input_dir}")
        return

    created = make_plots(df, output_dir)

    if not created:
        print("No plots were generated (missing metrics).")
    else:
        print(f"Generated {len(created)} plots in {output_dir}")


if __name__ == "__main__":
    main()
