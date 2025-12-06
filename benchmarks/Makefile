## Basic build system for benchmark programs.

CROSS_COMPILE ?= riscv64-linux-gnu-
CC := $(CROSS_COMPILE)gcc

OUT_DIR ?= build
BENCHMARKS := conv2d tinyml

conv2d_SRC := conv2d/conv2d.c
conv2d_BIN := $(OUT_DIR)/conv2d.elf
tinyml_SRC := tinyml/tinyml.c
tinyml_BIN := $(OUT_DIR)/tinyml.elf

ARCH_FLAGS := -march=rv64gc -mabi=lp64d
LINK_FLAGS := -static

CFLAGS ?= -O3 -std=c11 -Wall -Wextra -pedantic
LDFLAGS ?=

BINARIES := $(conv2d_BIN) $(tinyml_BIN)

.PHONY: all clean list conv2d tinyml help

all: $(BINARIES)

list:
	@printf "%s\n" $(BENCHMARKS)

conv2d: $(conv2d_BIN)

tinyml: $(tinyml_BIN)

$(OUT_DIR):
	mkdir -p $@

$(conv2d_BIN): $(conv2d_SRC) | $(OUT_DIR)
	$(CC) $(CFLAGS) $(ARCH_FLAGS) -o $@ $< $(LDFLAGS) $(LINK_FLAGS)

$(tinyml_BIN): $(tinyml_SRC) | $(OUT_DIR)
	$(CC) $(CFLAGS) $(ARCH_FLAGS) -o $@ $< $(LDFLAGS) $(LINK_FLAGS) -lm

clean:
	rm -rf $(OUT_DIR)

help:
	@echo "Available targets:"
	@echo "  make               Build all benchmarks"
	@echo "  make conv2d        Build only conv2d"
	@echo "  make list          Show known benchmarks"
	@echo "  make clean         Remove build outputs"
	@echo
	@echo "Set CROSS_COMPILE=<prefix> to cross-compile (e.g. riscv64-unknown-elf-)."
