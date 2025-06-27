"""
Minimal tracer: runs a script and produces an empty NYTProf file
so the quick-start command line works. Replace logic later.
"""

import runpy
import sys
from pathlib import Path

MAGIC = b'NYTPROF'  # 8 bytes incl. trailing NULL in NYTProf, we add later

def _emit_stub_file(out_path: Path) -> None:
    with out_path.open('wb') as f:
        f.write(MAGIC + b'\0')        # "NYTPROF\0"
        f.write((5).to_bytes(4, 'little'))  # major
        f.write((0).to_bytes(4, 'little'))  # minor
        f.write(b'E' + (0).to_bytes(4, 'little'))  # empty E-chunk

def profile_script(path: str) -> None:
    out = Path('nytprof.out')
    _emit_stub_file(out)
    runpy.run_path(path, run_name='__main__')

def cli() -> None:
    if len(sys.argv) != 2:
        print('Usage: pynytprof <script.py>', file=sys.stderr)
        sys.exit(1)
    profile_script(sys.argv[1])
