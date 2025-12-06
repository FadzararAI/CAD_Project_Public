# CAD Memory Technology Study

## Overview

This project conducts a comparative analysis of DDR4, DDR5, and HBM2 memory technologies, evaluating their performance in terms of execution time and bandwidth utilization when running TinyML and Conv2D machine learning workloads. The experiments are performed using the gem5 simulator with RISC-V architecture.

## Approach

This **branch** implements **Approach 2: gem5 Built-in DDR5 Model**.

Since DRAMSim3 does not natively support the DDR5 protocol, this approach uses a hybrid strategy:

| Memory Type | Simulation Backend | Metrics Available |
|-------------|-------------------|-------------------|
| **DDR4** | DRAMSim3 | Full metrics (row buffer hit rate, bank-level stats, power) |
| **DDR5** | gem5 built-in DDR5_4400_4x8 | Basic metrics (execution time, bandwidth, latency) |
| **HBM2** | DRAMSim3 | Full metrics (row buffer hit rate, bank-level stats, power) |

### Alternative Approach

**Approach 1** (documented in `A1.md`) uses DRAMSim3 with DDR4 protocol and DDR5-accurate timing parameters for all memory types. This provides consistent metrics across all memory types but compromises DDR5 protocol accuracy (burst length reduced from 16 to 8, DDR4 command scheduling).

## Project Goals

- Compare DDR4, DDR5, and HBM2 memory technologies for ML workloads
- Evaluate performance using TinyML and Conv2D benchmark algorithms
- Measure execution time, bandwidth, latency, and cache hit rates
- Provide data-driven guidance for RISC-V ML workload memory selection

## System Requirements

- **OS**: Linux (Ubuntu 20.04+ recommended)
- **RAM**: Minimum 8GB (16GB+ recommended for simulations)
- **Storage**: 20GB+ free space
- **CPU**: Multi-core processor (4+ cores recommended)

## Software Requirements

- **Docker** (20.10+)
- **Docker Compose** (1.29+)
- **Git**

## Installation

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installations
docker --version
docker-compose --version

# Clone and setup
git clone <your-repo-url>
cd CAD
chmod +x run_experiment.sh
```

## How to Run

### 1. Build Docker Environment

```bash
./run_experiment.sh build
```

This builds the Docker image containing gem5, DRAMSim3, and the RISC-V toolchain. First build takes 30-60 minutes.

### 2. Compile Benchmarks

```bash
./run_experiment.sh compile
```

Compiles TinyML and Conv2D benchmarks for RISC-V architecture.

### 3. Run Experiments

```bash
# Run all experiments (DDR4, DDR5, HBM2 with both benchmarks)
./run_experiment.sh run

# Or run a specific experiment manually
./run_experiment.sh shell
# Inside container:
python3 scripts/run_single_experiment.py \
    --memory-type ddr4 \
    --benchmark tinyml \
    --config configs/ddr4_config.py \
    --output results/ddr4/tinyml_ddr4.json
```

### 4. Analyze Results

```bash
./run_experiment.sh analyze
```

## Commands

| Command | Description |
|---------|-------------|
| `./run_experiment.sh build` | Build Docker image with gem5 and DRAMSim3 |
| `./run_experiment.sh compile` | Compile benchmarks for RISC-V |
| `./run_experiment.sh rebuild` | Force recompile all benchmarks |
| `./run_experiment.sh run` | Run all experiments (DDR4, DDR5, HBM2) |
| `./run_experiment.sh shell` | Start interactive shell in container |
| `./run_experiment.sh jupyter` | Start Jupyter notebook for analysis |
| `./run_experiment.sh analyze` | Analyze collected results |
| `./run_experiment.sh clean` | Clean up Docker resources |
| `./run_experiment.sh help` | Show help message |

## Project Structure

```
CAD/
├── Dockerfile                 # Multi-stage Docker build
├── docker-compose.yml         # Container orchestration
├── run_experiment.sh          # Main experiment runner
├── README.md                  # This file
├── A1.md                      # Approach 1 documentation (DRAMSim3 DDR5)
│
├── configs/                   # gem5 and DRAMSim3 configurations
│   ├── riscv_cpu.py           # RISC-V O3CPU configuration
│   ├── ddr4_config.py         # DDR4 with DRAMSim3
│   ├── ddr5_config.py         # DDR5 with DRAMSim3 (Approach 1)
│   ├── ddr5_gem5_config.py    # DDR5 with gem5 built-in (Approach 2)
│   ├── hbm2_config.py         # HBM2 with DRAMSim3
│   └── dramsim3/
│       └── ddr5/              # DRAMSim3 DDR5 timing configs
│           ├── DDR5_16Gb_x8_4800.ini
│           ├── DDR5_16Gb_x8_5600.ini
│           └── DDR5_16Gb_x8_6400.ini
│
├── benchmarks/                # Test programs
│   ├── Makefile               # Build system for benchmarks
│   ├── tinyml/
│   │   └── tinyml.c           # TinyML algorithm implementation
│   └── conv2d/
│       └── conv2d.c           # Conv2D algorithm implementation
│
├── scripts/                   # Experiment automation & analysis
│   ├── run_single_experiment.py
│   ├── batch_runner.py        # Batch experiment execution
│   ├── analyze_results.py     # Result aggregation
│   ├── result_utils.py        # Shared result utilities
│   ├── detect_regressions.py  # Baseline comparisons
│   ├── generate_report.py     # Markdown report builder
│   └── generate_plots.py      # Performance comparison charts
│
├── results/                   # Experiment results
│   ├── ddr4/                  # DDR4 results
│   ├── ddr5/                  # DDR5 results
│   ├── hbm2/                  # HBM2 results
│   └── analysis/              # Analysis outputs
│
├── tests/                     # Validation tests
├── logs/                      # Experiment logs
├── gem5/                      # gem5 simulator (submodule)
└── dramsim3/                  # DRAMSim3 simulator (submodule)
```

## Analysis Utilities

### Aggregate Results

```bash
python3 scripts/analyze_results.py --input-dir results --output-dir results/analysis
```

Aggregates JSON outputs from all experiments and generates CSV/JSON summaries.

### Detect Regressions

```bash
python3 scripts/detect_regressions.py --baseline results_baseline --current results
```

Compares a baseline directory against the latest results and flags performance degradations.

### Generate Report

```bash
python3 scripts/generate_report.py --input-dir results --output results/analysis/report.md
```

Produces a Markdown summary highlighting top-performing memory configurations.

### Generate Plots

```bash
python3 scripts/generate_plots.py --input-dir results --output-dir results/analysis
```

Creates performance comparison charts and visualizations.

## Experiment Configuration

### Memory Types

| Type | Speed Range | Configuration |
|------|-------------|---------------|
| **DDR4** | 2133-3200 MHz | DRAMSim3 with full metrics |
| **DDR5** | 4400 MHz (gem5 built-in) | gem5 DDR5_4400_4x8 model |
| **HBM2** | 1-4 GB stacks | DRAMSim3 with full metrics |

### Benchmarks

- **TinyML**: Lightweight ML inference algorithms for edge devices
- **Conv2D**: 2D convolution operations for image processing

### Metrics Collected

| Metric | DDR4 | DDR5 | HBM2 |
|--------|------|------|------|
| Execution time (sim_seconds) | Yes | Yes | Yes |
| Average bandwidth (GB/s) | Yes | Yes | Yes |
| Average memory latency (ns) | Yes | Yes | Yes |
| Cache hit rates (L1, L2) | Yes | Yes | Yes |
| Row buffer hit rate | Yes | No* | Yes |
| Bank-level statistics | Yes | No* | Yes |
| Power consumption | Yes | No* | Yes |

*DDR5 using gem5 built-in model does not provide these detailed metrics.

## References

- [gem5 Simulator Documentation](https://www.gem5.org/documentation/)
- [DRAMSim3 Documentation](https://github.com/umd-memsys/DRAMSim3)
- [RISC-V Instruction Set Manual](https://riscv.org/technical/specifications/)
- [TinyML Foundation](https://www.tinyml.org/)
