from __future__ import annotations

from typing import Optional


def enable(path: str, start_ns: int) -> None: ...


def dump() -> tuple[list[tuple[int, str, int, int, str]], list[tuple[Optional[str], int, int, int, int]], list[tuple[str, int, int, int, int]]]: ...


def write(
    out_path: str,
    files: list[tuple[int, int, int, int, str]],
    defs: list[tuple[int, int, int, int, str]],
    calls: list[tuple[int | None, int, int, int, int]],
    lines: list[tuple[int, int, int, int, int]],
    start_ns: int,
    ticks_per_sec: int,
) -> None: ...
