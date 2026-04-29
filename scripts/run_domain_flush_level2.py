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


def sum_matching(stats, contains, suffixes):
    total = 0.0
    found = False
    for k, v in stats.items():
        if contains not in k:
            continue
        if any(k.endswith(s) for s in suffixes):
            total += v
            found = True
    return total if found else 0.0


def build_base(cfg, outdir, num_cores, threads_per_core, max_ticks):
    return [
        cfg["gem5_bin"],
        "--outdir=" + str(outdir),
        cfg["config_script"],
        "--num-cores", str(num_cores),
        "--threads-per-core", str(threads_per_core),
        "--mem-size", cfg.get("mem_size", "512MB"),
        "--cpu-clock", cfg.get("cpu_clock", "2GHz"),
        "--l1i-size", cfg.get("l1i_size", "32kB"),
        "--l1d-size", cfg.get("l1d_size", "32kB"),
        "--l2-size", cfg.get("l2_size", "512kB"),
        "--max-ticks", str(max_ticks),
    ]


def add_job(cmd, job, core):
    cmd += [
        "--job-cmd", job["cmd"],
        "--job-opts", job.get("options", ""),
        "--job-core", str(core),
    ]


def run_case(cfg, case):
    outdir = Path(cfg["results_root"]) / case["name"]
    outdir.mkdir(parents=True, exist_ok=True)

    cmd = build_base(
        cfg,
        outdir,
        case["num_cores"],
        case["threads_per_core"],
        case.get("max_ticks", cfg.get("max_ticks", 1000000000)),
    )

    if case.get("flush_on_workbegin", False):
        cmd.append("--flush-on-workbegin")

    if case.get("flush_all_cores", False):
        cmd.append("--flush-all-cores")

    for job_spec in case["jobs"]:
        job = cfg["workloads"][job_spec["workload"]]
        add_job(cmd, job, job_spec["core"])

    print("\n[RUN]", case["name"])
    print(" ".join(shlex.quote(x) for x in cmd))

    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=cfg["repo_root"],
        text=True,
        capture_output=True,
    )
    wall = time.time() - t0

    stdout = proc.stdout + "\n" + proc.stderr

    log_path = outdir / "run.log"
    log_path.write_text(stdout)

    print(stdout[-2000:])
    if proc.returncode != 0:
        print("[ERROR] returncode =", proc.returncode)

    stats = parse_stats(outdir / "stats.txt")

    flush_count = 0
    m = re.search(r"DOMAIN_FLUSH_COUNT\s+(\d+)", stdout)
    if m:
        flush_count = int(m.group(1))

    sim_insts = stats.get("simInsts", 0.0)
    sim_seconds = stats.get("simSeconds", 0.0)

    # Works for both single CPU naming:
    #   system.cpu.dcache...
    # and multicore list naming:
    #   system.cpu0.dcache...
    #   system.cpu1.dcache...
    l1d_accesses = sum_matching(
        stats,
        ".dcache.",
        ["demandAccesses::total", "demandAccesses", "overallAccesses::total", "overallAccesses"],
    )
    l1d_misses = sum_matching(
        stats,
        ".dcache.",
        ["demandMisses::total", "demandMisses", "overallMisses::total", "overallMisses"],
    )

    l1d_miss_rate = (l1d_misses / l1d_accesses) if l1d_accesses else 0.0

    return {
        "name": case["name"],
        "policy": case["policy"],
        "returncode": proc.returncode,
        "num_cores": case["num_cores"],
        "threads_per_core": case["threads_per_core"],
        "job_count": len(case["jobs"]),
        "flush_enabled": int(case.get("flush_on_workbegin", False)),
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

    rows = []
    for case in cfg["cases"]:
        rows.append(run_case(cfg, case))

    out = Path(args.output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\nWrote", out)


if __name__ == "__main__":
    main()