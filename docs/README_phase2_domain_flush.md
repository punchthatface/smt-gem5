# Phase 2: gem5-side domain flush experiment

This document explains the Phase 2 implementation for SMT scheduling under security constraints.

## High-level goal

The goal is to evaluate a cache-cleanup mechanism for security-aware SMT experiments.

The mechanism models this idea:

```text
A protected workload reaches a work/domain boundary.
gem5 detects the boundary.
gem5 performs L1D writeback + invalidate.
simulation resumes.
```

This approximates cleanup of core-local cache state at security-domain or scheduling boundaries.

## What was added

### 1. gem5 config support

Main config:

```text
configs/smt_domain_flush.py
```

This config supports:

- multicore O3CPU setup
- SMT via `--threads-per-core`
- explicit L1I/L1D/L2 cache hierarchy
- running multiple jobs assigned to specific cores
- `--flush-on-workbegin`
- gem5-side L1D cleanup using:
  - `dcache.memWriteback()`
  - `dcache.memInvalidate()`

### 2. PARSEC swaptions patch

Patch files:

```text
patches/swaptions/HJM_Securities.cpp
patches/swaptions/Makefile
patches/swaptions/README.md
```

The patch adds:

```bash
-fi N
```

to PARSEC swaptions.

Meaning:

```text
-fi 0  = no markers
-fi 1  = marker every swaption
-fi 2  = marker every 2 swaptions
-fi 4  = marker every 4 swaptions
```

The application only emits markers. gem5 performs the L1D cleanup.

## Main runner

Main runner:

```text
scripts/run_parsec_phase2_smoke.py
```

Despite the name, this runner is used for the final Phase 2 runs. It:

- launches gem5 for each case in a JSON config
- collects gem5 stats
- records return code, flush count, sim stats, cache stats, and exit cause
- writes a CSV summary

## Config directory

Final Phase 2 JSON configs should live under:

```text
scripts/phase2_configs/
```

Important final configs:

```text
scripts/phase2_configs/parsec_phase2_final_node0_config.json
scripts/phase2_configs/parsec_phase2_final_node1_config.json
```

Current intended final pairing:

```text
node0: swaptions + streamcluster
node1: swaptions + blackscholes
```

Each final config includes:

```text
1. no-SMT separate-core baseline
2. shared SMT no flush
3. shared SMT flush fi1
4. shared SMT flush fi2
5. shared SMT flush fi4
```

## Example run

```bash
cd /users/<NETID>/smt-gem5

python3 scripts/run_parsec_phase2_smoke.py \
  --config scripts/phase2_configs/parsec_phase2_final_node0_config.json \
  --output-csv results/parsec_phase2_final_node0.csv \
  2>&1 | tee results/parsec_phase2_final_node0.log
```

For long runs, use tmux:

```bash
tmux new -s final
```

Detach:

```text
Ctrl+b then d
```

Reattach:

```bash
tmux attach -t final
```

## Expected output

The CSV includes fields such as:

```text
name
policy
returncode
num_cores
threads_per_core
flush_enabled
flush_count
simInsts
simSeconds
throughput_inst_per_simsec
host_wallclock_sec
l1d_accesses
l1d_misses
l1d_miss_rate
l2_accesses
l2_misses
l2_miss_rate
exit_cause
outdir
```

A valid final row should have:

```text
returncode = 0
exit_cause = exiting with last active thread context
```

For flush cases:

```text
flush_count > 0
```

For no-flush cases:

```text
flush_count = 0
```

## What plots this supports

The final CSVs support:

1. Normalized throughput by policy
2. L1D miss rate by policy / flush interval
3. L2 miss rate by policy / flush interval
4. Flush count vs flush interval
5. no-SMT separate-core vs shared-SMT comparison
6. Comparison across two PARSEC co-runners

## Important limitations

This implementation models L1D cleanup only.

It does not claim to fully protect all SMT shared resources. It does not flush or partition:

- branch predictors
- TLBs
- execution ports
- load/store queues
- ROB / issue queues
- fill buffers

Correct interpretation:

```text
This evaluates the cost and cache behavior of gem5-side L1D cleanup at marked work/domain boundaries.
```

It should not be described as a complete SecSMT implementation.
