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


def parse_stats(path: Path):
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


def sum_stats(stats, contains, endings):
    total = 0.0
    found = False
    for k, v in stats.items():
        if contains not in k:
            continue
        if any(k.endswith(e) for e in endings):
            total += v
            found = True
    return total if found else 0.0


def get_case_or_cfg(cfg, case, key, default=None):
    return case.get(key, cfg.get(key, default))


def build_cmd(cfg, case, outdir):
    max_ticks = get_case_or_cfg(cfg, case, "max_ticks", 3000000000)
    flush_every_ticks = int(get_case_or_cfg(cfg, case, "flush_every_ticks", 0) or 0)
    flush_scope = get_case_or_cfg(cfg, case, "flush_scope", "core0")
    flush_core = int(get_case_or_cfg(cfg, case, "flush_core", 0) or 0)

    cmd = [
        cfg["gem5_bin"],
        "--outdir=" + str(outdir),
        cfg["config_script"],
        "--num-cores", str(get_case_or_cfg(cfg, case, "num_cores", 1)),
        "--threads-per-core", str(get_case_or_cfg(cfg, case, "threads_per_core", 1)),
        "--mem-size", cfg.get("mem_size", "512MB"),
        "--cpu-clock", cfg.get("cpu_clock", "2GHz"),
        "--l1i-size", cfg.get("l1i_size", "32kB"),
        "--l1d-size", cfg.get("l1d_size", "32kB"),
        "--l2-size", cfg.get("l2_size", "512kB"),
        "--max-ticks", str(max_ticks),
    ]

    # Legacy / marker-based path. Keep this so older validation configs still run.
    if case.get("flush_on_workbegin", False):
        cmd.append("--flush-on-workbegin")
    if case.get("flush_all_cores", False):
        cmd.append("--flush-all-cores")

    # New gem5-controlled periodic cleanup path. Benchmarks do not need markers.
    if flush_every_ticks > 0:
        cmd += [
            "--flush-every-ticks", str(flush_every_ticks),
            "--flush-scope", str(flush_scope),
            "--flush-core", str(flush_core),
        ]

    for js in case["jobs"]:
        w = cfg["workloads"][js["workload"]]
        opts = js.get("options", w.get("options", ""))
        cmd += ["--job-cmd", w["cmd"], "--job-opts", opts, "--job-core", str(js["core"])]
    return cmd


def run_case(cfg, case):
    outdir = Path(cfg["results_root"]) / case["name"]
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = build_cmd(cfg, case, outdir)

    print("\n[RUN]", case["name"])
    print(" ".join(shlex.quote(x) for x in cmd), flush=True)
    t0 = time.time()
    proc = subprocess.run(cmd, cwd=cfg["repo_root"], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    wall = time.time() - t0

    log = proc.stdout or ""
    (outdir / "run.log").write_text(log, errors="ignore")
    print(log[-2500:], flush=True)
    print(f"[TIME] {wall:.2f}s returncode={proc.returncode}", flush=True)

    stats = parse_stats(outdir / "stats.txt")
    sim_insts = stats.get("simInsts", 0.0)
    sim_seconds = stats.get("simSeconds", 0.0)

    flush_count = 0
    m = re.search(r"DOMAIN_FLUSH_COUNT\s+(\d+)", log)
    if m:
        flush_count = int(m.group(1))

    work_items = 0.0
    for k, v in stats.items():
        if k.endswith("numWorkItemsStarted"):
            work_items += v

    l1d_accesses = sum_stats(stats, ".dcache.", [
        "demandAccesses::total", "demandAccesses", "overallAccesses::total", "overallAccesses"
    ])
    l1d_misses = sum_stats(stats, ".dcache.", [
        "demandMisses::total", "demandMisses", "overallMisses::total", "overallMisses"
    ])
    l2_accesses = sum_stats(stats, "l2", [
        "demandAccesses::total", "demandAccesses", "overallAccesses::total", "overallAccesses"
    ])
    l2_misses = sum_stats(stats, "l2", [
        "demandMisses::total", "demandMisses", "overallMisses::total", "overallMisses"
    ])

    exit_cause = ""
    m = re.findall(r"Final tick .* cause (.*)", log)
    if m:
        exit_cause = m[-1].strip()
    else:
        m = re.findall(r"Exit at tick .* because (.*)", log)
        if m:
            exit_cause = m[-1].strip()

    flush_every_ticks = int(get_case_or_cfg(cfg, case, "flush_every_ticks", 0) or 0)
    flush_scope = get_case_or_cfg(cfg, case, "flush_scope", "core0")
    flush_core = int(get_case_or_cfg(cfg, case, "flush_core", 0) or 0)
    marker_flush = bool(case.get("flush_on_workbegin", False))
    periodic_flush = flush_every_ticks > 0

    return {
        "name": case["name"],
        "policy": case.get("policy", case["name"]),
        "returncode": proc.returncode,
        "num_cores": get_case_or_cfg(cfg, case, "num_cores", 1),
        "threads_per_core": get_case_or_cfg(cfg, case, "threads_per_core", 1),
        "job_count": len(case["jobs"]),
        "flush_enabled": int(marker_flush or periodic_flush),
        "marker_flush_enabled": int(marker_flush),
        "periodic_flush_enabled": int(periodic_flush),
        "flush_every_ticks": flush_every_ticks,
        "flush_scope": flush_scope,
        "flush_core": flush_core,
        "flush_count": flush_count,
        "work_items_started": work_items,
        "simInsts": sim_insts,
        "simSeconds": sim_seconds,
        "throughput_inst_per_simsec": (sim_insts / sim_seconds) if sim_seconds else 0.0,
        "host_wallclock_sec": wall,
        "l1d_accesses": l1d_accesses,
        "l1d_misses": l1d_misses,
        "l1d_miss_rate": (l1d_misses / l1d_accesses) if l1d_accesses else 0.0,
        "l2_accesses": l2_accesses,
        "l2_misses": l2_misses,
        "l2_miss_rate": (l2_misses / l2_accesses) if l2_accesses else 0.0,
        "exit_cause": exit_cause,
        "outdir": str(outdir),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output-csv", required=True)
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    Path(cfg["results_root"]).mkdir(parents=True, exist_ok=True)

    rows = []
    for case in cfg["cases"]:
        rows.append(run_case(cfg, case))

    out = Path(args.output_csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print("\nWrote", out)


if __name__ == "__main__":
    main()
