#!/usr/bin/env bash
set -euo pipefail

# Phase 2 PARSEC setup helper.
#
# Run from repo root after setup-cloudlab.sh:
#   cd /users/<NETID>/smt-gem5
#   ./scripts/setup-phase2-parsec.sh
#
# Purpose:
#   Build and prepare the 8 PARSEC workloads used by the final 4-core/8-thread
#   SMT security-policy experiment.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PARSEC_DIR="$REPO_ROOT/parsec"

if [ ! -d "$PARSEC_DIR" ]; then
  echo "ERROR: PARSEC directory not found: $PARSEC_DIR"
  echo "Run setup-cloudlab.sh first."
  exit 1
fi

if [ ! -f "$PARSEC_DIR/env.sh" ]; then
  echo "ERROR: PARSEC env.sh not found: $PARSEC_DIR/env.sh"
  echo "PARSEC configure may not have completed."
  exit 1
fi

cd "$PARSEC_DIR"

# This PARSEC tree's env.sh can reference PARSECDIR / template variables while
# being sourced. Keep the main script strict, but relax nounset only here.
export PARSECDIR="$PARSEC_DIR"
export xxPARSECDIRxx="$PARSEC_DIR"
set +u
# shellcheck disable=SC1091
. "$PARSEC_DIR/env.sh"
set -u

echo
echo "=== Building Phase 2 PARSEC workloads ==="

build_pkg() {
  local pkg="$1"
  local conf="$2"
  echo
  echo "[PARSEC BUILD] $pkg -c $conf"
  parsecmgmt -a build -p "$pkg" -c "$conf"
}

# 8-workload final set.
build_pkg parsec.swaptions     gcc-pthreads
build_pkg parsec.blackscholes  gcc-pthreads
build_pkg parsec.streamcluster gcc-pthreads
build_pkg parsec.fluidanimate  gcc-pthreads
build_pkg parsec.canneal       gcc-pthreads
build_pkg parsec.bodytrack     gcc-pthreads
build_pkg parsec.dedup         gcc-pthreads

# freqmine does not provide gcc-pthreads in this PARSEC tree.
# It uses OpenMP; experiments run it with OMP_NUM_THREADS=1 so it is one domain.
build_pkg parsec.freqmine      gcc-openmp

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

# These packages need run/ inputs for direct gem5 command lines.
run_pkg parsec.blackscholes  gcc-pthreads
run_pkg parsec.fluidanimate  gcc-pthreads
run_pkg parsec.canneal       gcc-pthreads
run_pkg parsec.freqmine      gcc-openmp
run_pkg parsec.bodytrack     gcc-pthreads
run_pkg parsec.dedup         gcc-pthreads

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
check_file "$PARSEC_DIR/pkgs/apps/bodytrack/inst/amd64-linux.gcc-pthreads/bin/bodytrack" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/dedup/inst/amd64-linux.gcc-pthreads/bin/dedup" || missing=1

check_file "$PARSEC_DIR/pkgs/apps/blackscholes/run/in_4K.txt" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/fluidanimate/run/in_35K.fluid" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/canneal/run/100000.nets" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/freqmine/run/kosarak_250k.dat" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/bodytrack/run/sequenceB_1/poses.txt" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/dedup/run/media.dat" || missing=1

echo
if [ "$missing" -ne 0 ]; then
  echo "ERROR: Some expected files are missing."
  echo "If this node is not the prepared source node, copy the relevant run/ directories"
  echo "from a prepared node, or rerun this helper."
  exit 1
fi

echo "Phase 2 PARSEC setup complete."
echo
echo "Final workload set:"
echo "  swaptions      gcc-pthreads"
echo "  blackscholes   gcc-pthreads"
echo "  streamcluster  gcc-pthreads"
echo "  fluidanimate   gcc-pthreads"
echo "  canneal        gcc-pthreads"
echo "  freqmine       gcc-openmp, run with OMP_NUM_THREADS=1"
echo "  bodytrack      gcc-pthreads"
echo "  dedup          gcc-pthreads"
