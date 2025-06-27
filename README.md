# Pynytprof

Line-accurate Python profiler that emits Devel::NYTProf files. Use Perl's `nytprofhtml`
for rendering until a dedicated UI exists.

```bash
python -m pip install -e .
pynytprof your_script.py
nytprofhtml -f nytprof.out
```

Current status: MVP writes only H A F S E chunks.
