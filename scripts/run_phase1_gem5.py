#!/usr/bin/env python3
import argparse
import csv
import json
import re
import shlex
import subprocess
from pathlib import Path
import time

STAT_RE = re.compile(r"^(\S+)\s+([-+0-9.eE]+)")

def ensure_dir(p):
    p.mkdir(parents=True, exist_ok=True)

def parse_stats(stats_path):
    stats = {}
    with open(stats_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = STAT_RE.match(line.strip())
            if not m:
                continue
            try:
                stats[m.group(1)] = float(m.group(2))
            except ValueError:
                pass
    return stats

def summarize(stats):
    insts = stats.get("simInsts", 0.0)
    secs  = stats.get("simSeconds", 0.0)
    return {
        "simInsts": insts,
        "simSeconds": secs,
        "hostSeconds": stats.get("hostSeconds", 0.0),
        "throughput_inst_per_simsec": (insts / secs) if secs else 0.0,
    }

def run_gem5(cfg, policy, w1, w2, outdir, label):
    ensure_dir(outdir)
    cmd = [
        cfg["gem5_bin"],
        "--outdir=" + str(outdir),
        cfg["config_script"],
        "--policy", policy,
        "--cmd1", w1["cmd"],
        "--opts1", w1.get("options", ""),
        "--cmd2", w2["cmd"],
        "--opts2", w2.get("options", ""),
        "--num-cores", str(cfg.get("num_cores", 4)),
        "--mem-size", cfg.get("mem_size", "512MB"),
        "--cpu-clock", cfg.get("cpu_clock", "2GHz"),
    ]
    if int(cfg.get("max_ticks", 0)) > 0:
        cmd += ["--max-ticks", str(cfg["max_ticks"])]

    print(f"\n[RUN] {label}")
    print(" ".join(shlex.quote(x) for x in cmd))
    start = time.time()
    proc = subprocess.run(cmd, cwd=cfg["repo_root"], capture_output=True, text=True)
    elapsed = time.time() - start
    print(f"[TIME] {elapsed:.2f}s  returncode={proc.returncode}")

    res = {
        "returncode": proc.returncode,
        "run_cmd": " ".join(shlex.quote(x) for x in cmd),
        "stats_path": str(outdir / "stats.txt"),
    }
    sp = outdir / "stats.txt"
    if sp.exists():
        res.update(summarize(parse_stats(sp)))
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-csv", required=True)
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    output_csv = Path(args.output_csv).resolve()
    ensure_dir(output_csv.parent)
    results_root = Path(cfg["results_root"]).resolve()
    ensure_dir(results_root)

    workloads = cfg["workloads"]
    fieldnames = [
        "pair_name", "policy", "w1", "w2", "domain1", "domain2",
        "returncode", "simInsts", "simSeconds", "hostSeconds",
        "throughput_inst_per_simsec", "stats_path", "run_cmd"
    ]
    rows = []

    for pair in cfg["pairs"]:
        name = pair["name"]
        w1 = workloads[pair["w1"]]
        w2 = workloads[pair["w2"]]
        d1, d2 = w1["domain"], w2["domain"]

        for policy in ["no_smt", "unrestricted_smt", "constrained_smt"]:
            outdir = results_root / name / policy
            r = run_gem5(cfg, policy, w1, w2, outdir, f"{name} :: {policy}")
            rows.append({
                "pair_name": name,
                "policy": policy,
                "w1": pair["w1"], "w2": pair["w2"],
                "domain1": d1, "domain2": d2,
                "returncode": r.get("returncode", -1),
                "simInsts": r.get("simInsts", ""),
                "simSeconds": r.get("simSeconds", ""),
                "hostSeconds": r.get("hostSeconds", ""),
                "throughput_inst_per_simsec": r.get("throughput_inst_per_simsec", ""),
                "stats_path": r.get("stats_path", ""),
                "run_cmd": r.get("run_cmd", ""),
            })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[DONE] Wrote {len(rows)} rows to {output_csv}")

if __name__ == "__main__":
    main()
