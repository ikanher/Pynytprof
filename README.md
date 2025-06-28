# Pynytprof

Line-accurate Python profiler that emits Devel::NYTProf files. Use Perl's `nytprofhtml`
for rendering until a dedicated UI exists.

```bash
python -m pip install -e .
pynytprof your_script.py
nytprofhtml -f nytprof.out
```

Current status: files include H, A, F, D, C, S and E chunks.

## Selective profiling
Set `NYTPROF_FILTER` to a comma separated list of glob patterns.
Patterns are matched against absolute file paths before recording each
line. When unset or empty all executed files are profiled.

Examples:

```
NYTPROF_FILTER="*/site-packages/*"
NYTPROF_FILTER="project/*,*/util/*.py"
```

## File verification
Profiles can be checked with the builtin Python reader.
The verify command prints a short summary and exits with
an error status if the file is corrupted.

```bash
pynytprof verify nytprof.out
```

## Flamegraph output
Use `convert` to generate Speedscope JSON and view results in a browser.

```bash
pynytprof convert --speedscope nytprof.out
```

## Prerequisites
Debian/Ubuntu:  sudo ./setup.sh

## Quick start
```bash
bash setup.sh      # installs dependencies, builds C extensions, runs tests
source .venv/bin/activate
```
