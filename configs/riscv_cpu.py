# Copyright (c) 2025
# CAD Memory Technology Study - RISC-V CPU configuration helpers
#
# Provides utility routines to assemble a RISC-V O3CPU system with a
# two-level cache hierarchy. The individual memory configuration scripts
# can import the helper functions in this module to avoid duplicating the
# CPU and cache setup logic.

"""
Helper utilities for building a RISC-V O3CPU system for gem5 experiments.

The create_riscv_system() function wires together:
  * O3CPU with simple private L1 caches and a shared L2
  * SystemXBar / L2XBar interconnect
  * A caller-provided memory controller (DRAMSim3 or gem5 built-in DRAM interface)

Example usage with DRAMSim3::

    from riscv_cpu import create_riscv_system, run_simulation
    from m5.objects import DRAMsim3

    dram = DRAMsim3(configFile="path/to/config.ini", filePath="output/dir")
    system = create_riscv_system(binary_path="/path/to/app.elf",
                                 memory_controller=dram,
                                 mem_size="4GB")
    run_simulation(system)

Example usage with gem5 built-in DRAM::

    from riscv_cpu import create_riscv_system, run_simulation
    from m5.objects import DDR4_2400_16x4

    dram = DDR4_2400_16x4()
    system = create_riscv_system(binary_path="/path/to/app.elf",
                                 memory_controller=dram,
                                 mem_size="4GB")
    run_simulation(system)
"""

from __future__ import annotations

from typing import Optional

import m5
from m5.objects import (
    AddrRange,
    Cache,
    DRAMsim3,
    L2XBar,
    MemCtrl,
    O3CPU,
    Process,
    Root,
    SEWorkload,
    SrcClockDomain,
    System,
    SystemXBar,
    VoltageDomain,
)


class L1ICache(Cache):
    """Minimal instruction cache definition."""

    assoc = 2
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 4
    tgts_per_mshr = 16

    def connect_cpu(self, cpu: O3CPU) -> None:
        self.cpu_side = cpu.icache_port

    def connect_bus(self, bus: L2XBar) -> None:
        self.mem_side = bus.cpu_side_ports


class L1DCache(Cache):
    """Minimal data cache definition."""

    assoc = 4
    tag_latency = 2
    data_latency = 2
    response_latency = 2
    mshrs = 16
    tgts_per_mshr = 16

    def connect_cpu(self, cpu: O3CPU) -> None:
        self.cpu_side = cpu.dcache_port

    def connect_bus(self, bus: L2XBar) -> None:
        self.mem_side = bus.cpu_side_ports


class L2Cache(Cache):
    """Shared L2 cache sitting between the private L1s and the memory bus."""

    assoc = 8
    tag_latency = 12
    data_latency = 12
    response_latency = 12
    mshrs = 32
    tgts_per_mshr = 16

    def connect_cpu_side(self, bus: L2XBar) -> None:
        self.cpu_side = bus.mem_side_ports

    def connect_mem_side(self, bus: SystemXBar) -> None:
        self.mem_side = bus.cpu_side_ports


def _configure_cache_sizes(
    cpu: O3CPU, l1i_size: str, l1d_size: str, l2_size: str, l2: L2Cache
) -> None:
    cpu.icache.size = l1i_size
    cpu.dcache.size = l1d_size
    l2.size = l2_size


def create_riscv_system(
    binary_path: str,
    memory_controller,
    *,
    cpu_clock: str = "2GHz",
    cpu_voltage: str = "1.0V",
    mem_size: str = "4GB",
    l1i_size: str = "32kB",
    l1d_size: str = "32kB",
    l2_size: str = "1MB",
) -> System:
    """
    Assemble a RISC-V system suitable for syscall emulation (SE) mode runs.

    Args:
        binary_path: Path to the RISC-V binary to execute.
        memory_controller: A configured gem5 DRAM interface instance (e.g., DDR4_2400_16x4).
        cpu_clock: CPU clock frequency (default 2 GHz).
        cpu_voltage: Voltage domain level for the CPU clock domain.
        mem_size: Size of the system memory range.
        l1i_size: L1 instruction cache size.
        l1d_size: L1 data cache size.
        l2_size: Shared L2 cache size.

    Returns:
        The configured gem5 System object.
    """

    system = System()

    system.clk_domain = SrcClockDomain(
        clock=cpu_clock, voltage_domain=VoltageDomain(voltage=cpu_voltage)
    )
    system.mem_mode = "timing"
    system.mem_ranges = [AddrRange(mem_size)]

    system.membus = SystemXBar(width=64)
    system.l2bus = L2XBar(width=64)

    system.cpu = O3CPU()

    system.cpu.icache = L1ICache()
    system.cpu.dcache = L1DCache()
    system.l2cache = L2Cache()

    _configure_cache_sizes(system.cpu, l1i_size, l1d_size, l2_size, system.l2cache)

    system.cpu.icache.connect_cpu(system.cpu)
    system.cpu.dcache.connect_cpu(system.cpu)

    system.cpu.icache.connect_bus(system.l2bus)
    system.cpu.dcache.connect_bus(system.l2bus)

    system.l2cache.connect_cpu_side(system.l2bus)
    system.l2cache.connect_mem_side(system.membus)

    # Set up the memory controller
    # DRAMSim3 is an AbstractMemory and connects directly to the bus
    # gem5's built-in DRAM interfaces need to be wrapped in MemCtrl
    memory_controller.range = system.mem_ranges[0]

    if isinstance(memory_controller, DRAMsim3):
        # DRAMSim3 connects directly - it's already a complete memory controller
        system.mem_ctrl = memory_controller
        system.mem_ctrl.port = system.membus.mem_side_ports
    else:
        # gem5 built-in DRAM interfaces need MemCtrl wrapper
        system.mem_ctrl = MemCtrl()
        system.mem_ctrl.dram = memory_controller
        system.mem_ctrl.port = system.membus.mem_side_ports

    system.system_port = system.membus.cpu_side_ports

    # Set up workload for syscall emulation mode
    system.workload = SEWorkload.init_compatible(binary_path)

    process = Process()
    process.cmd = [binary_path]
    system.cpu.workload = process
    system.cpu.createThreads()
    system.cpu.createInterruptController()

    # Hook up TLB page-table walkers directly to the memory bus.
    if hasattr(system.cpu, "itb") and hasattr(system.cpu.itb, "walker"):
        system.cpu.itb.walker.port = system.membus.cpu_side_ports
    if hasattr(system.cpu, "dtb") and hasattr(system.cpu.dtb, "walker"):
        system.cpu.dtb.walker.port = system.membus.cpu_side_ports

    return system


def run_simulation(system: System, *, max_ticks: Optional[int] = None) -> None:
    """
    Instantiate and execute the provided gem5 system.

    Args:
        system: Configured gem5 System object.
        max_ticks: Optional maximum number of ticks to simulate.
    """

    root = Root(full_system=False, system=system)
    m5.instantiate()

    if max_ticks is not None and max_ticks > 0:
        exit_event = m5.simulate(max_ticks)
    else:
        exit_event = m5.simulate()

    print(f"Simulation exited @ tick {m5.curTick()} because {exit_event.getCause()}")
