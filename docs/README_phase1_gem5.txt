# Quick gem5 Phase-1 starter

What this is:
- `scripts/run_phase1_gem5.py`: runs unrestricted SMT, no-SMT, and a quick constrained-SMT baseline model.
- `configs/smt_baseline.py`: custom gem5 SE-mode config for 1-thread and 2-thread runs on one O3 CPU.
- `scripts/phase1_config_smoke.json`: bounded smoke-test config.
- `scripts/phase1_config_pilot.json`: bounded pilot config for faster iteration.
- `scripts/phase1_config_real.json`: larger bounded config used for the current baseline runs.

Policy model:
- `unrestricted_smt`:
  run two workloads together on one SMT-enabled core.

- `no_smt`:
  run each workload alone on one non-SMT core, then aggregate:
    pair throughput = (inst1 + inst2) / (time1 + time2)

- `constrained_smt` (current quick baseline):
  - same-domain pair -> same as unrestricted SMT
  - cross-domain pair -> same as no-SMT

Important implication:
- In the current pair-based Phase-1 model, constrained SMT is not a separate scheduler.
- It is a policy rule:
  - same-domain pair -> behaves like unrestricted SMT
  - cross-domain pair -> behaves like no-SMT
- Therefore, in pairwise experiments, constrained SMT will often exactly match one of the other two policies.

Current workload setup:
- Use PARSEC binaries under:
  `parsec/pkgs/...`
- The maintained PARSEC checkout should live at:
  `smt-gem5/parsec`
- Do not rely on the older broken PARSEC checkout that lacked working simsmall inputs.

Current baseline benchmark set:
- Domain A:
  - `swaptions`
  - `blackscholes`
- Domain B:
  - `streamcluster`
  - `canneal`

Smoke / pilot / real configs:
- Smoke:
  - for basic pipeline validation
  - uses smaller workload arguments
  - uses a hard `max_ticks` cap
- Pilot:
  - still capped
  - longer than smoke
  - used to sanity-check trends before long runs
- Real:
  - current reported baseline config
  - also bounded by `max_ticks` to keep runtime manageable

Most important runtime knob:
- `max_ticks` in the JSON config is forwarded to `configs/smt_baseline.py`
- This bounds runtime and is the main control for keeping gem5 runs manageable
- If runs are too long, lower `max_ticks`
- If runs are too short to be meaningful, raise `max_ticks`

Suggested workflow:
1. First verify gem5 itself with:
   `scripts/run-smoke.sh`

2. Then verify PARSEC binaries natively:
   - source `parsec/env.sh`
   - run the target benchmark with `parsecmgmt -a run ... -i simsmall -n 1`

3. Then run the bounded smoke config:
   `python3 scripts/run_phase1_gem5.py --config scripts/phase1_config_smoke.json --output-csv results/smoke_run.csv`

4. Then run the pilot config:
   `python3 scripts/run_phase1_gem5.py --config scripts/phase1_config_pilot.json --output-csv results/pilot_run.csv`

5. Then run the real baseline config:
   `python3 scripts/run_phase1_gem5.py --config scripts/phase1_config_real.json --output-csv results/real_run.csv`

6. Open the CSV and graph:
   `throughput_inst_per_simsec`
   by `policy` and `pair_name`

Expected Phase-1 behavior:
- Same-domain pair:
  unrestricted SMT ~= constrained SMT > no-SMT

- Cross-domain pair:
  unrestricted SMT > constrained SMT ~= no-SMT

Why this happens:
- This is the intended behavior of the current constrained-SMT baseline model, not a bug.

Current limitation:
- Pairwise experiments alone make constrained SMT collapse to one extreme or the other.
- To make constrained SMT appear as a more distinct middle point, extend the experiment from one pair to a queued multi-job case (for example A1, A2, B1).

Important:
- This is deliberately a quick baseline model for the characterization phase.
- It is suitable for showing the isolation/utilization tradeoff before adding more advanced architectural mechanisms.
- Long gem5 runs are normal; use `tmux` for pilot/real experiments.