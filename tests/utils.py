from __future__ import annotations

import re
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
