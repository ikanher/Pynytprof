#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

path = Path(sys.argv[1] if len(sys.argv) > 1 else "nytprof.out")
subprocess.run(["xxd", "-l", "32", path], check=True)
