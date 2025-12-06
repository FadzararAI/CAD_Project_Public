#!/bin/bash

# CAD Memory Technology Study - Experiment Runner
# This script runs experiments in Docker containers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
mkdir -p results/{ddr4,ddr5,hbm2}
mkdir -p logs
mkdir -p benchmarks

# Function to check if Docker image exists
check_docker_image() {
    if ! docker images | grep -q "cad"; then
        print_warning "Docker image not found. Building it first..."
        docker-compose build
    fi
}

# Function to run a single experiment
run_experiment() {
    local memory_type=$1
    local benchmark=$2
    local config=$3
    
    print_status "Running experiment: $memory_type with $benchmark"
    
    MSYS_NO_PATHCONV=1 docker-compose run --rm cad-experiment \
        python scripts/run_single_experiment.py \
        --memory-type $memory_type \
        --benchmark $benchmark \
        --config $config \
        --output results/$memory_type/${benchmark}_${memory_type}.json
}

# Function to build benchmarks
build_benchmarks() {
    check_docker_image
    print_status "Building benchmarks..."

    MSYS_NO_PATHCONV=1 docker-compose run --rm cad-experiment bash /workspace/scripts/build_benchmarks.sh $1

    if [ $? -ne 0 ]; then
        print_error "Failed to build benchmarks"
        exit 1
    fi

    print_success "Benchmarks built successfully"
}

# Function to run all experiments
run_all_experiments() {
    check_docker_image
    print_status "Running all experiments..."

    # Build benchmarks first (will skip if already built)
    build_benchmarks

    # Memory types
    memory_types=("ddr4" "ddr5" "hbm2")

    # Benchmarks
    benchmarks=("tinyml" "conv2d")

    # Run experiments
    for memory_type in "${memory_types[@]}"; do
        for benchmark in "${benchmarks[@]}"; do
            # DDR5 uses gem5 built-in model (ddr5_gem5_config.py)
            # DDR4 and HBM2 use DRAMSim3 for detailed metrics
            if [ "$memory_type" == "ddr5" ]; then
                run_experiment $memory_type $benchmark "configs/ddr5_gem5_config.py"
            else
                run_experiment $memory_type $benchmark "configs/${memory_type}_config.py"
            fi
        done
    done
}

# Function to analyze results
analyze_results() {
    check_docker_image
    print_status "Analyzing results..."

    MSYS_NO_PATHCONV=1 docker-compose run --rm cad-experiment \
        python scripts/analyze_results.py \
        --input-dir results/ \
        --output-dir results/analysis/
}

# Main menu
case "${1:-help}" in
    "build")
        print_status "Building Docker image..."
        docker-compose build
        print_success "Docker image built successfully!"
        ;;
    "compile")
        build_benchmarks "$2"
        ;;
    "rebuild")
        build_benchmarks "--force"
        ;;
    "run")
        run_all_experiments
        print_success "All experiments completed!"
        ;;
    "analyze")
        analyze_results
        print_success "Results analyzed!"
        ;;
    "shell")
        check_docker_image
        print_status "Starting interactive shell..."
        MSYS_NO_PATHCONV=1 docker-compose run --rm cad-experiment //bin/bash
        ;;
    "jupyter")
        print_status "Starting Jupyter notebook..."
        docker-compose up jupyter
        ;;
    "clean")
        print_status "Cleaning up Docker containers and images..."
        docker-compose down
        docker system prune -f
        print_success "Cleanup completed!"
        ;;
    "help"|*)
        echo "CAD Memory Technology Study - Experiment Runner"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  build     - Build Docker image"
        echo "  compile   - Compile benchmarks for RISC-V (skips if up to date)"
        echo "  rebuild   - Force recompile all benchmarks"
        echo "  run       - Run all experiments (includes compilation)"
        echo "  analyze   - Analyze results"
        echo "  shell     - Start interactive shell"
        echo "  jupyter   - Start Jupyter notebook"
        echo "  clean     - Clean up Docker resources"
        echo "  help      - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 build"
        echo "  $0 compile"
        echo "  $0 compile --force   # Force recompile"
        echo "  $0 rebuild           # Same as compile --force"
        echo "  $0 run"
        echo "  $0 shell"
        ;;
esac