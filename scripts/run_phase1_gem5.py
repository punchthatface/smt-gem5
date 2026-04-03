#!/usr/bin/env python3
"""
Phase-1 gem5 driver that uses the project's custom configs/smt_baseline.py
instead of gem5's deprecated se.py flow.

Policies:
- unrestricted_smt: run two workloads together on one SMT-enabled core
- no_smt: run each workload alone on one non-SMT core, then aggregate
- constrained_smt:
    * same-domain -> same as unrestricted SMT
    * cross-domain -> same as no-SMT (quick baseline model)
"""

import argparse
import csv
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

STAT_RE = re.compile(r"^(\S+)\s+([-+0-9.eE]+)")

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def parse_stats(stats_path: Path):
    stats = {}
    with open(stats_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = STAT_RE.match(line.strip())
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            try:
                stats[key] = float(value)
            except ValueError:
                pass
    return stats

def summarize(stats):
    insts = stats.get("simInsts", 0.0)
    secs = stats.get("simSeconds", 0.0)
    return {
        "simInsts": insts,
        "simSeconds": secs,
        "hostSeconds": stats.get("hostSeconds", 0.0),
        "throughput_inst_per_simsec": (insts / secs) if secs else 0.0,
    }

def run_cmd(cmd, cwd):
    print("\n[RUN]", " ".join(shlex.quote(x) for x in cmd))
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)

def build_base(cfg, outdir):
    return [
        cfg["gem5_bin"],
        "--outdir=" + str(outdir),
        cfg["config_script"],
        "--mem-size", cfg.get("mem_size", "512MB"),
        "--cpu-clock", cfg.get("cpu_clock", "2GHz"),
    ]

def run_single(cfg, workload, outdir):
    ensure_dir(outdir)
    cmd = build_base(cfg, outdir) + [
        "--threads", "1",
        "--cmd1", workload["cmd"],
        "--opts1", workload.get("options", ""),
    ]
    proc = run_cmd(cmd, Path(cfg["repo_root"]))
    res = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "run_cmd": " ".join(shlex.quote(x) for x in cmd),
        "stats_path": str(outdir / "stats.txt"),
        "config_path": str(outdir / "config.ini"),
    }
    sp = outdir / "stats.txt"
    if sp.exists():
        res.update(summarize(parse_stats(sp)))
    return res

def run_pair_smt(cfg, w1, w2, outdir):
    ensure_dir(outdir)
    cmd = build_base(cfg, outdir) + [
        "--threads", "2",
        "--cmd1", w1["cmd"],
        "--opts1", w1.get("options", ""),
        "--cmd2", w2["cmd"],
        "--opts2", w2.get("options", ""),
    ]
    proc = run_cmd(cmd, Path(cfg["repo_root"]))
    res = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "run_cmd": " ".join(shlex.quote(x) for x in cmd),
        "stats_path": str(outdir / "stats.txt"),
        "config_path": str(outdir / "config.ini"),
    }
    sp = outdir / "stats.txt"
    if sp.exists():
        res.update(summarize(parse_stats(sp)))
    return res

def combine_no_smt(r1, r2):
    insts = r1.get("simInsts", 0.0) + r2.get("simInsts", 0.0)
    secs = r1.get("simSeconds", 0.0) + r2.get("simSeconds", 0.0)
    host = r1.get("hostSeconds", 0.0) + r2.get("hostSeconds", 0.0)
    return {
        "simInsts": insts,
        "simSeconds": secs,
        "hostSeconds": host,
        "throughput_inst_per_simsec": (insts / secs) if secs else 0.0,
    }

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

    fieldnames = [
        "pair_name", "policy", "effective_policy",
        "w1", "w2", "domain1", "domain2",
        "returncode", "simInsts", "simSeconds", "hostSeconds",
        "throughput_inst_per_simsec", "outdir", "stats_path",
        "config_path", "run_cmd", "notes"
    ]
    rows = []

    workloads = cfg["workloads"]
    for pair in cfg["pairs"]:
        name = pair["name"]
        w1 = workloads[pair["w1"]]
        w2 = workloads[pair["w2"]]
        d1, d2 = w1["domain"], w2["domain"]

        # unrestricted SMT
        outdir = results_root / name / "unrestricted_smt"
        r = run_pair_smt(cfg, w1, w2, outdir)
        rows.append({
            "pair_name": name,
            "policy": "unrestricted_smt",
            "effective_policy": "unrestricted_smt",
            "w1": pair["w1"], "w2": pair["w2"],
            "domain1": d1, "domain2": d2,
            "returncode": r.get("returncode", -1),
            "simInsts": r.get("simInsts", ""),
            "simSeconds": r.get("simSeconds", ""),
            "hostSeconds": r.get("hostSeconds", ""),
            "throughput_inst_per_simsec": r.get("throughput_inst_per_simsec", ""),
            "outdir": str(outdir),
            "stats_path": r.get("stats_path", ""),
            "config_path": r.get("config_path", ""),
            "run_cmd": r.get("run_cmd", ""),
            "notes": "",
        })

        # no SMT
        solo1 = results_root / name / "no_smt" / "solo1"
        solo2 = results_root / name / "no_smt" / "solo2"
        r1 = run_single(cfg, w1, solo1)
        r2 = run_single(cfg, w2, solo2)
        combo = combine_no_smt(r1, r2)
        rc = 0 if r1.get("returncode", 1) == 0 and r2.get("returncode", 1) == 0 else 1
        rows.append({
            "pair_name": name,
            "policy": "no_smt",
            "effective_policy": "sequential_single_core",
            "w1": pair["w1"], "w2": pair["w2"],
            "domain1": d1, "domain2": d2,
            "returncode": rc,
            "simInsts": combo.get("simInsts", ""),
            "simSeconds": combo.get("simSeconds", ""),
            "hostSeconds": combo.get("hostSeconds", ""),
            "throughput_inst_per_simsec": combo.get("throughput_inst_per_simsec", ""),
            "outdir": str(results_root / name / "no_smt"),
            "stats_path": f"{r1.get('stats_path','')} | {r2.get('stats_path','')}",
            "config_path": f"{r1.get('config_path','')} | {r2.get('config_path','')}",
            "run_cmd": f"{r1.get('run_cmd','')} || {r2.get('run_cmd','')}",
            "notes": "aggregated from two solo runs",
        })

        # constrained SMT (quick model)
        if d1 == d2:
            outdir = results_root / name / "constrained_smt"
            r = run_pair_smt(cfg, w1, w2, outdir)
            rows.append({
                "pair_name": name,
                "policy": "constrained_smt",
                "effective_policy": "same_domain_pair_on_smt",
                "w1": pair["w1"], "w2": pair["w2"],
                "domain1": d1, "domain2": d2,
                "returncode": r.get("returncode", -1),
                "simInsts": r.get("simInsts", ""),
                "simSeconds": r.get("simSeconds", ""),
                "hostSeconds": r.get("hostSeconds", ""),
                "throughput_inst_per_simsec": r.get("throughput_inst_per_simsec", ""),
                "outdir": str(outdir),
                "stats_path": r.get("stats_path", ""),
                "config_path": r.get("config_path", ""),
                "run_cmd": r.get("run_cmd", ""),
                "notes": "",
            })
        else:
            rows.append({
                "pair_name": name,
                "policy": "constrained_smt",
                "effective_policy": "cross_domain_fell_back_to_no_smt",
                "w1": pair["w1"], "w2": pair["w2"],
                "domain1": d1, "domain2": d2,
                "returncode": rc,
                "simInsts": combo.get("simInsts", ""),
                "simSeconds": combo.get("simSeconds", ""),
                "hostSeconds": combo.get("hostSeconds", ""),
                "throughput_inst_per_simsec": combo.get("throughput_inst_per_simsec", ""),
                "outdir": str(results_root / name / "constrained_smt"),
                "stats_path": f"{r1.get('stats_path','')} | {r2.get('stats_path','')}",
                "config_path": f"{r1.get('config_path','')} | {r2.get('config_path','')}",
                "run_cmd": f"{r1.get('run_cmd','')} || {r2.get('run_cmd','')}",
                "notes": "quick constrained model: cross-domain pair cannot co-run",
            })

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {output_csv}")

if __name__ == "__main__":
    main()
