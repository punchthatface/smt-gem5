#!/usr/bin/env python3
from pathlib import Path

path = Path("scripts/run_phase2_experiment.py")
text = path.read_text()

# Add output CSV columns if not already present.
old_cols = '"flush_core",'
new_cols = """\"flush_core\",
        \"smt_resource_policy\",
        \"smt_fetch_policy\",
        \"smt_commit_policy\",
        \"smt_rob_policy\",
        \"smt_iq_policy\",
        \"smt_lsq_policy\",
        \"smt_num_fetching_threads\","""
if new_cols not in text:
    text = text.replace(old_cols, new_cols)

# Add command-line forwarding after flush_core args are appended.
anchor = """    if flush_core is not None:
        cmd += [\"--flush-core\", str(flush_core)]
"""
insert = """    smt_resource_policy = case.get(\"smt_resource_policy\", config.get(\"smt_resource_policy\", \"default\"))
    smt_fetch_policy = case.get(\"smt_fetch_policy\", config.get(\"smt_fetch_policy\", \"\"))
    smt_commit_policy = case.get(\"smt_commit_policy\", config.get(\"smt_commit_policy\", \"\"))
    smt_rob_policy = case.get(\"smt_rob_policy\", config.get(\"smt_rob_policy\", \"\"))
    smt_iq_policy = case.get(\"smt_iq_policy\", config.get(\"smt_iq_policy\", \"\"))
    smt_lsq_policy = case.get(\"smt_lsq_policy\", config.get(\"smt_lsq_policy\", \"\"))
    smt_num_fetching_threads = case.get(\"smt_num_fetching_threads\", config.get(\"smt_num_fetching_threads\", None))

    if smt_resource_policy:
        cmd += [\"--smt-resource-policy\", str(smt_resource_policy)]
    if smt_fetch_policy:
        cmd += [\"--smt-fetch-policy\", str(smt_fetch_policy)]
    if smt_commit_policy:
        cmd += [\"--smt-commit-policy\", str(smt_commit_policy)]
    if smt_rob_policy:
        cmd += [\"--smt-rob-policy\", str(smt_rob_policy)]
    if smt_iq_policy:
        cmd += [\"--smt-iq-policy\", str(smt_iq_policy)]
    if smt_lsq_policy:
        cmd += [\"--smt-lsq-policy\", str(smt_lsq_policy)]
    if smt_num_fetching_threads is not None:
        cmd += [\"--smt-num-fetching-threads\", str(smt_num_fetching_threads)]
"""
if insert not in text:
    if anchor not in text:
        raise SystemExit("Could not find flush_core command anchor. Send current scripts/run_phase2_experiment.py.")
    text = text.replace(anchor, anchor + "\n" + insert)

# Add row fields near flush_core output.
old_row = """            \"flush_core\": flush_core,"""
new_row = """            \"flush_core\": flush_core,
            \"smt_resource_policy\": smt_resource_policy,
            \"smt_fetch_policy\": smt_fetch_policy,
            \"smt_commit_policy\": smt_commit_policy,
            \"smt_rob_policy\": smt_rob_policy,
            \"smt_iq_policy\": smt_iq_policy,
            \"smt_lsq_policy\": smt_lsq_policy,
            \"smt_num_fetching_threads\": smt_num_fetching_threads,"""
if new_row not in text:
    if old_row not in text:
        raise SystemExit("Could not find flush_core row anchor. Send current scripts/run_phase2_experiment.py.")
    text = text.replace(old_row, new_row)

path.write_text(text)
print("Patched scripts/run_phase2_experiment.py to forward SMT resource-policy args.")
