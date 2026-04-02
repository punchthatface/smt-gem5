#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GEM5_DIR="$REPO_ROOT/gem5"

sudo apt update
sudo apt install -y build-essential scons python3-dev python3-pip git zlib1g-dev m4 libprotobuf-dev protobuf-compiler libprotoc-dev libgoogle-perftools-dev libboost-all-dev libhdf5-serial-dev libpng-dev libelf-dev pkg-config

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