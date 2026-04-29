# PARSEC Phase 2 Level 5 Short Split

This is a shortened split-node pilot/final-ish run.

Workload:
- swaptions: -ns 4 -sm 500 -nt 1
- streamcluster: 10 20 32 256 256 50 none output.txt 1

Cases:
- node0: fi0 and fi1
- node1: fi2 and fi4

Notes:
- fi0 is no flush, so flush_on_workbegin is disabled.
- fi1/fi2/fi4 enable gem5-side L1D writeback+invalidate at swaptions m5 work markers.
- Paths contain /users/akim2/smt-gem5 and must be changed for other users.
