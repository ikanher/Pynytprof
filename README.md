# Pynytprof

Line-accurate Python profiler that emits Devel::NYTProf files. Use Perl's `nytprofhtml`
for rendering until a dedicated UI exists.

```bash
python -m pip install -e .
pynytprof profile your_script.py
nytprofhtml -f nytprof.out
```

Current status: files include H, A, F, D, C, S and E chunks.

See [ARCHITECTURE.md](docs/ARCHITECTURE.md) for a high level overview.

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

## Debugging
Set `PYNYTPROF_DEBUG=1` to print the chosen writer class and a summary of each
chunk written. Debug information is emitted to stderr.

## Flamegraph output
Use the `speedscope` command to generate JSON for the Speedscope viewer.

```bash
pynytprof speedscope nytprof.out
```

## Prerequisites
Debian/Ubuntu:  sudo ./setup.sh
Running the HTML round-trip test requires `cpanm Devel::NYTProf`

## Quick start
```bash
bash setup.sh      # installs dependencies, builds C extensions, runs tests
source .venv/bin/activate
```

## Command-line usage
Typical operations:

```bash
pynytprof profile script.py
pynytprof verify nytprof.out
pynytprof html nytprof.out --out report
pynytprof speedscope nytprof.out --out profile.json
```
