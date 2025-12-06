#!/usr/bin/env python3
"""
DDR5 memory configuration for the CAD Memory Technology Study.

Creates a RISC-V O3CPU system backed by DRAMSim3 cycle-accurate DDR5 simulation.

Available DDR5 configurations (in configs/dramsim3/ddr5/):
  - DDR5_16Gb_x8_4800: DDR5-4800 (tCK=417ps, CL=40)
  - DDR5_16Gb_x8_5600: DDR5-5600 (tCK=357ps, CL=46)
  - DDR5_16Gb_x8_6400: DDR5-6400 (tCK=312ps, CL=52)
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

from m5.objects import DRAMsim3

from riscv_cpu import create_riscv_system, run_simulation

# Available DDR5 speed grades (custom project configs)
DDR5_CONFIGS = {
    "4800": "DDR5_16Gb_x8_4800.ini",
    "5600": "DDR5_16Gb_x8_5600.ini",
    "6400": "DDR5_16Gb_x8_6400.ini",
}
DEFAULT_DDR5_SPEED = "6400"


def get_dramsim3_config_path(config_name: str) -> str:
    """Get the full path to a DRAMSim3 DDR5 config file.

    Note: DDR5 configs are custom (not in standard DRAMSim3), so we
    prioritize the project's custom configs directory.
    """
    # Priority 1: project's custom DDR5 configs (DDR5 not in standard DRAMSim3)
    project_config = PROJECT_ROOT / "configs" / "dramsim3" / "ddr5" / config_name
    if project_config.exists():
        return str(project_config)

    # Priority 2: gem5's integrated DRAMSim3 (in case DDR5 is added upstream)
    gem5_ext_config = Path("/opt/gem5/ext/dramsim3/DRAMsim3/configs") / config_name
    if gem5_ext_config.exists():
        return str(gem5_ext_config)

    # Priority 3: standalone DRAMSim3 installation
    system_config = Path("/opt/dramsim3/configs") / config_name
    if system_config.exists():
        return str(system_config)

    # Fallback: project's dramsim3/configs directory
    dramsim3_config = PROJECT_ROOT / "dramsim3" / "configs" / config_name
    if dramsim3_config.exists():
        return str(dramsim3_config)

    raise FileNotFoundError(f"DRAMSim3 DDR5 config not found: {config_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run gem5 with DRAMSim3 DDR5 memory")
    parser.add_argument("binary", help="Path to the benchmark ELF binary")
    parser.add_argument("--cpu-clock", default="2GHz", help="CPU clock frequency")
    parser.add_argument("--mem-size", default="4GB", help="Total memory size")
    parser.add_argument(
        "--ddr5-speed",
        default=DEFAULT_DDR5_SPEED,
        choices=list(DDR5_CONFIGS.keys()),
        help=f"DDR5 speed grade (default: {DEFAULT_DDR5_SPEED})",
    )
    parser.add_argument(
        "--dramsim3-output",
        default=None,
        help="Output directory for DRAMSim3 stats (default: gem5 output dir)",
    )
    parser.add_argument(
        "--max-ticks", type=int, default=None, help="Optional maximum tick limit"
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Get DRAMSim3 config file path
    config_name = DDR5_CONFIGS[args.ddr5_speed]
    config_path = get_dramsim3_config_path(config_name)

    # Set output directory for DRAMSim3 stats
    output_dir = args.dramsim3_output or os.path.join("m5out", "dramsim3_ddr5")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Using DRAMSim3 DDR5-{args.ddr5_speed} configuration: {config_path}")
    print(f"DRAMSim3 output directory: {output_dir}")

    # Create DRAMSim3 memory controller
    mem_ctrl = DRAMsim3(configFile=config_path, filePath=output_dir)

    system = create_riscv_system(
        binary_path=args.binary,
        memory_controller=mem_ctrl,
        cpu_clock=args.cpu_clock,
        mem_size=args.mem_size,
    )

    run_simulation(system, max_ticks=args.max_ticks)


if __name__ == "__m5_main__":
    main()
