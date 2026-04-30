#!/usr/bin/env bash
set -euo pipefail

# Phase 2 PARSEC setup helper for the vips/no-bodytrack final.
# Run from repo root:
#   cd /users/akim2/smt-gem5
#   ./scripts/setup-phase2-parsec-vips.sh

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARSEC_DIR="$REPO_ROOT/parsec"

if [ ! -d "$PARSEC_DIR" ]; then
  echo "ERROR: PARSEC directory not found: $PARSEC_DIR"
  exit 1
fi
if [ ! -f "$PARSEC_DIR/env.sh" ]; then
  echo "ERROR: PARSEC env.sh not found: $PARSEC_DIR/env.sh"
  exit 1
fi

cd "$PARSEC_DIR"
export PARSECDIR="$PARSEC_DIR"
export xxPARSECDIRxx="$PARSEC_DIR"
set +u
# shellcheck disable=SC1091
. "$PARSEC_DIR/env.sh"
set -u

echo
echo "=== Building Phase 2 PARSEC workloads: no bodytrack, vips replacement ==="

build_pkg() {
  local pkg="$1"
  local conf="$2"
  echo
  echo "[PARSEC BUILD] $pkg -c $conf"
  parsecmgmt -a build -p "$pkg" -c "$conf"
}

build_pkg parsec.swaptions     gcc-pthreads
build_pkg parsec.blackscholes  gcc-pthreads
build_pkg parsec.streamcluster gcc-pthreads
build_pkg parsec.fluidanimate  gcc-pthreads
build_pkg parsec.canneal       gcc-pthreads
build_pkg parsec.freqmine      gcc-openmp
build_pkg parsec.dedup         gcc-pthreads
build_pkg parsec.vips          gcc-pthreads

echo
echo "=== Preparing simsmall run/input directories ==="

run_pkg() {
  local pkg="$1"
  local conf="$2"
  echo
  echo "[PARSEC INPUT/RUN PREP] $pkg -c $conf -i simsmall -n 1"
  parsecmgmt -a run -p "$pkg" -c "$conf" -i simsmall -n 1 || {
    echo "WARNING: parsecmgmt run failed for $pkg. Continuing to verification."
  }
}

run_pkg parsec.blackscholes  gcc-pthreads
run_pkg parsec.fluidanimate  gcc-pthreads
run_pkg parsec.canneal       gcc-pthreads
run_pkg parsec.freqmine      gcc-openmp
run_pkg parsec.dedup         gcc-pthreads
run_pkg parsec.vips          gcc-pthreads

echo
echo "=== Verifying expected binaries and input files ==="

check_file() {
  local path="$1"
  if [ ! -e "$path" ]; then
    echo "MISSING: $path"
    return 1
  fi
  echo "OK: $path"
}

missing=0
check_file "$PARSEC_DIR/pkgs/apps/swaptions/inst/amd64-linux.gcc-pthreads/bin/swaptions" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/blackscholes/inst/amd64-linux.gcc-pthreads/bin/blackscholes" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/streamcluster/inst/amd64-linux.gcc-pthreads/bin/streamcluster" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/fluidanimate/inst/amd64-linux.gcc-pthreads/bin/fluidanimate" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/canneal/inst/amd64-linux.gcc-pthreads/bin/canneal" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/freqmine/inst/amd64-linux.gcc-openmp/bin/freqmine" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/dedup/inst/amd64-linux.gcc-pthreads/bin/dedup" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/vips/inst/amd64-linux.gcc-pthreads/bin/vips" || missing=1

check_file "$PARSEC_DIR/pkgs/apps/blackscholes/run/in_4K.txt" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/fluidanimate/run/in_35K.fluid" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/canneal/run/100000.nets" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/freqmine/run/kosarak_250k.dat" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/dedup/run/media.dat" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/vips/run/pomegranate_1600x1200.v" || missing=1

if [ "$missing" -ne 0 ]; then
  echo
  echo "ERROR: Some expected files are missing. Do not run final configs yet."
  exit 1
fi

echo
echo "Phase 2 vips/no-bodytrack PARSEC setup complete."
