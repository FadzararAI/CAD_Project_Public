#!/usr/bin/env python3
"""
DDR5 memory configuration using gem5's built-in DDR5 model.

This configuration uses gem5's native DDR5_4400_4x8 DRAM interface instead of
DRAMSim3, since DRAMSim3 does not support DDR5 protocol natively.

Note: gem5's built-in DRAM model provides fewer detailed metrics compared to
DRAMSim3. Specifically, row buffer hit rate statistics are not available.

Available metrics with gem5 built-in DRAM:
  - Execution time (sim_seconds)
  - Average bandwidth (bw_read, bw_write)
  - Basic latency statistics

NOT available (compared to DRAMSim3):
  - Row buffer hit rate
  - Detailed bank-level statistics
  - Power consumption breakdown
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Add configs directory to Python path for imports
CONFIGS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CONFIGS_DIR.parent
if str(CONFIGS_DIR) not in sys.path:
    sys.path.insert(0, str(CONFIGS_DIR))

from m5.objects import DDR5_4400_4x8

from riscv_cpu import create_riscv_system, run_simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run gem5 with built-in DDR5 memory model"
    )
    parser.add_argument("binary", help="Path to the benchmark ELF binary")
    parser.add_argument("--cpu-clock", default="2GHz", help="CPU clock frequency")
    parser.add_argument("--mem-size", default="4GB", help="Total memory size")
    parser.add_argument(
        "--max-ticks", type=int, default=None, help="Optional maximum tick limit"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("Using gem5 built-in DDR5_4400_4x8 memory model")
    print("Note: Row buffer hit rate metrics are NOT available with this model")

    # Create gem5 built-in DDR5 memory interface
    mem_ctrl = DDR5_4400_4x8()

    system = create_riscv_system(
        binary_path=args.binary,
        memory_controller=mem_ctrl,
        cpu_clock=args.cpu_clock,
        mem_size=args.mem_size,
    )

    run_simulation(system, max_ticks=args.max_ticks)


if __name__ == "__m5_main__":
    main()
