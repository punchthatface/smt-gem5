# Phase 2 vips/no-bodytrack fixed20B bundle

Keep these files:

- `scripts/run_phase2_experiment.py`: patched runner with `detected_failure`, `failure_reason`, incremental CSV writing, and `--stop-on-detected-failure`.
- `configs/smt_domain_flush.py`: current gem5 config.
- `scripts/setup-phase2-parsec-vips.sh`: builds/prepares final workload set with `vips` and without `bodytrack`.
- `scripts/copy-phase2-parsec-runs-vips.sh`: copies run input dirs including `vips` and excluding `bodytrack`.
- `scripts/phase2_configs/test/vips_node0_smoke_1b_config.json`: node0 quick 1B unrestricted-SMT smoke.
- `scripts/phase2_configs/test/vips_node0_validation_5b_config.json`: node0 5B all-policy validation.
- `scripts/phase2_configs/final/fixed20b_vips_8workload_4policy_node*.json`: final configs.

Benchmark choice:
- Replaces `bodytrack` with `vips`.
- Uses `IM_CONCURRENCY=1` so `vips` acts as one workload/domain.

Tick policy:
- Final `max_ticks = 20,000,000,000`.
- `flush_every_ticks = 1,000,000,000`.
- Expected `flush_smt` count for fixed20B is about 19.

Run order:
1. Install/copy these files into the repo.
2. Build/prepare `vips` on node0 with `setup-phase2-parsec-vips.sh`.
3. Run native `vips` sanity.
4. Run node0 1B smoke.
5. Run node0 5B all-policy validation.
6. Run node0 final 20B.
7. Only after node0 passes, copy/setup to node1-node5 and run final configs there.
