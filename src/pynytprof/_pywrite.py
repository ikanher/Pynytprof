# Simple pure-Python NYTProf writer fallback
from __future__ import annotations

from pathlib import Path


def write(
    out_path: str,
    files: list[tuple[int, int, int, int, str]],
    defs: list[tuple[int, str, int, int, int]],
    calls: list[tuple[int | None, str | None, int, int, int]],
    lines: list[tuple[str, int, int, int, int]],
    start_ns: int,
    ticks_per_sec: int,
) -> None:
    """Write minimal NYTProf file with only header and empty E chunk."""
    path = Path(out_path)
    with path.open("wb") as f:
        f.write(b"NYTPROF\0")
        f.write((5).to_bytes(4, "little"))
        f.write((0).to_bytes(4, "little"))
        f.write(b"E" + (0).to_bytes(4, "little"))

