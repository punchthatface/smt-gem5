# Phase 2: SMT security-policy experiment

## Current final target

The final experiment is a 4-core / 8-thread SMT policy study using unmodified PARSEC workloads.

Hardware model:

```text
4 physical cores
2 SMT hardware threads per core
8 hardware contexts total
```

Workload set:

```text
swaptions
blackscholes
streamcluster
fluidanimate
canneal
freqmine
bodytrack
dedup
```

`freqmine` uses `gcc-openmp`; run it with `OMP_NUM_THREADS=1` so it acts as one workload/domain in gem5 SE mode.

## Policies

The final comparison should include four policies:

```text
1. no_smt
   8 cores, 1 thread/core, 8 workloads.
   Isolation baseline: no two workloads share an SMT core.

2. unrestricted_smt
   4 cores, 2 threads/core, 8 workloads.
   Normal SMT co-running with default gem5 O3 SMT behavior.

3. constrained_smt
   4 cores, 2 threads/core, 8 workloads.
   Uses gem5 O3 SMT resource policy when supported:
     smtFetchPolicy  = RoundRobin
     smtCommitPolicy = RoundRobin
     smtROBPolicy    = Partitioned
     smtLSQPolicy    = Partitioned
   `smtIQPolicy=Partitioned` was tested but not supported in the current gem5 build.

4. flush_smt
   4 cores, 2 threads/core, 8 workloads.
   Same placement as unrestricted_smt, plus periodic L1D cleanup:
     dcache.memWriteback()
     dcache.memInvalidate()
```

## Main files

```text
configs/smt_domain_flush.py
  Main gem5 SE config. Supports:
  - SMT/no-SMT workload placement
  - periodic L1D cleanup
  - O3 SMT resource policy controls

scripts/run_phase2_experiment.py
  Main experiment runner. Reads JSON configs, launches gem5, writes CSV.

scripts/setup-phase2-parsec.sh
  Builds/prepares the 8 PARSEC workloads.

scripts/copy-phase2-parsec-runs.sh
  Optional helper to copy prepared PARSEC run/ input directories from another node.

scripts/phase2_configs/test/
  Short fixed-window test configs only.

scripts/phase2_configs/final/
  Long final configs only.

results/test_runs/
  Short tests. It is OK for these to end with simulate() limit reached.

results/final/
  Final runs. These should ideally exit naturally:
    exiting with last active thread context
```

## Setup on a node

After `setup-cloudlab.sh`:

```bash
cd /users/<NETID>/smt-gem5
git pull
chmod +x scripts/setup-phase2-parsec.sh
./scripts/setup-phase2-parsec.sh
```

If inputs are already prepared on node0 and only run directories are missing:

```bash
chmod +x scripts/copy-phase2-parsec-runs.sh
./scripts/copy-phase2-parsec-runs.sh node0
```

## Validity checks

For tests:

```text
returncode = 0
simulate() limit reached is OK
flush_smt should have flush_count > 0
constrained_smt log should show smt_resource_policy=partitioned
```

For final:

```text
returncode = 0
exit_cause = exiting with last active thread context
no_smt/unrestricted_smt/constrained_smt: flush_count = 0
flush_smt: flush_count > 0
```
