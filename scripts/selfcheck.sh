#!/usr/bin/env bash
set -e
pytest -q
pynytprof info
