#!/bin/bash
# Build script for RISC-V benchmarks
# This script compiles benchmarks for RISC-V architecture using cross-compilation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Parse arguments
FORCE_REBUILD=false
for arg in "$@"; do
    case $arg in
        --force|-f)
            FORCE_REBUILD=true
            ;;
    esac
done

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BENCHMARK_DIR="$PROJECT_ROOT/benchmarks"

cd "$BENCHMARK_DIR"

# Check if binaries already exist and are newer than source files
check_needs_rebuild() {
    local binary=$1
    local source=$2

    # If binary doesn't exist, need to build
    if [ ! -f "$binary" ]; then
        return 0  # true, needs rebuild
    fi

    # If source is newer than binary, need to rebuild
    if [ "$source" -nt "$binary" ]; then
        return 0  # true, needs rebuild
    fi

    return 1  # false, no rebuild needed
}

# Check if any rebuild is needed
TINYML_NEEDS_BUILD=false
CONV2D_NEEDS_BUILD=false

if [ "$FORCE_REBUILD" = true ]; then
    print_status "Force rebuild requested"
    TINYML_NEEDS_BUILD=true
    CONV2D_NEEDS_BUILD=true
else
    if check_needs_rebuild "build/tinyml.elf" "tinyml/tinyml.c"; then
        TINYML_NEEDS_BUILD=true
    fi
    if check_needs_rebuild "build/conv2d.elf" "conv2d/conv2d.c"; then
        CONV2D_NEEDS_BUILD=true
    fi
fi

# If nothing needs rebuilding, exit early
if [ "$TINYML_NEEDS_BUILD" = false ] && [ "$CONV2D_NEEDS_BUILD" = false ]; then
    print_success "All benchmarks are up to date, skipping build"
    print_status "  - build/tinyml.elf: OK"
    print_status "  - build/conv2d.elf: OK"
    print_status "Use --force or -f to rebuild anyway"
    exit 0
fi

# Check if RISC-V toolchain is available
if command -v riscv64-linux-gnu-gcc &> /dev/null; then
    CROSS_COMPILE="riscv64-linux-gnu-"
    print_status "Using RISC-V toolchain: ${CROSS_COMPILE}gcc"
elif command -v riscv64-unknown-elf-gcc &> /dev/null; then
    CROSS_COMPILE="riscv64-unknown-elf-"
    print_status "Using RISC-V toolchain: ${CROSS_COMPILE}gcc"
else
    print_error "RISC-V toolchain not found. Please install riscv64-linux-gnu-gcc or riscv64-unknown-elf-gcc"
    exit 1
fi

# Build only what's needed
print_status "Building benchmarks..."

if [ "$TINYML_NEEDS_BUILD" = true ] && [ "$CONV2D_NEEDS_BUILD" = true ]; then
    # Both need rebuild, use make all
    print_status "Compiling all benchmarks for RISC-V..."
    CROSS_COMPILE="$CROSS_COMPILE" make all
elif [ "$TINYML_NEEDS_BUILD" = true ]; then
    print_status "Compiling tinyml benchmark..."
    CROSS_COMPILE="$CROSS_COMPILE" make tinyml
elif [ "$CONV2D_NEEDS_BUILD" = true ]; then
    print_status "Compiling conv2d benchmark..."
    CROSS_COMPILE="$CROSS_COMPILE" make conv2d
fi

# Verify builds
print_status "Verifying built binaries..."
if [ -f "build/tinyml.elf" ]; then
    print_success "tinyml.elf built successfully ($(ls -lh build/tinyml.elf | awk '{print $5}'))"
else
    print_error "Failed to build tinyml.elf"
    exit 1
fi

if [ -f "build/conv2d.elf" ]; then
    print_success "conv2d.elf built successfully ($(ls -lh build/conv2d.elf | awk '{print $5}'))"
else
    print_error "Failed to build conv2d.elf"
    exit 1
fi

print_success "All benchmarks built successfully!"
