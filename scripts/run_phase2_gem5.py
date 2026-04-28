#!/usr/bin/env python3
import json, csv, re, subprocess, time
from pathlib import Path

STAT_RE = re.compile(r"^(\S+)\s+([-+0-9.eE]+)")

def parse_stats(path):
    stats = {}
    try:
        with open(path) as f:
            for line in f:
                m = STAT_RE.match(line.strip())
                if m:
                    try: stats[m.group(1)] = float(m.group(2))
                    except: pass
    except: pass
    return stats

def summarize(stats):
    insts = stats.get("simInsts", 0)
    secs  = stats.get("simSeconds", 0)
    return {
        "simInsts": insts,
        "simSeconds": secs,
        "throughput": insts/secs if secs else 0,
        "ipc": stats.get("system.cpu0.ipc", 0),
    }

def run_gem5(cfg, policy, w1, w2, outdir, flush_penalty=0):
    Path(outdir).mkdir(parents=True, exist_ok=True)
    cmd = [
        cfg["gem5_bin"],
        f"--outdir={outdir}",
        cfg["config_script"],
        "--policy", policy,
        "--cmd1", w1["cmd"],
        "--opts1", w1.get("options", ""),
        "--cmd2", w2["cmd"],
        "--opts2", w2.get("options", ""),
        "--num-cores", str(cfg.get("num_cores", 4)),
        "--mem-size", cfg["mem_size"],
        "--cpu-clock", cfg["cpu_clock"],
        "--max-ticks", str(cfg["max_ticks"]),
    ]
    if policy == "flush_assisted":
        cmd += ["--flush-penalty", str(flush_penalty),
                "--switch-interval", str(cfg["switch_interval"])]

    label = f"{policy}" + (f" penalty={flush_penalty}" if policy == "flush_assisted" else "")
    print(f"\n[RUN] {label}")
    print(" ".join(cmd))
    start = time.time()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start
    print(f"[TIME] {elapsed:.1f}s  rc={proc.returncode}")
    if proc.returncode != 0:
        print(f"STDERR: {proc.stderr[-500:]}")

    sp = Path(outdir) / "stats.txt"
    res = {"returncode": proc.returncode, "elapsed": elapsed}
    if sp.exists():
        res.update(summarize(parse_stats(sp)))
    return res

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-csv", required=True)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    output_csv_path = args.output_csv
    results_root = Path(cfg["results_root"])
    results_root.mkdir(parents=True, exist_ok=True)

    workloads = cfg["workloads"]
    fieldnames = ["pair","policy","flush_penalty","simInsts","simSeconds",
                  "throughput","ipc","elapsed","returncode"]
    rows = []

    for pair in cfg["pairs"]:
        name = pair["name"]
        w1 = workloads[pair["w1"]]
        w2 = workloads[pair["w2"]]

        for policy in ["no_smt", "unrestricted_smt"]:
            outdir = str(results_root / name / policy)
            r = run_gem5(cfg, policy, w1, w2, outdir)
            rows.append({"pair":name,"policy":policy,"flush_penalty":0,**r})

        for penalty in cfg["flush_penalties"]:
            outdir = str(results_root / name / f"flush_{penalty}")
            r = run_gem5(cfg, "flush_assisted", w1, w2, outdir, penalty)
            rows.append({"pair":name,"policy":"flush_assisted","flush_penalty":penalty,**r})

    output = Path(output_csv_path)
    with open(output, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n[DONE] {output}")

if __name__ == "__main__":
    main()
