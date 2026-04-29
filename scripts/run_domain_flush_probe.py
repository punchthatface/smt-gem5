#!/usr/bin/env python3
import argparse
import csv
import json
import re
import shlex
import subprocess
import time
from pathlib import Path

STAT_RE = re.compile(r"^(\S+)\s+([-+0-9.eE]+)")

def parse_stats(path):
    stats = {}
    if not path.exists():
        return stats
    for line in path.read_text(errors="ignore").splitlines():
        m = STAT_RE.match(line.strip())
        if not m:
            continue
        try:
            stats[m.group(1)] = float(m.group(2))
        except ValueError:
            pass
    return stats

def first_stat(stats, names, default=0.0):
    for name in names:
        if name in stats:
            return stats[name]
    return default

def run_one(cfg, name, flush_enabled):
    outdir = Path(cfg["results_root"]) / name
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [
        cfg["gem5_bin"],
        "--outdir=" + str(outdir),
        cfg["config_script"],
        "--num-cores", str(cfg.get("num_cores", 1)),
        "--threads-per-core", str(cfg.get("threads_per_core", 1)),
        "--mem-size", cfg.get("mem_size", "512MB"),
        "--cpu-clock", cfg.get("cpu_clock", "2GHz"),
        "--l1i-size", cfg.get("l1i_size", "32kB"),
        "--l1d-size", cfg.get("l1d_size", "32kB"),
        "--l2-size", cfg.get("l2_size", "512kB"),
        "--max-ticks", str(cfg.get("max_ticks", 1000000000)),
        "--job-cmd", cfg["workload"]["cmd"],
        "--job-opts", cfg["workload"].get("options", ""),
        "--job-core", "0",
    ]
    if flush_enabled:
        cmd.insert(cmd.index("--job-cmd"), "--flush-on-workbegin")

    print("\n[RUN]", name)
    print(" ".join(shlex.quote(x) for x in cmd))
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=cfg["repo_root"], text=True, capture_output=True)
    wall = time.time() - t0
    print(proc.stdout[-2000:])
    if proc.returncode != 0:
        print(proc.stderr[-4000:])

    stats = parse_stats(outdir / "stats.txt")
    stdout = proc.stdout + "\n" + proc.stderr
    flush_count = 0
    m = re.search(r"DOMAIN_FLUSH_COUNT\s+(\d+)", stdout)
    if m:
        flush_count = int(m.group(1))

    sim_insts = stats.get("simInsts", 0.0)
    sim_seconds = stats.get("simSeconds", 0.0)
    l1d_accesses = first_stat(stats, [
        "system.cpu.dcache.demandAccesses::total",
        "system.cpu.dcache.demandAccesses",
    ])
    l1d_misses = first_stat(stats, [
        "system.cpu.dcache.demandMisses::total",
        "system.cpu.dcache.demandMisses",
    ])
    l1d_miss_rate = (l1d_misses / l1d_accesses) if l1d_accesses else 0.0

    return {
        "name": name,
        "returncode": proc.returncode,
        "flush_enabled": int(flush_enabled),
        "flush_count": flush_count,
        "simInsts": sim_insts,
        "simSeconds": sim_seconds,
        "throughput_inst_per_simsec": (sim_insts / sim_seconds) if sim_seconds else 0.0,
        "host_wallclock_sec": wall,
        "l1d_accesses": l1d_accesses,
        "l1d_misses": l1d_misses,
        "l1d_miss_rate": l1d_miss_rate,
        "outdir": str(outdir),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-csv", required=True)
    args = ap.parse_args()
    cfg = json.loads(Path(args.config).read_text())

    rows = [
        run_one(cfg, "domain_switch_no_flush", False),
        run_one(cfg, "domain_switch_l1d_flush", True),
    ]

    out = Path(args.output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("Wrote", out)

if __name__ == "__main__":
    main()
