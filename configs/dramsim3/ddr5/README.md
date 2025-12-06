# DDR5 Configuration Files for DRAMSim3

This directory contains DDR5 timing and structural configuration files for DRAMSim3 that ship with the CAD Memory Technology Study repository.

Each `.ini` file represents a 16Gb x8 DDR5 component at a different data rate. Timing values follow JEDEC JESD79-5A and recent public vendor datasheets (Micron, Samsung, SK hynix). When DRAMSim3 requires cycle-aligned values, the parameters are rounded to the nearest cycle.

## Files

- `DDR5_16Gb_x8_4800.ini` – Baseline DDR5-4800 configuration
- `DDR5_16Gb_x8_5600.ini` – Higher-bin DDR5-5600 configuration
- `DDR5_16Gb_x8_6400.ini` – Enthusiast-grade DDR5-6400 configuration

Common assumptions across the three bins:

- Two 32-bit subchannels (effective 64-bit channel width)
- Single rank per channel with eight x8 devices
- Open-page policy with FR-FCFS scheduler
- Per-bank command queues

To use these from GEM5, point the DRAMSim3 wrapper to the desired `.ini` file, for example:

```bash
--dramsim3-ini=configs/dramsim3/ddr5/DDR5_16Gb_x8_5600.ini
```
