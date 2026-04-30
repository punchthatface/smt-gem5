# Final 8-workload / 4-policy Phase 2 configs

These are the final long-running configs for the report/presentation.

## What this experiment is

This is the final architecture-aware SMT scheduling experiment:

- 8 unmodified PARSEC workload instances
- no benchmark marker patching
- gem5 SE mode
- 4 policies:
  1. no-SMT isolation
  2. unrestricted SMT
  3. constrained SMT using O3 SMT resource policy
  4. SMT with periodic L1D cleanup

## Policies

### no_smt_8c1t
- 8 physical cores
- 1 thread per core
- 8 workloads
- No SMT sibling sharing.
- This is the isolation baseline.

### unrestricted_smt_4c8t
- 4 physical cores
- 2 SMT threads per core
- 8 workloads
- Default gem5 O3 SMT behavior.

### constrained_smt_4c8t_resource_partitioned
- 4 physical cores
- 2 SMT threads per core
- 8 workloads
- Uses gem5 O3 SMT resource policy:
  - smtFetchPolicy = RoundRobin
  - smtCommitPolicy = RoundRobin
  - smtROBPolicy = Partitioned
  - smtLSQPolicy = Partitioned
- smtIQPolicy was tested and is not supported by this gem5 build.

### flush_smt_4c8t_periodic_l1d
- 4 physical cores
- 2 SMT threads per core
- 8 workloads
- Same placement as unrestricted SMT
- Periodic L1D cleanup every 2,000,000,000 simulated ticks:
  - dcache.memWriteback()
  - dcache.memInvalidate()

## Node configs

Place these files under:

```text
scripts/phase2_configs/final/
```

Node assignment:

```text
node0 -> final_8workload_4policy_node0_config.json
node1 -> final_8workload_4policy_node1_config.json
node2 -> final_8workload_4policy_node2_config.json
node3 -> final_8workload_4policy_node3_config.json
node4 -> final_8workload_4policy_node4_config.json
node5 -> final_8workload_4policy_node5_config.json
```

Each node uses the same 8 workloads and 4 policies, but different SMT co-location pairings for the 4-core SMT cases.

## Run command

On nodeX:

```bash
cd /users/akim2/smt-gem5
mkdir -p results/final

tmux new -s final
```

Inside tmux:

```bash
python3 scripts/run_phase2_experiment.py \
  --config scripts/phase2_configs/final/final_8workload_4policy_nodeX_config.json \
  --output-csv results/final/8workload_4policy_nodeX.csv \
  2>&1 | tee results/final/8workload_4policy_nodeX.log
```

Detach:

```text
Ctrl+b then d
```

## Final validity checks

After completion:

```bash
cat results/final/8workload_4policy_nodeX.csv

grep "smt_resource_policy\|applied_smt_params\|DOMAIN_FLUSH_COUNT\|Final tick" \
  results/final/8workload_4policy_nodeX.log
```

Expected:
- all `returncode = 0`
- final rows should ideally end with `exiting with last active thread context`
- no_smt/unrestricted_smt/constrained_smt: `flush_count = 0`
- flush_smt: `flush_count > 0`
- constrained_smt logs should show `smt_resource_policy=partitioned`
- constrained_smt logs should show applied fetch/commit/ROB/LSQ policy params
