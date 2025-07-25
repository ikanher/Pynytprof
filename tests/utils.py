from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


def newest_profile_file(path: str | Path = '.') -> Path:
    base = Path(path)
    files = sorted(base.glob('nytprof.out.*'), key=lambda p: p.stat().st_mtime, reverse=True)
    assert files, 'no nytprof.out.* found'
    return files[0]


def parse_nv_size_from_banner(data: bytes) -> int:
    banner = data.split(b'\nP', 1)[0]
    m = re.search(rb':nv_size=(\d+)', banner)
    return int(m.group(1)) if m else 8


def run_tracer(tmp_path: Path) -> Path:
    """Run example_script.py under the tracer and return the profile path."""
    env = {
        **os.environ,
        "PYNYTPROF_WRITER": "py",
        "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src"),
    }
    script = Path(__file__).with_name("example_script.py")
    subprocess.check_call(
        [sys.executable, "-m", "pynytprof.tracer", str(script)],
        cwd=tmp_path,
        env=env,
    )
    return newest_profile_file(tmp_path)
