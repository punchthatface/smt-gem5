#!/usr/bin/env bash
set -euo pipefail

# Build/extract the PARSEC workloads used by the Phase 2 gem5 SMT experiments.
# Run from repo root:
#   cd /users/<NETID>/smt-gem5
#   ./scripts/setup-phase2-parsec.sh
#
# Assumes:
#   - gem5 and parsec have already been cloned by setup-cloudlab.sh
#   - parsec/env.sh exists

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

export PARSECDIR="$PARSEC_DIR"
export xxPARSECDIRxx="$PARSEC_DIR"

# PARSEC env.sh may reference template variables before assigning them.
# Temporarily disable nounset while sourcing it.
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

# Main 6-workload set.
build_pkg parsec.swaptions     gcc-pthreads
build_pkg parsec.blackscholes  gcc-pthreads
build_pkg parsec.streamcluster gcc-pthreads
build_pkg parsec.fluidanimate  gcc-pthreads
build_pkg parsec.canneal       gcc-pthreads

# freqmine does not provide gcc-pthreads in this PARSEC tree. It uses OpenMP.
# In experiments, run it with OMP_NUM_THREADS=1 so it remains one workload/domain.
build_pkg parsec.freqmine      gcc-openmp

echo
echo "=== Extracting / preparing simsmall input directories ==="

# parsecmgmt run creates package run/ directories and extracts input tarballs.
run_pkg() {
  local pkg="$1"
  local conf="$2"
  echo
  echo "[PARSEC INPUT/RUN PREP] $pkg -c $conf -i simsmall -n 1"
  parsecmgmt -a run -p "$pkg" -c "$conf" -i simsmall -n 1 || {
    echo "WARNING: parsecmgmt run failed for $pkg. Checking whether run inputs exist anyway."
  }
}

run_pkg parsec.blackscholes  gcc-pthreads
run_pkg parsec.fluidanimate  gcc-pthreads
run_pkg parsec.canneal       gcc-pthreads
run_pkg parsec.freqmine      gcc-openmp

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

check_file "$PARSEC_DIR/pkgs/apps/blackscholes/run/in_4K.txt" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/fluidanimate/run/in_35K.fluid" || missing=1
check_file "$PARSEC_DIR/pkgs/kernels/canneal/run/100000.nets" || missing=1
check_file "$PARSEC_DIR/pkgs/apps/freqmine/run/kosarak_250k.dat" || missing=1

echo
if [ "$missing" -ne 0 ]; then
  echo "Some expected files are missing. If this node is not node0, copy the relevant run/ dirs from a prepared node."
  echo
  echo "Example:"
  echo "  scp -r node0:$PARSEC_DIR/pkgs/apps/blackscholes/run $PARSEC_DIR/pkgs/apps/blackscholes/"
  echo "  scp -r node0:$PARSEC_DIR/pkgs/apps/fluidanimate/run $PARSEC_DIR/pkgs/apps/fluidanimate/"
  echo "  scp -r node0:$PARSEC_DIR/pkgs/kernels/canneal/run $PARSEC_DIR/pkgs/kernels/canneal/"
  echo "  scp -r node0:$PARSEC_DIR/pkgs/apps/freqmine/run $PARSEC_DIR/pkgs/apps/freqmine/"
  exit 1
fi

echo "Phase 2 PARSEC setup complete."
