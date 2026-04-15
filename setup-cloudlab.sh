#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEM5_DIR="$REPO_ROOT/gem5"

sudo apt update
sudo apt install -y \
    build-essential scons python3-dev python3-pip python3-venv \
    git zlib1g-dev m4 libprotobuf-dev protobuf-compiler libprotoc-dev \
    libgoogle-perftools-dev libboost-all-dev libhdf5-dev libpng-dev \
    libelf-dev pkg-config

if [ ! -d "$GEM5_DIR" ]; then
    git clone https://github.com/gem5/gem5 "$GEM5_DIR"
fi

cd "$GEM5_DIR"
git checkout stable

# ✅ Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# ✅ Upgrade pip inside venv
python3 -m pip install --upgrade pip

# ✅ Install requirements safely
python3 -m pip install -r requirements.txt

# Apply patches if any
if ls "$REPO_ROOT"/patches/*.patch >/dev/null 2>&1; then
    for p in "$REPO_ROOT"/patches/*.patch; do
        git apply "$p"
    done
fi

# Build gem5
scons build/X86/gem5.opt -j"$(nproc)"