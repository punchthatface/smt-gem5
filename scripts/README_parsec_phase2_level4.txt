PARSEC Phase 2 Level 4 sweep configs.

These configs assume repo root /users/akim2/smt-gem5. Partners must replace this path with their own repo root.

Use parsec_phase2_level4_sweep_config.json for one-node all-cases run.
Use parsec_phase2_level4_node1_config.json and parsec_phase2_level4_node2_config.json to split across two CloudLab nodes.

All configs use:
  swaptions -ns 4 -sm 200 -nt 1 with fi 0/1/2/4
  streamcluster 10 20 32 256 256 50 none output.txt 1
  max_ticks = 20000000000

Run command template:
python3 scripts/run_parsec_phase2_smoke.py --config <config.json> --output-csv <output.csv> 2>&1 | tee <logfile.log>
