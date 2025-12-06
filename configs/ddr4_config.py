#!/usr/bin/env python3
"""
DDR4 memory configuration for the CAD Memory Technology Study.

Creates a RISC-V O3CPU system backed by DRAMSim3 cycle-accurate DDR4 simulation.

Available DDR4 configurations (in dramsim3/configs/):
  - DDR4_8Gb_x8_2400: DDR4-2400 (tCK=0.83ns, CL=17)
  - DDR4_8Gb_x8_2666: DDR4-2666 (tCK=0.75ns, CL=19)
  - DDR4_8Gb_x8_3200: DDR4-3200 (tCK=0.63ns, CL=22)
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

# Available DDR4 speed grades
DDR4_CONFIGS = {
    "2400": "DDR4_8Gb_x8_2400.ini",
    "2666": "DDR4_8Gb_x8_2666.ini",
    "3200": "DDR4_8Gb_x8_3200.ini",
}
DEFAULT_DDR4_SPEED = "3200"


def get_dramsim3_config_path(config_name: str) -> str:
    """Get the full path to a DRAMSim3 config file.

    Prioritizes Docker-built DRAMSim3 configs to ensure compatibility
    with the compiled library version.
    """
    # Priority 1: gem5's integrated DRAMSim3 (built into Docker image)
    # This ensures config matches the compiled DRAMSim3 library version
    gem5_ext_config = Path("/opt/gem5/ext/dramsim3/DRAMsim3/configs") / config_name
    if gem5_ext_config.exists():
        return str(gem5_ext_config)

    # Priority 2: standalone DRAMSim3 installation in Docker
    system_config = Path("/opt/dramsim3/configs") / config_name
    if system_config.exists():
        return str(system_config)

    # Priority 3: project's dramsim3/configs directory (mounted at /workspace)
    project_config = PROJECT_ROOT / "dramsim3" / "configs" / config_name
    if project_config.exists():
        return str(project_config)

    # Fallback: local gem5's ext directory (for local development)
    gem5_config = PROJECT_ROOT / "gem5" / "ext" / "dramsim3" / "DRAMsim3" / "configs" / config_name
    if gem5_config.exists():
        return str(gem5_config)

    raise FileNotFoundError(f"DRAMSim3 config not found: {config_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run gem5 with DRAMSim3 DDR4 memory")
    parser.add_argument("binary", help="Path to the benchmark ELF binary")
    parser.add_argument("--cpu-clock", default="2GHz", help="CPU clock frequency")
    parser.add_argument("--mem-size", default="4GB", help="Total memory size")
    parser.add_argument(
        "--ddr4-speed",
        default=DEFAULT_DDR4_SPEED,
        choices=list(DDR4_CONFIGS.keys()),
        help=f"DDR4 speed grade (default: {DEFAULT_DDR4_SPEED})",
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
    config_name = DDR4_CONFIGS[args.ddr4_speed]
    config_path = get_dramsim3_config_path(config_name)

    # Set output directory for DRAMSim3 stats
    output_dir = args.dramsim3_output or os.path.join("m5out", "dramsim3_ddr4")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Using DRAMSim3 DDR4-{args.ddr4_speed} configuration: {config_path}")
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
