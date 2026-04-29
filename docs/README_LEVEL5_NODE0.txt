Level 5 node0 config for Phase 2 PARSEC shared-SMT flush-frequency sweep.

Copy parsec_phase2_level5_node0_config.json into:
  /users/akim2/smt-gem5/scripts/

Run from repo root:
  cd /users/akim2/smt-gem5
  rm -rf results/parsec_phase2_level5_node0
  rm -f results/parsec_phase2_level5_node0.csv
  python3 scripts/run_parsec_phase2_smoke.py \
    --config scripts/parsec_phase2_level5_node0_config.json \
    --output-csv results/parsec_phase2_level5_node0.csv \
    2>&1 | tee results/parsec_phase2_level5_node0.log

Recommended: run inside tmux.

This config assumes repo root:
  /users/akim2/smt-gem5

For another user/node path, replace /users/akim2/smt-gem5 in the JSON.
