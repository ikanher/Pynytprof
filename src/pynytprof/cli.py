import argparse
import sys

from . import tracer, convert, verify


def _cmd_profile(args: argparse.Namespace) -> int:
    sys.argv = [args.script] + args.args
    try:
        tracer.profile_script(args.script)
        return 0
    except SystemExit as exc:  # forward script exit code
        return int(exc.code) if isinstance(exc.code, int) else 1


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


def main(argv: list[str] | None = None) -> int:
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
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
