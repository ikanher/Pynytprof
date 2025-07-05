from __future__ import annotations

import argparse
import os
import subprocess
import sys

from . import convert, verify


def _cmd_profile(args: argparse.Namespace) -> int:
    cmd = [sys.executable, "-m", "pynytprof.tracer", args.script, *args.args]
    proc = subprocess.run(cmd, env=os.environ.copy())
    return proc.returncode


def _cmd_verify(args: argparse.Namespace) -> int:
    ok = verify.verify(args.path, quiet=args.quiet)
    return 0 if ok else 1


def _cmd_html(args: argparse.Namespace) -> int:
    out = convert.to_html(args.input, args.out)
    if not args.quiet:
        print(out)
    return 0


def _cmd_speedscope(args: argparse.Namespace) -> int:
    out = convert.to_speedscope(args.input, args.out)
    if not args.quiet:
        print(out)
    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="pynytprof")
    sub = parser.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("profile", help="profile a script")
    pr.add_argument("script")
    pr.add_argument("args", nargs=argparse.REMAINDER)
    pr.add_argument("-q", "--quiet", action="store_true")
    pr.set_defaults(func=_cmd_profile)

    vr = sub.add_parser("verify", help="verify output file")
    vr.add_argument("path")
    vr.add_argument("-q", "--quiet", action="store_true")
    vr.set_defaults(func=_cmd_verify)

    ht = sub.add_parser("html", help="generate HTML report")
    ht.add_argument("input")
    ht.add_argument("--out")
    ht.add_argument("-q", "--quiet", action="store_true")
    ht.set_defaults(func=_cmd_html)

    sp = sub.add_parser("speedscope", help="generate speedscope JSON")
    sp.add_argument("input")
    sp.add_argument("--out")
    sp.add_argument("-q", "--quiet", action="store_true")
    sp.set_defaults(func=_cmd_speedscope)

    args = parser.parse_args(argv)
    code = args.func(args)
    raise SystemExit(code)


if __name__ == "__main__":  # pragma: no cover
    main()
