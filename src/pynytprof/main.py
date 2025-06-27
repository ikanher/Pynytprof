from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import tracer, reader
from . import convert


def _verify(path: str) -> int:
    try:
        data = reader.read(path)
    except ValueError as e:
        print(f"{path} \u2717  {e}")
        return 1
    except OSError as e:
        print(f"{path} \u2717  {e}")
        return 2
    ticks = sum(r[4] for r in data["records"])
    tick_str = f"{ticks:,}".replace(",", " ")
    print(f"{path} \u2713  {len(data['records'])} lines, {tick_str} total ticks")
    return 0


def _convert_speedscope(src: str, dest: str | None) -> None:
    out = convert.to_speedscope(src, dest)
    print(out)


def cli(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"profile", "verify", "convert"}:
        argv.insert(0, "profile")
    p = argparse.ArgumentParser(prog="pynytprof")
    sp = p.add_subparsers(dest="cmd", required=True)
    pr = sp.add_parser("profile")
    pr.add_argument("script")
    pr.add_argument("args", nargs=argparse.REMAINDER)
    vr = sp.add_parser("verify")
    vr.add_argument("path")
    cv = sp.add_parser("convert")
    cv.add_argument("--speedscope", action="store_true")
    cv.add_argument("src")
    cv.add_argument("dest", nargs="?")
    args = p.parse_args(argv)
    if args.cmd == "verify":
        return _verify(args.path)
    if args.cmd == "convert":
        if args.speedscope:
            _convert_speedscope(args.src, args.dest)
            return 0
        p.error("convert: no format specified")
    sys.argv = [args.script] + args.args
    tracer.profile_script(args.script)
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())
