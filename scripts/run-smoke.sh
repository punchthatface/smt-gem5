#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
GEM5_BIN="$REPO_ROOT/gem5/build/X86/gem5.opt"
CONFIG="$REPO_ROOT/gem5/configs/learning_gem5/part1/simple.py"
OUTDIR="$REPO_ROOT/results/smoke"

mkdir -p "$OUTDIR"
"$GEM5_BIN" --outdir="$OUTDIR" "$CONFIG"

echo "Done. See $OUTDIR/stats.txt"