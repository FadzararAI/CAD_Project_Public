import importlib
import sys
import types
from pathlib import Path

import pytest


def _install_fake_m5() -> types.ModuleType:
    # Only install the shim once; reuse it across imports.
    existing = sys.modules.get("m5")
    if existing:
        return existing

    m5_module = types.ModuleType("m5")
    objects_module = types.ModuleType("m5.objects")

    class FakeExitEvent:
        def getCause(self) -> str:
            return "test exit"

    class FakeCache:
        size = ""

        def __init__(self):
            self.cpu_side = None
            self.mem_side = None

    class FakeWalker:
        def __init__(self):
            self.port = None

    class FakeTLB:
        def __init__(self):
            self.walker = FakeWalker()

    class FakeO3CPU:
        def __init__(self):
            self.icache_port = object()
            self.dcache_port = object()
            self.icache = FakeCache()
            self.dcache = FakeCache()
            self.workload = None
            self.itb = FakeTLB()
            self.dtb = FakeTLB()

        def createThreads(self) -> None:
            pass

    class FakeL2XBar:
        def __init__(self, width=0):
            self.width = width
            self.cpu_side_ports = object()
            self.mem_side_ports = object()

    class FakeSystemXBar(FakeL2XBar):
        pass

    class FakeVoltageDomain:
        def __init__(self, voltage="1.0V"):
            self.voltage = voltage

    class FakeSrcClockDomain:
        def __init__(self, clock="1GHz", voltage_domain=None):
            self.clock = clock
            self.voltage_domain = voltage_domain

    class FakeAddrRange:
        def __init__(self, size: str):
            self.size = size

    class FakeProcess:
        def __init__(self):
            self.cmd = []

    class FakeSystem:
        def __init__(self):
            self.clk_domain = None
            self.mem_mode = ""
            self.mem_ranges = []
            self.membus = None
            self.l2bus = None
            self.cpu = None
            self.l2cache = None
            self.mem_ctrl = None
            self.system_port = None
            self.workload = None

    class FakeRoot:
        def __init__(self, full_system=False, system=None):
            self.full_system = full_system
            self.system = system

    class FakeDRAMSim3:
        def __init__(self):
            self.device_config = None
            self.device_file = None
            self.system_config = None
            self.config_file = None
            self.work_dir = None
            self.trace_file = None
            self.range = None
            self.port = None

    def instantiate() -> None:
        return None

    def simulate(max_ticks=None):
        return FakeExitEvent()

    def curTick() -> int:
        return 12345

    objects_module.Cache = FakeCache
    objects_module.L2XBar = FakeL2XBar
    objects_module.O3CPU = FakeO3CPU
    objects_module.Process = FakeProcess
    objects_module.Root = FakeRoot
    objects_module.SrcClockDomain = FakeSrcClockDomain
    objects_module.System = FakeSystem
    objects_module.SystemXBar = FakeSystemXBar
    objects_module.VoltageDomain = FakeVoltageDomain
    objects_module.AddrRange = FakeAddrRange
    objects_module.DRAMSim3 = FakeDRAMSim3

    m5_module.objects = objects_module
    m5_module.instantiate = instantiate
    m5_module.simulate = simulate
    m5_module.curTick = curTick

    sys.modules["m5"] = m5_module
    sys.modules["m5.objects"] = objects_module
    return m5_module


_install_fake_m5()

ddr4_config = importlib.import_module("configs.ddr4_config")
ddr5_config = importlib.import_module("configs.ddr5_config")
hbm2_config = importlib.import_module("configs.hbm2_config")


@pytest.mark.parametrize(
    "module,expected_output_dir",
    [
        (ddr4_config, "logs/dramsim3/ddr4"),
        (ddr5_config, "logs/dramsim3/ddr5"),
        (hbm2_config, "logs/dramsim3/hbm2"),
    ],
)
def test_build_memory_controller_sets_expected_fields(module, expected_output_dir, tmp_path):
    controller = module.build_memory_controller("dev.ini", "sys.ini", tmp_path)
    assert controller.device_config == "dev.ini"
    assert controller.device_file == "dev.ini"
    assert controller.system_config == "sys.ini"
    assert controller.config_file == "sys.ini"
    assert controller.work_dir == str(tmp_path)
    assert controller.trace_file == ""
    assert isinstance(tmp_path, Path)
    assert module.DEFAULT_OUTPUT_DIR == expected_output_dir


@pytest.mark.parametrize(
    "module,env_key,env_value",
    [
        (ddr4_config, "DDR4_DEVICE_CONFIG", "custom_ddr4.ini"),
        (ddr5_config, "DDR5_DEVICE_CONFIG", "custom_ddr5.ini"),
        (hbm2_config, "HBM2_DEVICE_CONFIG", "custom_hbm2.ini"),
    ],
)
def test_parse_args_respects_environment_overrides(module, env_key, env_value, monkeypatch, tmp_path):
    monkeypatch.setenv(env_key, env_value)
    monkeypatch.setenv("DDR_SYSTEM_CONFIG", "system_override.ini")
    monkeypatch.setenv("DRAMSIM3_OUTPUT_DIR", str(tmp_path / "logs"))
    monkeypatch.setattr(sys, "argv", ["config.py", "benchmark.elf"])

    args = module.parse_args()

    assert args.binary == "benchmark.elf"
    assert args.device_config == env_value
    assert args.system_config == "system_override.ini"
    assert Path(args.output_dir) == tmp_path / "logs"


@pytest.mark.parametrize(
    "module",
    [ddr4_config, ddr5_config, hbm2_config],
)
def test_main_invokes_run_simulation_with_expected_arguments(module, monkeypatch, tmp_path):
    created = {}

    def fake_create_riscv_system(**kwargs):
        created["kwargs"] = kwargs
        return object()

    def fake_run_simulation(system, max_ticks=None):
        created["system"] = system
        created["max_ticks"] = max_ticks

    monkeypatch.setattr(module, "create_riscv_system", fake_create_riscv_system)
    monkeypatch.setattr(module, "run_simulation", fake_run_simulation)

    output_dir = tmp_path / "dramsim_output"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "config.py",
            "app.elf",
            "--device-config",
            "device.ini",
            "--system-config",
            "system.ini",
            "--output-dir",
            str(output_dir),
            "--cpu-clock",
            "3GHz",
            "--mem-size",
            "2GB",
            "--max-ticks",
            "250000",
        ],
    )

    module.main()

    assert "kwargs" in created
    assert created["kwargs"]["binary_path"] == "app.elf"
    assert created["kwargs"]["cpu_clock"] == "3GHz"
    assert created["kwargs"]["mem_size"] == "2GB"
    mem_ctrl = created["kwargs"]["memory_controller"]
    assert mem_ctrl.device_config == "device.ini"
    assert mem_ctrl.system_config == "system.ini"
    assert created["max_ticks"] == 250000
    assert output_dir.exists()
