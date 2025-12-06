import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = REPO_ROOT / "benchmarks"


def _require_tool(name: str):
    if shutil.which(name) is None:
        pytest.skip(f"{name} not available in PATH")


def test_make_lists_expected_benchmarks():
    _require_tool("make")
    result = subprocess.run(
        ["make", "list"],
        cwd=BENCHMARK_DIR,
        capture_output=True,
        text=True,
        check=True,
    )
    entries = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    assert {"tinyml", "conv2d"}.issubset(entries)


@pytest.mark.parametrize(
    "target,binary",
    [("tinyml", "tinyml.elf"), ("conv2d", "conv2d.elf")],
)
def test_benchmarks_build_with_default_gcc(tmp_path, target, binary):
    _require_tool("make")
    _require_tool("gcc")

    env = os.environ.copy()
    out_dir = tmp_path / "build"
    env["OUT_DIR"] = str(out_dir)

    subprocess.run(
        ["make", target],
        cwd=BENCHMARK_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    assert (out_dir / binary).exists()
