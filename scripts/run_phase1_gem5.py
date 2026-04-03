#!/usr/bin/env python3
"""
Run gem5 Phase-1 SMT policy experiments and emit a CSV.

Assumptions:
- Legacy/deprecated SE-mode config script like configs/example/se.py or configs/deprecated/example/se.py
- Unrestricted SMT: 1 CPU with 2 hardware threads and 2 programs
- No-SMT:
    * sequential_single_core (default): one physical core with SMT disabled, so the pair is represented
      by two solo runs completed one after the other
    * parallel_two_cores: aggregate two solo runs as if they could run at the same time on separate cores
- Quick constrained SMT:
    * same domain -> run together with SMT
    * different domains -> fall back to the configured no-SMT aggregation model

Usage:
  python3 run_phase1_gem5.py --config phase1_config.example.json --output-csv results.csv
"""

import argparse
import csv
import json
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

STAT_RE = re.compile(r"^(\S+)\s+([-+0-9.eE]+)")

def parse_stats(stats_path: Path) -> Dict[str, float]:
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

def summarize_stats(stats: Dict[str, float]) -> Dict[str, float]:
    sim_insts = stats.get("simInsts", 0.0)
    sim_seconds = stats.get("simSeconds", 0.0)
    host_seconds = stats.get("hostSeconds", 0.0)
    throughput = sim_insts / sim_seconds if sim_seconds else 0.0
    return {
        "simInsts": sim_insts,
        "simSeconds": sim_seconds,
        "hostSeconds": host_seconds,
        "throughput_inst_per_simsec": throughput,
        "simTicks": stats.get("simTicks", 0.0),
        "finalTick": stats.get("finalTick", 0.0),
    }

def find_se_script(gem5_root: Path, user_path: str = "") -> Path:
    if user_path:
        p = Path(user_path)
        if p.exists():
            return p.resolve()
        raise FileNotFoundError(f"SE script not found: {user_path}")
    candidates = [
        gem5_root / "configs" / "deprecated" / "example" / "se.py",
        gem5_root / "configs" / "example" / "se.py",
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError("Could not find se.py under configs/example or configs/deprecated/example")

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd: List[str], cwd: Path) -> subprocess.CompletedProcess:
    print("\n[RUN]", " ".join(shlex.quote(x) for x in cmd))
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)

def build_base_cmd(cfg: Dict, outdir: Path) -> List[str]:
    gem5_bin = cfg["gem5_bin"]
    gem5_root = Path(cfg["gem5_root"]).resolve()
    se_script = str(find_se_script(gem5_root, cfg.get("se_script", "")))
    common_args = cfg.get("common_args", [])
    return [gem5_bin, "-d", str(outdir), se_script] + common_args

def workload_cmd_and_opts(w: Dict) -> Tuple[str, str]:
    return w["cmd"], w.get("options", "")

def execute_single(cfg: Dict, workload: Dict, outdir: Path) -> Dict:
    ensure_dir(outdir)
    base = build_base_cmd(cfg, outdir)
    cmd, opts = workload_cmd_and_opts(workload)
    args = base + ["-c", cmd]
    if opts:
        args += ["-o", opts]
    proc = run_cmd(args, Path(cfg["gem5_root"]))
    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stats_path": str(outdir / "stats.txt"),
        "config_path": str(outdir / "config.ini"),
        "run_cmd": " ".join(shlex.quote(x) for x in args),
    }
    stats_path = outdir / "stats.txt"
    if stats_path.exists():
        result.update(summarize_stats(parse_stats(stats_path)))
    return result

def execute_pair_smt(cfg: Dict, w1: Dict, w2: Dict, outdir: Path) -> Dict:
    ensure_dir(outdir)
    base = build_base_cmd(cfg, outdir)
    c1, o1 = workload_cmd_and_opts(w1)
    c2, o2 = workload_cmd_and_opts(w2)
    cmd_field = f"{c1};{c2}"
    args = base + ["--smt", "-c", cmd_field]
    if o1 or o2:
        args += ["-o", f"{o1};{o2}"]
    proc = run_cmd(args, Path(cfg["gem5_root"]))
    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stats_path": str(outdir / "stats.txt"),
        "config_path": str(outdir / "config.ini"),
        "run_cmd": " ".join(shlex.quote(x) for x in args),
    }
    stats_path = outdir / "stats.txt"
    if stats_path.exists():
        result.update(summarize_stats(parse_stats(stats_path)))
    return result

def combine_solo_results(r1: Dict, r2: Dict, mode: str) -> Dict:
    total_insts = r1.get("simInsts", 0.0) + r2.get("simInsts", 0.0)
    if mode == "sequential_single_core":
        total_sim_seconds = r1.get("simSeconds", 0.0) + r2.get("simSeconds", 0.0)
        total_host_seconds = r1.get("hostSeconds", 0.0) + r2.get("hostSeconds", 0.0)
    elif mode == "parallel_two_cores":
        total_sim_seconds = max(r1.get("simSeconds", 0.0), r2.get("simSeconds", 0.0))
        total_host_seconds = r1.get("hostSeconds", 0.0) + r2.get("hostSeconds", 0.0)
    else:
        raise ValueError(f"Unknown no_smt_mode: {mode}")
    throughput = total_insts / total_sim_seconds if total_sim_seconds else 0.0
    return {
        "simInsts": total_insts,
        "simSeconds": total_sim_seconds,
        "hostSeconds": total_host_seconds,
        "throughput_inst_per_simsec": throughput,
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="JSON config")
    ap.add_argument("--output-csv", required=True, help="Where to write CSV")
    args = ap.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    no_smt_mode = cfg.get("no_smt_mode", "sequential_single_core")

    out_csv = Path(args.output_csv).resolve()
    ensure_dir(out_csv.parent)

    workloads = cfg["workloads"]
    pairs = cfg["pairs"]

    fieldnames = [
        "pair_name", "policy", "effective_policy",
        "w1", "w2", "domain1", "domain2",
        "returncode",
        "simInsts", "simSeconds", "hostSeconds", "throughput_inst_per_simsec",
        "outdir", "stats_path", "config_path", "run_cmd", "notes"
    ]

    rows = []
    base_results_dir = Path(cfg.get("results_root", "./phase1_runs")).resolve()
    ensure_dir(base_results_dir)

    for pair in pairs:
        name = pair["name"]
        w1 = workloads[pair["w1"]]
        w2 = workloads[pair["w2"]]
        d1 = w1["domain"]
        d2 = w2["domain"]

        # Unrestricted SMT
        outdir = base_results_dir / name / "unrestricted_smt"
        r = execute_pair_smt(cfg, w1, w2, outdir)
        rows.append({
            "pair_name": name,
            "policy": "unrestricted_smt",
            "effective_policy": "unrestricted_smt",
            "w1": pair["w1"],
            "w2": pair["w2"],
            "domain1": d1,
            "domain2": d2,
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

        # No-SMT = two solo runs
        outdir1 = base_results_dir / name / "no_smt" / "solo1"
        outdir2 = base_results_dir / name / "no_smt" / "solo2"
        r1 = execute_single(cfg, w1, outdir1)
        r2 = execute_single(cfg, w2, outdir2)
        rc = 0 if r1.get("returncode", 1) == 0 and r2.get("returncode", 1) == 0 else 1
        combo = combine_solo_results(r1, r2, no_smt_mode)
        rows.append({
            "pair_name": name,
            "policy": "no_smt",
            "effective_policy": no_smt_mode,
            "w1": pair["w1"],
            "w2": pair["w2"],
            "domain1": d1,
            "domain2": d2,
            "returncode": rc,
            "simInsts": combo.get("simInsts", ""),
            "simSeconds": combo.get("simSeconds", ""),
            "hostSeconds": combo.get("hostSeconds", ""),
            "throughput_inst_per_simsec": combo.get("throughput_inst_per_simsec", ""),
            "outdir": str(base_results_dir / name / "no_smt"),
            "stats_path": f"{r1.get('stats_path','')} | {r2.get('stats_path','')}",
            "config_path": f"{r1.get('config_path','')} | {r2.get('config_path','')}",
            "run_cmd": f"{r1.get('run_cmd','')} || {r2.get('run_cmd','')}",
            "notes": f"aggregated from two solo runs using {no_smt_mode}",
        })

        # Quick constrained SMT
        if d1 == d2:
            outdir = base_results_dir / name / "constrained_smt"
            r = execute_pair_smt(cfg, w1, w2, outdir)
            rows.append({
                "pair_name": name,
                "policy": "constrained_smt",
                "effective_policy": "same_domain_pair_on_smt",
                "w1": pair["w1"],
                "w2": pair["w2"],
                "domain1": d1,
                "domain2": d2,
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
                "effective_policy": f"cross_domain_fell_back_to_{no_smt_mode}",
                "w1": pair["w1"],
                "w2": pair["w2"],
                "domain1": d1,
                "domain2": d2,
                "returncode": rc,
                "simInsts": combo.get("simInsts", ""),
                "simSeconds": combo.get("simSeconds", ""),
                "hostSeconds": combo.get("hostSeconds", ""),
                "throughput_inst_per_simsec": combo.get("throughput_inst_per_simsec", ""),
                "outdir": str(base_results_dir / name / "constrained_smt"),
                "stats_path": f"{r1.get('stats_path','')} | {r2.get('stats_path','')}",
                "config_path": f"{r1.get('config_path','')} | {r2.get('config_path','')}",
                "run_cmd": f"{r1.get('run_cmd','')} || {r2.get('run_cmd','')}",
                "notes": "quick constrained model: cross-domain pair cannot co-run",
            })

    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows to {out_csv}")

if __name__ == "__main__":
    main()
