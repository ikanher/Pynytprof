#!/usr/bin/env bash
set -euo pipefail

echo "[*] Updating apt cache"
sudo apt-get update -qq

echo "[*] Installing build tool-chain, headers, Perl viewer, graphviz"
sudo apt-get install --no-install-recommends -y \
    build-essential python3-all-dev python3-venv \
    libdevel-nytprof-perl graphviz

echo "[*] Creating virtual environment .venv"
python3 -m venv .venv
source .venv/bin/activate

echo "[*] Upgrading pip & wheel, installing project"
pip install --upgrade pip wheel >/dev/null
pip install -e .  # builds _tracer / _writer C extensions

echo "[*] Running smoke test"
pytest -q
pynytprof info

echo "[✓] Environment ready — activate with:  source .venv/bin/activate"
