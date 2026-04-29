#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GEM5_DIR="$REPO_ROOT/gem5"
SRC="$REPO_ROOT/workloads/src/domain_switch_probe.c"
OUT_DIR="$REPO_ROOT/workloads/bin"
OUT="$OUT_DIR/domain_switch_probe"
M5_DIR="$GEM5_DIR/util/m5"
LIBM5="$M5_DIR/build/x86/out/libm5.a"
mkdir -p "$OUT_DIR"
if [ ! -f "$LIBM5" ]; then
  echo "Building gem5 m5ops library..."
  (cd "$M5_DIR" && scons build/x86/out/libm5.a)
fi
gcc -O2 -g -static -no-pie -DUSE_M5OPS \
  -I"$GEM5_DIR/include" \
  "$SRC" "$LIBM5" \
  -o "$OUT"
file "$OUT"
echo "Built $OUT"
