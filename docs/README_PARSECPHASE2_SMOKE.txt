Files:
  scripts/run_parsec_phase2_smoke.py
  scripts/parsec_phase2_smoke_config.json

Purpose:
  Smoke-test the Phase 2 gem5-side L1D flush mechanism on PARSEC swaptions + streamcluster.

Important path note:
  This config contains /users/akim2/smt-gem5 paths. Partners must replace /users/akim2 with their own CloudLab username/path.

Run from repo root:
  chmod +x scripts/run_parsec_phase2_smoke.py
  rm -rf results/parsec_phase2_smoke
  rm -f results/parsec_phase2_smoke.csv
  python3 scripts/run_parsec_phase2_smoke.py \
    --config scripts/parsec_phase2_smoke_config.json \
    --output-csv results/parsec_phase2_smoke.csv \
    2>&1 | tee results/parsec_phase2_smoke.log

Check:
  cat results/parsec_phase2_smoke.csv

Expected:
  all returncode values should be 0.
  flush cases should have flush_count > 0.
