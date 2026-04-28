#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC_DIR="$REPO_ROOT/workloads/src"
BIN_DIR="$REPO_ROOT/workloads/bin"

mkdir -p "$BIN_DIR"

CC=${CC:-gcc}
CFLAGS=${CFLAGS:-"-O2 -g -std=c11 -Wall -Wextra -Wno-unused-parameter"}

$CC $CFLAGS "$SRC_DIR/phase2_victim.c" -o "$BIN_DIR/phase2_victim"
$CC $CFLAGS "$SRC_DIR/phase2_interferer.c" -o "$BIN_DIR/phase2_interferer"

file "$BIN_DIR/phase2_victim"
file "$BIN_DIR/phase2_interferer"

echo "Built Phase 2 workloads in $BIN_DIR"
