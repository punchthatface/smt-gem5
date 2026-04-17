# isolation_constrained_smt_gem5

gem5-based infrastructure for the 18-742 / 15-742 project on SMT scheduling under security constraints.

## CloudLab setup

Use Ubuntu (latest, x86_64).

```bash
git clone https://github.com/punchthatface/smt-gem5.git
cd smt-gem5
./setup-cloudlab.sh
```

## PARSEC benchmarks

Currently validated benchmarks:
- swaptions
- streamcluster
- fluidanimate
- blackscholes
- canneal
- freqmine

Recommended experiment subset:
- Domain A: swaptions, blackscholes
- Domain B: streamcluster, canneal

## Running PARSEC

```bash
cd parsec
source ./env.sh

parsecmgmt -a build -p parsec.swaptions -c gcc-pthreads
parsecmgmt -a run   -p parsec.swaptions -c gcc-pthreads -i simsmall -n 1
```

## Running gem5 experiments

```bash
python3 scripts/run_phase1_gem5.py   --config scripts/phase1_config_real.json   --output-csv results/real_run.csv
```

## Notes

- Must run on x86_64 when using gem5 X86 build
- Verify binaries with `file <binary>`
- Update paths in config JSON files before running (replace akim2 with your path)
- Use tmux for long runs
