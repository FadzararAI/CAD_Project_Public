#!/usr/bin/env python
"""
Convenience utility to launch multiple experiments in sequence.

Example::
    python scripts/batch_runner.py --memory-types ddr4,ddr5 --benchmarks tinyml
"""

from __future__ import annotations

import argparse
import itertools
import subprocess
import sys
from pathlib import Path
from typing import Dict, Iterable, List


DEFAULT_MEMORY_TYPES = ["ddr4", "ddr5", "hbm2"]
DEFAULT_BENCHMARKS = ["tinyml", "conv2d"]


def config_map(base_dir: Path) -> Dict[str, Path]:
    return {
        "ddr4": base_dir / "ddr4_config.py",
        "ddr5": base_dir / "ddr5_config.py",
        "hbm2": base_dir / "hbm2_config.py",
    }


def build_command(
    memory: str,
    benchmark: str,
    config_path: Path,
    results_dir: Path,
) -> List[str]:
    output_path = results_dir / memory / f"{benchmark}_{memory}.json"
    cmd = [
        sys.executable,
        str(Path(__file__).resolve().parent / "run_single_experiment.py"),
        "--memory-type",
        memory,
        "--benchmark",
        benchmark,
        "--config",
        str(config_path),
        "--output",
        str(output_path),
    ]
    return cmd


def run_batch(
    memories: Iterable[str],
    benchmarks: Iterable[str],
    configs_dir: Path,
    results_dir: Path,
) -> None:
    cfg = config_map(configs_dir)
    missing = [mem for mem in memories if mem not in cfg]
    if missing:
        raise ValueError(f"No config files for memory types: {', '.join(missing)}")

    combinations = list(itertools.product(memories, benchmarks))
    if not combinations:
        print("No experiments scheduled.")
        return

    results_dir.mkdir(parents=True, exist_ok=True)

    for memory, benchmark in combinations:
        config_path = cfg[memory]
        cmd = build_command(memory, benchmark, config_path, results_dir)
        print(f"[RUN] {memory} / {benchmark}")
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as exc:
            print(f"[FAIL] {memory}-{benchmark}: {exc}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Batch experiment runner")
    parser.add_argument(
        "--memory-types",
        default=",".join(DEFAULT_MEMORY_TYPES),
        help="Comma-separated memory types to run",
    )
    parser.add_argument(
        "--benchmarks",
        default=",".join(DEFAULT_BENCHMARKS),
        help="Comma-separated benchmark names to run",
    )
    parser.add_argument(
        "--configs-dir",
        default="configs",
        help="Directory containing memory configuration scripts",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Directory to store experiment outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    memories = [m.strip() for m in args.memory_types.split(",") if m.strip()]
    benchmarks = [b.strip() for b in args.benchmarks.split(",") if b.strip()]

    configs_dir = Path(args.configs_dir).resolve()
    results_dir = Path(args.results_dir).resolve()

    run_batch(
        memories=memories,
        benchmarks=benchmarks,
        configs_dir=configs_dir,
        results_dir=results_dir,
    )


if __name__ == "__main__":
    main()
