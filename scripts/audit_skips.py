import subprocess
import sys


def run_pytest() -> str:
    proc = subprocess.run(
        [sys.executable, '-m', 'pytest', '-rs'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return proc.stdout


def collect_reasons(output: str) -> list[str]:
    reasons = []
    for line in output.splitlines():
        if line.startswith('SKIPPED'):
            parts = line.split(':', 2)
            if len(parts) >= 3:
                reason = parts[2].strip()
                reasons.append(reason)
    return reasons


def extra_info_for(reason: str) -> str:
    r = reason.lower()
    if 'nytprofhtml' in r:
        res = subprocess.run(['which', 'nytprofhtml'], stdout=subprocess.PIPE, text=True)
        info = res.stdout.strip()
        return info if info else '<missing>'
    if 'graphviz' in r:
        res = subprocess.run(['dot', '-V'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        info = res.stdout.strip()
        return info if info else '<missing>'
    return ''


def main() -> int:
    output = run_pytest()
    reasons = collect_reasons(output)
    counts: dict[str, int] = {}
    info: dict[str, str] = {}
    for r in reasons:
        counts[r] = counts.get(r, 0) + 1
    for r in counts:
        info[r] = extra_info_for(r)

    print('reason | count | extra_info')
    missing = False
    for r, c in sorted(counts.items()):
        ex = info[r]
        print(f'{r} | {c} | {ex}')
        if '<missing>' in ex or '<missing>' in r:
            missing = True

    return 1 if missing else 0


if __name__ == '__main__':
    sys.exit(main())
