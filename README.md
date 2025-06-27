# Pynytprof

Line-accurate Python profiler that emits Devel::NYTProf files. Use Perl's `nytprofhtml`
for rendering until a dedicated UI exists.

```bash
python -m pip install -e .
pynytprof your_script.py
nytprofhtml -f nytprof.out
```

Current status: MVP writes only H A F S E chunks.

## Selective profiling
Set `NYTPROF_FILTER` to a comma separated list of glob patterns.
Patterns are matched against absolute file paths before recording each
line. When unset or empty all executed files are profiled.

Examples:

```
NYTPROF_FILTER="*/site-packages/*"
NYTPROF_FILTER="project/*,*/util/*.py"
```
