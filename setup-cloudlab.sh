#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEM5_DIR="$REPO_ROOT/gem5"
PARSEC_DIR="$REPO_ROOT/parsec"

sudo apt update
sudo apt install -y \
  build-essential \
  scons \
  python3-dev \
  python3-pip \
  git \
  zlib1g-dev \
  m4 \
  libprotobuf-dev \
  protobuf-compiler \
  libprotoc-dev \
  libgoogle-perftools-dev \
  libboost-all-dev \
  libhdf5-serial-dev \
  libpng-dev \
  libelf-dev \
  pkg-config

# ----------------------
# gem5 setup
# ----------------------
if [ ! -d "$GEM5_DIR" ]; then
  git clone https://github.com/gem5/gem5 "$GEM5_DIR"
fi

cd "$GEM5_DIR"
git checkout stable

python3 -m pip install --break-system-packages -r requirements.txt

if ls "$REPO_ROOT"/patches/*.patch >/dev/null 2>&1; then
  for p in "$REPO_ROOT"/patches/*.patch; do
    git apply "$p"
  done
fi

scons build/X86/gem5.opt -j"$(nproc)"

# ----------------------
# PARSEC setup (maintained repo, but folder = parsec/)
# ----------------------
if [ ! -d "$PARSEC_DIR" ]; then
  git clone https://github.com/cirosantilli/parsec-benchmark "$PARSEC_DIR"
fi

cd "$PARSEC_DIR"
./configure

# Source PARSEC environment before building packages.
# shellcheck disable=SC1091
. "$PARSEC_DIR/env.sh"

# Build the PARSEC workloads used by the Phase 2 experiments.
# Keep this list focused so setup does not become unnecessarily huge.
PARSEC_PACKAGES=(
  parsec.swaptions
  parsec.streamcluster
  parsec.blackscholes
  parsec.fluidanimate
  parsec.canneal
)

echo
echo "Building PARSEC packages used by experiments..."
for pkg in "${PARSEC_PACKAGES[@]}"; do
  echo "[PARSEC BUILD] $pkg"
  parsecmgmt -a build -p "$pkg" -c gcc-pthreads
done

echo
echo "Setup complete."
echo "gem5:   $GEM5_DIR/build/X86/gem5.opt"
echo "parsec: $PARSEC_DIR"
echo
echo "Built PARSEC packages:"
for pkg in "${PARSEC_PACKAGES[@]}"; do
  echo "  $pkg"
done