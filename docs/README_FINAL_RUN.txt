Final Phase 2 overnight configs.

node0: swaptions + streamcluster
node1: swaptions + blackscholes

Both run:
- no-SMT separate-core baseline
- shared SMT no-flush baseline
- shared SMT with gem5-side L1D flush at fi=1,2,4

Workload:
- swaptions: -ns 4 -sm 2000 -nt 1
- node0 streamcluster: 10 20 32 512 512 100 none output.txt 1
- node1 blackscholes: 1 /users/akim2/smt-gem5/parsec/pkgs/apps/blackscholes/run/in_4K.txt blackscholes.out

Expected result plots:
1. normalized throughput by policy, grouped by co-runner
2. L1D miss rate by policy / fi interval
3. L2 miss rate by policy / fi interval
4. flush_count vs fi interval
5. no-SMT vs shared SMT comparison for each co-runner
