#!/usr/bin/env bash
set -euo pipefail

sudo apt-get update -qq
sudo apt-get install --no-install-recommends -y \
    build-essential python3-all-dev python3-venv \
    libdevel-nytprof-perl perl-doc graphviz \
    vim-common coreutils  # xxd and od

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel >/dev/null
pip install -e .

pytest -q
pynytprof info
echo "[✓] Ready — activate via:  source .venv/bin/activate"
