#!/usr/bin/env bash
set -e

sudo apt-get update -qq

# 1. C compiler + Python headers
sudo apt-get install --no-install-recommends -y \
    build-essential python3-all-dev

# 2. Perl NYTProf viewer + Graphviz for call-graph images
sudo apt-get install --no-install-recommends -y \
    libdevel-nytprof-perl graphviz
