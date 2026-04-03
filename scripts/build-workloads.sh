#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "$ROOT/workloads/bin"
mkdir -p "$ROOT/results"

gcc -O2 -static -o "$ROOT/workloads/bin/compute_loop" \
    "$ROOT/workloads/src/compute_loop.c"

gcc -O2 -static -o "$ROOT/workloads/bin/memory_loop" \
    "$ROOT/workloads/src/memory_loop.c"

echo "Built workloads:"
ls -lh "$ROOT/workloads/bin"