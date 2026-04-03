# Quick gem5 Phase-1 starter

What this is:
- `run_phase1_gem5.py`: runs unrestricted SMT, no-SMT, and a quick constrained-SMT model.
- `phase1_config.example.json`: edit this with your gem5 paths and benchmark binaries.

Most important config knob:
- `no_smt_mode = "sequential_single_core"` means:
  unrestricted SMT is one physical core with 2 hardware threads, while no-SMT runs the pair one after the other on that same core.
  Pair throughput is computed as:
    (inst1 + inst2) / (time1 + time2)

- `no_smt_mode = "parallel_two_cores"` means:
  treat no-SMT as if each job had its own physical core.
  Pair throughput is computed as:
    (inst1 + inst2) / max(time1, time2)

Suggested workflow:
1. First, sanity check gem5 with a tiny static binary.
2. Then replace the example workload paths in the JSON with your real binaries.
3. Run:
   `python3 run_phase1_gem5.py --config phase1_config.example.json --output-csv phase1_results.csv`
4. Open the CSV and graph `throughput_inst_per_simsec` by `policy`.

Important:
- This is deliberately a *quick* constrained-SMT model for your baseline phase.
- On a single 2-thread SMT core, constrained SMT is only a distinct middle point when there are enough same-domain jobs to keep both siblings busy. If you only compare one cross-domain pair, constrained SMT collapses to no-SMT for that pair.
- Later, if you want Experiment 3 from your report (1x / 1.5x / 2x overcommitment), extend the driver so each run contains a queue of 3–4 jobs with domain labels instead of only one pair.

Benchmarks:
- Start with any CPU-bound statically linked binaries that run in SE mode.
- Once the flow works, swap in more standard workloads from PARSEC / GAPBS / SPEC as needed.
