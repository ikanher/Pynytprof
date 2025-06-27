from __future__ import annotations

import json
from pathlib import Path

from .reader import read

__all__ = ["to_speedscope"]


def to_speedscope(in_path: str, out_path: str) -> None:
    data = read(in_path)
    script = Path(data.get("files", {}).get(0, {}).get("path", "script")).name
    events = []
    current = 0
    for fid, line, _calls, inc, _exc in data.get("records", []):
        start = current
        dur_us = inc // 10
        events.append({"type": "O", "at": start, "name": f"<line {line}>"})
        events.append({"type": "C", "at": start + dur_us})
        current += dur_us
    result = {
        "schema": "https://www.speedscope.app/file-format-schema.json",
        "version": "0.3.0",
        "profiles": [
            {
                "type": "evented",
                "name": script,
                "unit": "microseconds",
                "events": events,
            }
        ],
    }
    Path(out_path).write_text(json.dumps(result))
