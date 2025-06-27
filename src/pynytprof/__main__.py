import argparse
import sys

from . import tracer, reader


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


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] not in {"profile", "verify"}:
        argv.insert(0, "profile")
    p = argparse.ArgumentParser(prog="pynytprof")
    sp = p.add_subparsers(dest="cmd", required=True)
    pr = sp.add_parser("profile")
    pr.add_argument("script")
    vr = sp.add_parser("verify")
    vr.add_argument("path")
    args = p.parse_args(argv)
    if args.cmd == "verify":
        return _verify(args.path)
    tracer.profile_script(args.script)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
