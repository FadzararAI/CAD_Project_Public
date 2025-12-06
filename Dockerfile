# Multi-stage Dockerfile for CAD Memory Technology Study
FROM ubuntu:22.04 as base

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV GEM5_HOME=/opt/gem5
ENV DRAMSIM3_HOME=/opt/dramsim3

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    python-is-python3 \
    scons \
    zlib1g-dev \
    libprotobuf-dev \
    protobuf-compiler \
    libprotoc-dev \
    libgoogle-perftools-dev \
    pkg-config \
    cmake \
    make \
    gcc \
    g++ \
    wget \
    curl \
    vim \
    nano \
    htop \
    gcc-riscv64-linux-gnu \
    g++-riscv64-linux-gnu \
    m4 \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /workspace

# Copy project files
COPY . /workspace/

# Stage 1: Build GEM5 with DRAMSim3 integration
FROM base as gem5-builder
WORKDIR /opt

# Clone gem5
RUN git clone https://github.com/gem5/gem5.git

# Clone DRAMSim3 into gem5's ext directory for integration
WORKDIR /opt/gem5/ext/dramsim3
RUN git clone https://github.com/umd-memsys/DRAMSim3.git DRAMsim3

# Build DRAMSim3 library
WORKDIR /opt/gem5/ext/dramsim3/DRAMsim3
RUN mkdir -p build && cd build && cmake .. && make -j8

# Build gem5 with DRAMSim3 support
WORKDIR /opt/gem5
# For 32GB RAM with i9 (8+ cores): use -j8 for parallel compilation
# Each gem5 compile job uses ~2-4GB RAM, so 8 jobs = ~16-32GB
RUN scons build/RISCV/gem5.opt -j8

# Stage 2: Build standalone DRAMSim3 (for configs and standalone use)
FROM base as dramsim3-builder
WORKDIR /opt
RUN git clone https://github.com/umd-memsys/DRAMSim3.git dramsim3
WORKDIR /opt/dramsim3
RUN mkdir -p build && cd build && cmake .. && make -j8

# Stage 3: Final image
FROM base as final

# Copy built GEM5
COPY --from=gem5-builder /opt/gem5 /opt/gem5

# Copy built DRAMSim3
COPY --from=dramsim3-builder /opt/dramsim3 /opt/dramsim3

# Set environment variables
ENV GEM5_HOME=/opt/gem5
ENV DRAMSIM3_HOME=/opt/dramsim3
ENV PATH=$PATH:/opt/gem5/build/RISCV
ENV RISCV_CROSS_COMPILE=riscv64-linux-gnu-

# Create experiment directories
RUN mkdir -p /workspace/experiments/{ddr4,ddr5,hbm2}
RUN mkdir -p /workspace/results/{ddr4,ddr5,hbm2}
RUN mkdir -p /workspace/benchmarks
RUN mkdir -p /workspace/logs

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    numpy \
    matplotlib \
    pandas \
    seaborn \
    scipy \
    jupyter \
    tqdm

# Create non-root user
RUN useradd -m -s /bin/bash researcher
RUN chown -R researcher:researcher /workspace
USER researcher

# Set working directory
WORKDIR /workspace

# Default command
CMD ["/bin/bash"]
