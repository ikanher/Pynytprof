from __future__ import annotations

import json
from pathlib import Path

from .reader import read

__all__ = ["to_speedscope"]


def to_speedscope(in_path: str, out_path: str | None) -> None:
    data = read(in_path)
    files = data.get("files", {})
    script = Path(files.get(0, {}).get("path", "script")).name

    frames: list[dict] = []
    frame_map: dict[str, int] = {}
    events = []
    current = 0

    for fid, line, _calls, inc, _exc in data.get("records", []):
        path = files.get(fid, {}).get("path", "")
        frame_name = f"{Path(path).name}:{line}"
        if frame_name not in frame_map:
            frame_map[frame_name] = len(frames)
            frames.append({"name": frame_name})
        idx = frame_map[frame_name]
        start = current
        dur_us = inc // 10
        events.append({"type": "O", "at": start, "frame": idx})
        events.append({"type": "C", "at": start + dur_us})
        current += dur_us

    result = {
        "$schema": "https://www.speedscope.app/file-format-schema.json",
        "shared": {"frames": frames},
        "profiles": [
            {
                "type": "evented",
                "name": script,
                "unit": "microseconds",
                "startValue": 0,
                "endValue": current,
                "events": events,
            }
        ],
    }

    dest = out_path or str(Path(in_path).with_suffix(".speedscope.json"))
    Path(dest).write_text(json.dumps(result, indent=2))
