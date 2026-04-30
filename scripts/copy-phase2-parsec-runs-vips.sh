#!/usr/bin/env bash
set -euo pipefail

# Optional helper: copy prepared PARSEC run/ input directories from one node.
# Usage:
#   cd /users/akim2/smt-gem5
#   ./scripts/copy-phase2-parsec-runs-vips.sh node0

SRC_NODE="${1:-node0}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARSEC_DIR="$REPO_ROOT/parsec"

copy_run_dir() {
  local pkg_path="$1"
  echo "[COPY] $SRC_NODE:$PARSEC_DIR/$pkg_path/run -> $PARSEC_DIR/$pkg_path/"
  mkdir -p "$PARSEC_DIR/$pkg_path"
  rm -rf "$PARSEC_DIR/$pkg_path/run"
  scp -r "$SRC_NODE:$PARSEC_DIR/$pkg_path/run" "$PARSEC_DIR/$pkg_path/"
}

copy_run_dir "pkgs/apps/blackscholes"
copy_run_dir "pkgs/apps/fluidanimate"
copy_run_dir "pkgs/kernels/canneal"
copy_run_dir "pkgs/apps/freqmine"
copy_run_dir "pkgs/kernels/dedup"
copy_run_dir "pkgs/apps/vips"

echo "Copied Phase 2 PARSEC run directories from $SRC_NODE."
