# isolation_constrained_smt_gem5

gem5-based infrastructure for the 18-742 project on SMT scheduling under security constraints.

The project studies the performance/security tradeoff between unrestricted SMT, no-SMT / separate-core execution, and a Phase 2 gem5-side L1D cleanup mechanism triggered at marked work/domain boundaries.

## Repository layout

```text
configs/
  smt_domain_flush.py

scripts/
  run_parsec_phase2_smoke.py
  phase2_configs/
    parsec_phase2_final_node0_config.json
    parsec_phase2_final_node1_config.json

patches/
  swaptions/
    HJM_Securities.cpp
    Makefile
    README.md

docs/
  README_phase2_domain_flush.md
  PHASE2_HANDOFF.txt
```

Generated or external directories are intentionally not tracked:

```text
gem5/
parsec/
results/
workloads/bin/
```

## CloudLab setup

Use Ubuntu x86_64.

```bash
git clone https://github.com/punchthatface/smt-gem5.git
cd smt-gem5
./setup-cloudlab.sh
```

The setup creates/builds local `gem5/` and `parsec/` trees. These are large generated/external directories and should not be committed.

## PARSEC benchmarks used

The final Phase 2 experiments use:

- `swaptions` as the protected / marker-emitting workload
- `streamcluster` as one co-runner
- `blackscholes` as a second co-runner

Other PARSEC benchmarks may be built for additional experiments, but the final configs currently target the two pairs above.

## Phase 2 mechanism

The Phase 2 implementation uses gem5-side L1D cleanup.

1. PARSEC `swaptions` is patched to support a new option:

   ```bash
   -fi N
   ```

   where:

   ```text
   -fi 0  = no gem5 markers / no flush
   -fi 1  = emit a marker every swaption
   -fi 2  = emit a marker every 2 swaptions
   -fi 4  = emit a marker every 4 swaptions
   ```

2. `swaptions` emits gem5 `m5_work_begin` markers. The application does not directly flush cache lines.

3. gem5 exits at those markers. The Python runner/config then performs L1D cleanup using gem5 cache methods:

   ```python
   dcache.memWriteback()
   dcache.memInvalidate()
   ```

4. Simulation resumes after each cleanup event.

This models L1D cache cleanup at work/domain boundaries. It does not claim to implement full SMT security or SecSMT-style partitioning of all shared structures.

## Applying the swaptions patch

After running setup, copy the files from `patches/swaptions/` into the PARSEC swaptions source tree.

From repo root:

```bash
cp patches/swaptions/HJM_Securities.cpp \
  parsec/pkgs/apps/swaptions/src/HJM_Securities.cpp

cp patches/swaptions/Makefile \
  parsec/pkgs/apps/swaptions/src/Makefile
```

The patched Makefile may contain absolute paths such as:

```text
/users/akim2/smt-gem5
```

Replace that with the local repo path before rebuilding, for example:

```bash
sed -i "s#/users/akim2/smt-gem5#/users/<NETID>/smt-gem5#g" \
  parsec/pkgs/apps/swaptions/src/Makefile
```

Build the gem5 m5ops library:

```bash
cd /users/<NETID>/smt-gem5/gem5/util/m5
scons build/x86/out/libm5.a
```

Rebuild swaptions:

```bash
cd /users/<NETID>/smt-gem5/parsec
. env.sh

rm -rf pkgs/apps/swaptions/obj/amd64-linux.gcc-pthreads
rm -rf pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads

parsecmgmt -a build -p parsec.swaptions -c gcc-pthreads
```

Verify:

```bash
file /users/<NETID>/smt-gem5/parsec/pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads/bin/swaptions
```

Expected: `statically linked`.

Native sanity check:

```bash
/users/<NETID>/smt-gem5/parsec/pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads/bin/swaptions \
  -ns 2 -sm 100 -nt 1 -fi 0
```

Expected output includes:

```text
Phase2 gem5 work marker interval: 0
```

Do not run nonzero `-fi` natively. Nonzero `-fi` emits gem5 pseudo-instructions and should be used inside gem5 only.

## Building blackscholes input support

If `blackscholes` is missing:

```bash
cd /users/<NETID>/smt-gem5/parsec
. env.sh
parsecmgmt -a build -p parsec.blackscholes -c gcc-pthreads
```

The final node1 config expects:

```text
parsec/pkgs/apps/blackscholes/run/in_4K.txt
```

If needed, copy the `blackscholes/run/` directory from a node where it exists.

Native sanity check:

```bash
cd /users/<NETID>/smt-gem5
./parsec/pkgs/apps/blackscholes/inst/amd64-linux.gcc-pthreads/bin/blackscholes \
  1 parsec/pkgs/apps/blackscholes/run/in_4K.txt blackscholes.out
```

Expected exit code: `0`.

## Final Phase 2 runs

Final configs:

```text
scripts/phase2_configs/parsec_phase2_final_node0_config.json
scripts/phase2_configs/parsec_phase2_final_node1_config.json
```

Node assignment:

```text
node0: swaptions + streamcluster
node1: swaptions + blackscholes
```

Each final config runs:

```text
1. no-SMT separate-core baseline
2. shared SMT no flush
3. shared SMT flush fi1
4. shared SMT flush fi2
5. shared SMT flush fi4
```

Run node0:

```bash
cd /users/<NETID>/smt-gem5

python3 scripts/run_parsec_phase2_smoke.py \
  --config scripts/phase2_configs/parsec_phase2_final_node0_config.json \
  --output-csv results/parsec_phase2_final_node0.csv \
  2>&1 | tee results/parsec_phase2_final_node0.log
```

Run node1:

```bash
cd /users/<NETID>/smt-gem5

python3 scripts/run_parsec_phase2_smoke.py \
  --config scripts/phase2_configs/parsec_phase2_final_node1_config.json \
  --output-csv results/parsec_phase2_final_node1.csv \
  2>&1 | tee results/parsec_phase2_final_node1.log
```

For long runs, use tmux:

```bash
tmux new -s final
```

Detach without stopping the run:

```text
Ctrl+b then d
```

Reattach:

```bash
tmux attach -t final
```

## Result validity checks

A valid final row should have:

```text
returncode = 0
exit_cause = exiting with last active thread context
```

Expected flush counts:

```text
no flush / fi0: flush_count = 0
fi1:           flush_count > fi2
fi2:           flush_count > fi4
fi4:           flush_count > 0
```

The CSV output includes:

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

## Plots supported

The final CSVs support:

- normalized throughput by policy
- no-SMT separate-core vs shared SMT comparison
- L1D miss rate by policy / flush interval
- L2 miss rate by policy / flush interval
- flush count vs flush interval
- comparison across two PARSEC co-runners

## Notes

- Must run on x86_64 when using gem5 X86 build.
- Verify binaries with `file <binary>`.
- Replace `/users/akim2/smt-gem5` in config/Makefile paths with the local repo path.
- Keep `parsec/`, `gem5/`, `results/`, and generated binaries out of git.
