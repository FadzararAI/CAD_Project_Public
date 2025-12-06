#!/usr/bin/env python
"""
Single Experiment Runner for CAD Memory Technology Study
Runs a single experiment with specified memory type and benchmark
"""

import argparse
import subprocess
import json
import time
import os
import sys
from pathlib import Path

def run_gem5_simulation(memory_type, benchmark, config_file, output_file):
    """Run GEM5 simulation with specified parameters"""

    # Check if benchmark exists
    benchmark_path = f"benchmarks/build/{benchmark}.elf"
    if not os.path.exists(benchmark_path):
        print(f"Error: Benchmark file not found: {benchmark_path}")
        print("Please run './scripts/build_benchmarks.sh' first to compile benchmarks")
        return None

    # GEM5 command - use full path to gem5.opt
    gem5_cmd = [
        "/opt/gem5/build/RISCV/gem5.opt",
        "--outdir", f"results/{memory_type}",
        config_file,
        benchmark_path
    ]
    
    print(f"Running GEM5 simulation: {' '.join(gem5_cmd)}")
    
    # Run simulation
    start_time = time.time()
    result = subprocess.run(gem5_cmd, capture_output=True, text=True)
    end_time = time.time()
    
    # Check if simulation was successful
    if result.returncode != 0:
        print(f"Error running simulation (return code {result.returncode}):")
        print("=== STDOUT ===")
        print(result.stdout)
        print("=== STDERR ===")
        print(result.stderr)
        return None
    
    # Extract performance metrics from GEM5 output
    metrics = extract_metrics(f"results/{memory_type}/stats.txt")
    metrics['execution_time'] = end_time - start_time
    metrics['memory_type'] = memory_type
    metrics['benchmark'] = benchmark
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    return metrics

def extract_metrics(stats_file):
    """
    Extract performance metrics from GEM5 stats.txt

    Required metrics per CADProject_CONTEXT.txt:
    - Execution time (sim_seconds)
    - Average bandwidth
    - Average memory latency
    - Row buffer hit rate
    """
    metrics = {}

    try:
        with open(stats_file, 'r') as f:
            content = f.read()

        for line in content.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            parts = line.split()
            if len(parts) < 2:
                continue

            stat_name = parts[0]
            try:
                stat_value = float(parts[1])
            except (ValueError, IndexError):
                continue

            # Execution time
            if stat_name == 'simSeconds' or stat_name == 'sim_seconds':
                metrics['sim_seconds'] = stat_value

            # Cache miss rates
            elif 'icache' in stat_name and 'overallMissRate' in stat_name and '::total' in stat_name:
                metrics['icache_miss_rate'] = stat_value
            elif 'dcache' in stat_name and 'overallMissRate' in stat_name and '::total' in stat_name:
                metrics['dcache_miss_rate'] = stat_value

            # Memory controller stats - try multiple naming conventions
            # Bytes read/written
            elif 'mem_ctrl' in stat_name and 'bytesRead' in stat_name and '::total' in stat_name:
                metrics['bytes_read'] = int(stat_value)
            elif 'mem_ctrl' in stat_name and 'bytesWritten' in stat_name and '::total' in stat_name:
                metrics['bytes_written'] = int(stat_value)

            # Average bandwidth (bytes/second)
            elif 'mem_ctrl' in stat_name and 'bwRead' in stat_name and '::total' in stat_name:
                metrics['avg_read_bandwidth'] = stat_value
            elif 'mem_ctrl' in stat_name and 'bwWrite' in stat_name and '::total' in stat_name:
                metrics['avg_write_bandwidth'] = stat_value
            elif 'mem_ctrl' in stat_name and 'bwTotal' in stat_name and '::total' in stat_name:
                metrics['avg_bandwidth'] = stat_value

            # Average memory latency (in ticks or ns)
            elif 'mem_ctrl' in stat_name and 'avgRdBW' in stat_name:
                metrics['avg_read_bandwidth'] = stat_value
            elif 'mem_ctrl' in stat_name and 'avgWrBW' in stat_name:
                metrics['avg_write_bandwidth'] = stat_value

            # DRAM specific stats
            elif 'dram' in stat_name.lower():
                # Row buffer hit rate
                if 'readRowHits' in stat_name:
                    metrics['read_row_hits'] = int(stat_value)
                elif 'writeRowHits' in stat_name:
                    metrics['write_row_hits'] = int(stat_value)
                elif 'readRowHitRate' in stat_name:
                    metrics['read_row_hit_rate'] = stat_value
                elif 'writeRowHitRate' in stat_name:
                    metrics['write_row_hit_rate'] = stat_value
                # Read/write latency
                elif 'avgRdQLen' in stat_name:
                    metrics['avg_read_queue_len'] = stat_value
                elif 'avgWrQLen' in stat_name:
                    metrics['avg_write_queue_len'] = stat_value
                elif 'totQLat' in stat_name:
                    metrics['total_queue_latency'] = stat_value
                elif 'totMemAccLat' in stat_name:
                    metrics['total_mem_access_latency'] = stat_value
                elif 'avgMemAccLat' in stat_name:
                    metrics['avg_mem_latency'] = stat_value
                # Total reads/writes
                elif 'numReads' in stat_name and '::total' in stat_name:
                    metrics['num_reads'] = int(stat_value)
                elif 'numWrites' in stat_name and '::total' in stat_name:
                    metrics['num_writes'] = int(stat_value)

            # Alternative stat names (gem5 versions vary)
            elif 'averageLatency' in stat_name or 'avgLatency' in stat_name:
                if 'mem_ctrl' in stat_name or 'mem_ctrls' in stat_name:
                    metrics['avg_latency'] = stat_value
            elif 'averageBandwidth' in stat_name or 'avgBandwidth' in stat_name:
                if 'mem_ctrl' in stat_name or 'mem_ctrls' in stat_name:
                    metrics['avg_bandwidth'] = stat_value

    except FileNotFoundError:
        print(f"Warning: Stats file {stats_file} not found")
    except Exception as e:
        print(f"Warning: Error parsing stats file: {e}")

    # Calculate derived metrics if possible
    if 'read_row_hits' in metrics and 'num_reads' in metrics and metrics['num_reads'] > 0:
        metrics['read_row_hit_rate'] = metrics['read_row_hits'] / metrics['num_reads']
    if 'write_row_hits' in metrics and 'num_writes' in metrics and metrics['num_writes'] > 0:
        metrics['write_row_hit_rate'] = metrics['write_row_hits'] / metrics['num_writes']

    # Combined row buffer hit rate
    total_hits = metrics.get('read_row_hits', 0) + metrics.get('write_row_hits', 0)
    total_accesses = metrics.get('num_reads', 0) + metrics.get('num_writes', 0)
    if total_accesses > 0:
        metrics['row_buffer_hit_rate'] = total_hits / total_accesses

    # Calculate total bandwidth if components available
    if 'avg_read_bandwidth' in metrics and 'avg_write_bandwidth' in metrics:
        if 'avg_bandwidth' not in metrics:
            metrics['avg_bandwidth'] = metrics['avg_read_bandwidth'] + metrics['avg_write_bandwidth']

    return metrics

def main():
    parser = argparse.ArgumentParser(description='Run single experiment')
    parser.add_argument('--memory-type', required=True, choices=['ddr4', 'ddr5', 'hbm2'],
                        help='Memory type to test')
    parser.add_argument('--benchmark', required=True, choices=['tinyml', 'conv2d'],
                        help='Benchmark to run')
    parser.add_argument('--config', required=True, help='GEM5 configuration file')
    parser.add_argument('--output', required=True, help='Output JSON file')
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Run experiment
    metrics = run_gem5_simulation(args.memory_type, args.benchmark, args.config, args.output)
    
    if metrics:
        print(f"Experiment completed successfully!")
        print(f"Results saved to: {args.output}")
        print(f"Execution time: {metrics['execution_time']:.2f} seconds")
    else:
        print("Experiment failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()