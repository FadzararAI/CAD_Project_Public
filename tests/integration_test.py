import json
import subprocess
import sys
from pathlib import Path

import pytest


def test_run_single_experiment_creates_results(monkeypatch, tmp_path):
    project_root = Path(__file__).resolve().parents[1]
    script = __import__("scripts.run_single_experiment", fromlist=["scripts"])

    workdir = tmp_path / "work"
    (workdir / "benchmarks").mkdir(parents=True)
    (workdir / "benchmarks" / "tinyml.elf").write_text("", encoding="utf-8")
    output_file = workdir / "out" / "ddr4_tinyml.json"
    config_path = project_root / "configs" / "ddr4_config.py"

    commands = {}

    def fake_run(cmd, capture_output=False, text=False, check=False, **_):
        commands["cmd"] = cmd
        stats_dir = workdir / "results" / "ddr4"
        stats_dir.mkdir(parents=True, exist_ok=True)
        stats_dir.joinpath("stats.txt").write_text(
            "\n".join(
                [
                    "sim_seconds 0.125",
                    "system.cpu.icache.overall_miss_rate::total 0.05",
                    "system.cpu.dcache.overall_miss_rate::total 0.07",
                    "system.mem_ctrls.bytes_read::total 1024",
                    "system.mem_ctrls.bytes_written::total 2048",
                    "system.mem_ctrls.avg_bandwidth::total 3.14",
                    "system.mem_ctrls.avg_latency::total 88.0",
                ]
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(script.subprocess, "run", fake_run)
    monkeypatch.chdir(workdir)

    argv = [
        "run_single_experiment.py",
        "--memory-type",
        "ddr4",
        "--benchmark",
        "tinyml",
        "--config",
        str(config_path),
        "--output",
        str(output_file),
    ]
    monkeypatch.setattr(sys, "argv", argv)

    script.main()

    assert commands["cmd"][0] == "gem5.opt"
    assert commands["cmd"][3] == str(config_path)
    assert commands["cmd"][4] == "benchmarks/tinyml.elf"
    assert output_file.exists()

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["memory_type"] == "ddr4"
    assert data["benchmark"] == "tinyml"
    assert data["sim_seconds"] == pytest.approx(0.125)
    assert data["avg_bandwidth"] == pytest.approx(3.14)
    assert data["avg_latency"] == pytest.approx(88.0)
    assert data["bytes_read"] == 1024
    assert data["bytes_written"] == 2048
    assert data["execution_time"] >= 0.0
