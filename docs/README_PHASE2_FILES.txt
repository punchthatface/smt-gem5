Phase 2 flush-assisted SMT files

Copy these into repo root (/users/akim2/smt-gem5) preserving paths:

configs/smt_flush_cache.py
scripts/run_phase2_gem5.py
scripts/phase2_flush_config_smoke.json
scripts/phase2_flush_config.json
scripts/build-phase2-workloads.sh
workloads/src/phase2_victim.c
workloads/src/phase2_interferer.c

Then run:

cd /users/akim2/smt-gem5
chmod +x scripts/build-phase2-workloads.sh scripts/run_phase2_gem5.py
./scripts/build-phase2-workloads.sh

Smoke:
rm -rf results/phase2_flush_smoke
rm -f results/phase2_flush_smoke.csv
python3 scripts/run_phase2_gem5.py \
  --config scripts/phase2_flush_config_smoke.json \
  --output-csv results/phase2_flush_smoke.csv

Final:
tmux new -s phase2
cd /users/akim2/smt-gem5
rm -rf results/phase2_flush_final
rm -f results/phase2_flush_results.csv
python3 scripts/run_phase2_gem5.py \
  --config scripts/phase2_flush_config.json \
  --output-csv results/phase2_flush_results.csv

Detach with Ctrl+b then d.
