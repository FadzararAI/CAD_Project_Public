#!/usr/bin/env python3
"""
HBM2 memory configuration for the CAD Memory Technology Study.

Creates a RISC-V O3CPU system backed by DRAMSim3 cycle-accurate HBM2 simulation.

Available HBM2 configurations (in dramsim3/configs/):
  - HBM2_4Gb_x128: HBM2 4Gb per die, 8 channels, 128-bit width (4GB total)
  - HBM2_8Gb_x128: HBM2 8Gb per die, 8 channels, 128-bit width (8GB total)
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

# Available HBM2 configurations
HBM2_CONFIGS = {
    "4Gb": "HBM2_4Gb_x128.ini",
    "8Gb": "HBM2_8Gb_x128.ini",
}
DEFAULT_HBM2_DENSITY = "8Gb"


def get_dramsim3_config_path(config_name: str) -> str:
    """Get the full path to a DRAMSim3 HBM2 config file.

    Prioritizes Docker-built DRAMSim3 configs to ensure compatibility
    with the compiled library version.
    """
    # Priority 1: gem5's integrated DRAMSim3 (built into Docker image)
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

    raise FileNotFoundError(f"DRAMSim3 HBM2 config not found: {config_name}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run gem5 with DRAMSim3 HBM2 memory")
    parser.add_argument("binary", help="Path to the benchmark ELF binary")
    parser.add_argument("--cpu-clock", default="2GHz", help="CPU clock frequency")
    parser.add_argument("--mem-size", default="4GB", help="Total memory size")
    parser.add_argument(
        "--hbm2-density",
        default=DEFAULT_HBM2_DENSITY,
        choices=list(HBM2_CONFIGS.keys()),
        help=f"HBM2 die density (default: {DEFAULT_HBM2_DENSITY})",
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
    config_name = HBM2_CONFIGS[args.hbm2_density]
    config_path = get_dramsim3_config_path(config_name)

    # Set output directory for DRAMSim3 stats
    output_dir = args.dramsim3_output or os.path.join("m5out", "dramsim3_hbm2")
    os.makedirs(output_dir, exist_ok=True)

    print(f"Using DRAMSim3 HBM2-{args.hbm2_density} configuration: {config_path}")
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
