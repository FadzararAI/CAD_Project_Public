#!/usr/bin/env python
"""Utility helpers for processing CAD project result files."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Dict, Iterable, List, Optional, Tuple

# Metrics captured by run_single_experiment.py JSON outputs.
DEFAULT_METRICS = [
    "sim_seconds",
    "execution_time",
    "avg_bandwidth",
    "avg_latency",
    "bytes_read",
    "bytes_written",
    "icache_miss_rate",
    "dcache_miss_rate",
]


@dataclass
class ResultRecord:
    """Container for a single experiment result."""

    memory_type: str
    benchmark: str
    metrics: Dict[str, float]
    source: Path


def discover_result_files(input_dir: Path) -> List[Path]:
    """Return all JSON result files under the provided directory."""
    if not input_dir.exists():
        return []
    return sorted([p for p in input_dir.rglob("*.json") if p.is_file()])


def _parse_single_record(payload: dict, json_path: Path) -> Optional[ResultRecord]:
    """Parse a single result record from a dict payload."""
    if not isinstance(payload, dict):
        return None

    memory_type = str(payload.get("memory_type", "unknown"))
    benchmark = str(payload.get("benchmark", "unknown"))
    metrics = {}

    # Extract all numeric values as metrics (not just predefined ones)
    for key, value in payload.items():
        if key in ("memory_type", "benchmark"):
            continue
        if isinstance(value, (int, float)):
            metrics[key] = float(value)

    return ResultRecord(memory_type, benchmark, metrics, json_path)


def load_results(input_dir: Path) -> List[ResultRecord]:
    """Load experiment results stored as JSON files."""
    records: List[ResultRecord] = []
    for json_path in discover_result_files(input_dir):
        try:
            payload = json.loads(json_path.read_text())
        except json.JSONDecodeError:
            # Skip files with invalid JSON while keeping traceability.
            continue

        # Handle both single object and array of objects
        if isinstance(payload, list):
            for item in payload:
                record = _parse_single_record(item, json_path)
                if record:
                    records.append(record)
        elif isinstance(payload, dict):
            record = _parse_single_record(payload, json_path)
            if record:
                records.append(record)
    return records


def group_records(
    records: Iterable[ResultRecord],
) -> Dict[Tuple[str, str], List[ResultRecord]]:
    """Group records by (memory_type, benchmark)."""
    grouped: Dict[Tuple[str, str], List[ResultRecord]] = defaultdict(list)
    for record in records:
        key = (record.memory_type, record.benchmark)
        grouped[key].append(record)
    return dict(grouped)


def _summarize_metric(values: List[float]) -> Dict[str, float]:
    """Return summary statistics for a single metric."""
    if not values:
        return {}
    summary: Dict[str, float] = {
        "mean": mean(values),
        "median": median(values),
        "min": min(values),
        "max": max(values),
    }
    summary["stdev"] = pstdev(values) if len(values) > 1 else 0.0
    return summary


def aggregate_statistics(
    grouped_records: Dict[Tuple[str, str], List[ResultRecord]],
    metrics: Optional[Iterable[str]] = None,
) -> List[Dict[str, float]]:
    """Compute summary statistics for each (memory_type, benchmark) tuple."""
    metrics = list(metrics) if metrics else DEFAULT_METRICS
    summaries: List[Dict[str, float]] = []

    for (memory_type, benchmark), records in sorted(grouped_records.items()):
        row: Dict[str, float] = {
            "memory_type": memory_type,
            "benchmark": benchmark,
            "samples": len(records),
        }
        for metric in metrics:
            values = [
                rec.metrics[metric]
                for rec in records
                if metric in rec.metrics
            ]
            stats = _summarize_metric(values)
            for suffix, value in stats.items():
                row[f"{metric}_{suffix}"] = value
        summaries.append(row)
    return summaries


def write_json(path: Path, payload: object) -> None:
    """Persist payload to JSON with standard formatting."""
    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def ensure_dir(path: Path) -> None:
    """Create directory if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)

