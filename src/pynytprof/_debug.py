from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from typing import IO


@dataclass
class DebugConfig:
    active: bool = bool(os.getenv("PYNYTPROF_DEBUG"))
    level: int = int(os.getenv("PYNYTPROF_DEBUG_LEVEL", 1))
    at_off: int | None = int(os.getenv("PYNYTPROF_DEBUG_AT", "0") or 0)
    sink: IO[str] = sys.stderr
    extras: list[IO[str]] = field(default_factory=list)


DBG = DebugConfig()


def log(msg: str, level: int = 1) -> None:
    if DBG.active and DBG.level >= level:
        print(msg, file=DBG.sink)
        for fp in DBG.extras:
            print(msg, file=fp)


def hexdump(data: bytes) -> None:
    for i in range(0, len(data), 16):
        slice = data[i : i + 16]
        hexs = " ".join(f"{b:02x}" for b in slice).ljust(47)
        asci = "".join(chr(b) if 32 <= b < 127 else "." for b in slice)
        log(f"{i:08x}: {hexs} {asci}")


def hexdump_around(b: bytes, pos: int, ctx: int = 32) -> None:
    start = max(0, pos - ctx)
    end = min(len(b), pos + ctx)
    for i in range(start, end, 16):
        slice = b[i : i + 16]
        hexs = " ".join(f"{x:02x}" for x in slice).ljust(47)
        asci = "".join(chr(x) if 32 <= x < 127 else "." for x in slice)
        log(f"{i:08x}: {hexs} {asci}")
