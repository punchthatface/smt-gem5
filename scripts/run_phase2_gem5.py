#!/usr/bin/env python3
"""
Phase 2 gem5 driver for cache-aware flush-assisted SMT experiments.

This runner does NOT fake flushing with penalty ticks. It runs binaries that can
execute real x86 CLFLUSH instructions and compares:
  - victim solo
  - victim + interferer on the same SMT core
  - victim + interferer on separate cores
  - victim + interferer on same SMT core with several victim flush intervals
"""

import argparse
import csv
import json
import re
import shlex
import subprocess
import time
from pathlib import Path

STAT_RE = re.compile(r"^(\S+)\s+([-+0-9.eE]+)")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def parse_stats(stats_path: Path):
    stats = {}
    if not stats_path.exists():
        return stats
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


def sum_matching(stats, required_terms, forbidden_terms=None):
    forbidden_terms = forbidden_terms or []
    total = 0.0
    matched = []
    for key, value in stats.items():
        lk = key.lower()
        if all(term.lower() in lk for term in required_terms) and not any(
            term.lower() in lk for term in forbidden_terms
        ):
            total += value
            matched.append(key)
    return total, matched


def cache_summary(stats):
    # gem5 stat names vary across versions/configs. Prefer precise classic-cache
    # totals, then fall back to broader matching.
    l1d_accesses, l1d_access_keys = sum_matching(stats, ["dcache", "overallaccesses::total"])
    if not l1d_access_keys:
        l1d_accesses, l1d_access_keys = sum_matching(stats, ["dcache", "accesses"], ["miss", "hit"])

    l1d_misses, l1d_miss_keys = sum_matching(stats, ["dcache", "overallmisses::total"])
    if not l1d_miss_keys:
        l1d_misses, l1d_miss_keys = sum_matching(stats, ["dcache", "misses"], ["rate"])

    l2_accesses, l2_access_keys = sum_matching(stats, ["l2cache", "overallaccesses::total"])
    if not l2_access_keys:
        l2_accesses, l2_access_keys = sum_matching(stats, ["l2cache", "accesses"], ["miss", "hit"])

    l2_misses, l2_miss_keys = sum_matching(stats, ["l2cache", "overallmisses::total"])
    if not l2_miss_keys:
        l2_misses, l2_miss_keys = sum_matching(stats, ["l2cache", "misses"], ["rate"])

    return {
        "l1d_accesses": l1d_accesses,
        "l1d_misses": l1d_misses,
        "l1d_miss_rate": (l1d_misses / l1d_accesses) if l1d_accesses else 0.0,
        "l2_accesses": l2_accesses,
        "l2_misses": l2_misses,
        "l2_miss_rate": (l2_misses / l2_accesses) if l2_accesses else 0.0,
        "l1d_access_keys": ";".join(l1d_access_keys[:4]),
        "l1d_miss_keys": ";".join(l1d_miss_keys[:4]),
        "l2_access_keys": ";".join(l2_access_keys[:4]),
        "l2_miss_keys": ";".join(l2_miss_keys[:4]),
    }


def summarize(stats):
    insts = stats.get("simInsts", 0.0)
    secs = stats.get("simSeconds", 0.0)
    base = {
        "simInsts": insts,
        "simSeconds": secs,
        "hostSeconds": stats.get("hostSeconds", 0.0),
        "throughput_inst_per_simsec": (insts / secs) if secs else 0.0,
    }
    base.update(cache_summary(stats))
    return base


class Progress:
    def __init__(self, total):
        self.total = total
        self.done = 0

    def start(self, label):
        idx = self.done + 1
        pct = (idx / self.total) * 100 if self.total else 100.0
        print(f"\n[PROGRESS] [{idx}/{self.total} | {pct:5.1f}%] {label}")

    def finish(self):
        self.done += 1


def build_base(cfg, exp, outdir):
    cmd = [
        cfg["gem5_bin"],
        "--outdir=" + str(outdir),
        cfg["config_script"],
        "--num-cores", str(exp["num_cores"]),
        "--threads-per-core", str(exp["threads_per_core"]),
        "--mem-size", cfg.get("mem_size", "512MB"),
        "--cpu-clock", cfg.get("cpu_clock", "2GHz"),
        "--l1i-size", cfg.get("l1i_size", "32kB"),
        "--l1d-size", cfg.get("l1d_size", "32kB"),
        "--l2-size", cfg.get("l2_size", "512kB"),
    ]
    max_ticks = int(exp.get("max_ticks", cfg.get("max_ticks", 0)))
    if max_ticks > 0:
        cmd += ["--max-ticks", str(max_ticks)]
    return cmd


def append_job(cmd, workload, core_id, flush_interval=None):
    opts = workload.get("options", "")
    if flush_interval is not None:
        opts = (opts + f" --flush-interval {flush_interval}").strip()
    cmd += ["--job-cmd", workload["cmd"]]
    cmd += ["--job-opts", opts]
    cmd += ["--job-core", str(core_id)]
    return cmd


def make_experiment_command(cfg, exp, outdir):
    workloads = cfg["workloads"]
    victim = workloads[exp.get("victim", "victim")]
    interferer = workloads.get(exp.get("interferer", "interferer"))
    layout = exp["layout"]
    flush_interval = exp.get("flush_interval", 0)

    cmd = build_base(cfg, exp, outdir)

    if layout == "solo":
        append_job(cmd, victim, 0, flush_interval)
    elif layout == "shared_smt":
        append_job(cmd, victim, 0, flush_interval)
        append_job(cmd, interferer, 0, None)
    elif layout == "split_core":
        append_job(cmd, victim, 0, flush_interval)
        append_job(cmd, interferer, 1, None)
    else:
        raise RuntimeError(f"Unknown layout {layout}")

    return cmd


def run_one(cfg, exp, progress):
    results_root = Path(cfg["results_root"]).resolve()
    outdir = results_root / exp["name"]
    ensure_dir(outdir)

    cmd = make_experiment_command(cfg, exp, outdir)
    progress.start(exp["name"])
    print("[RUN]", " ".join(shlex.quote(x) for x in cmd))

    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(Path(cfg["repo_root"])),
        capture_output=True,
        text=True,
    )
    elapsed = time.time() - t0
    progress.finish()
    print(f"[TIME] {exp['name']} took {elapsed:.2f}s")

    (outdir / "gem5_stdout.txt").write_text(proc.stdout or "", encoding="utf-8", errors="ignore")
    (outdir / "gem5_stderr.txt").write_text(proc.stderr or "", encoding="utf-8", errors="ignore")

    if proc.returncode != 0:
        print(f"[ERROR] {exp['name']} failed with return code {proc.returncode}")
        if proc.stderr:
            print(proc.stderr[-2000:])

    stats_path = outdir / "stats.txt"
    stats = parse_stats(stats_path)
    row = {
        "name": exp["name"],
        "group": exp.get("group", ""),
        "layout": exp["layout"],
        "flush_interval": exp.get("flush_interval", 0),
        "num_cores": exp["num_cores"],
        "threads_per_core": exp["threads_per_core"],
        "returncode": proc.returncode,
        "host_wallclock_sec": elapsed,
        "outdir": str(outdir),
        "stats_path": str(stats_path),
        "run_cmd": " ".join(shlex.quote(x) for x in cmd),
    }
    row.update(summarize(stats))
    return row


def expand_sweep(cfg):
    expanded = []
    for exp in cfg["experiments"]:
        if "flush_intervals" in exp:
            for fi in exp["flush_intervals"]:
                e = dict(exp)
                e.pop("flush_intervals")
                e["flush_interval"] = fi
                e["name"] = f"{exp['name']}_fi{fi}"
                expanded.append(e)
        else:
            expanded.append(exp)
    return expanded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="scripts/phase2_flush_config.json")
    ap.add_argument("--output-csv", default="results/phase2_flush_results.csv")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    output_csv = Path(args.output_csv).resolve()
    ensure_dir(output_csv.parent)
    ensure_dir(Path(cfg["results_root"]).resolve())

    experiments = expand_sweep(cfg)
    progress = Progress(len(experiments))

    rows = []
    for exp in experiments:
        rows.append(run_one(cfg, exp, progress))

    fieldnames = list(rows[0].keys()) if rows else []
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[INFO] Completed {progress.done}/{progress.total} experiments")
    print(f"Wrote {len(rows)} rows to {output_csv}")


if __name__ == "__main__":
    main()
