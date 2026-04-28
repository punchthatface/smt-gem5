#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUTDIR="$ROOT/results/smt_baseline"

mkdir -p "$OUTDIR"

"$ROOT/gem5/build/X86/gem5.opt" \
  --outdir="$OUTDIR" \
  "$ROOT/configs/smt_baseline.py"

echo "Done. See $OUTDIR"