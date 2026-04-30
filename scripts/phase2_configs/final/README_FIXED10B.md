# Fixed-window 10B final configs

Reduced fixed-window configs to improve chance of finishing before the deadline.

Scope is unchanged:
- 8 PARSEC workloads
- 4 policies
- 4-core / 8-thread SMT cases
- 6 placement mixes across node0-node5

Changes:
- max_ticks = 10,000,000,000
- flush_every_ticks = 1,000,000,000

This keeps the same qualitative experiment and gives about 9 periodic flushes in the flush_smt case.
`simulate() limit reached` is expected and valid for this fixed-window final.
