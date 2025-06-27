# Pynytprof

Goal: line-accurate, low-overhead Python profiler that emits **exactly the same
binary stream** as Devel::NYTProf.  We rely on Perl’s `nytprofhtml` to render
HTML until our own UI exists.

Quick start
```bash
python -m pip install -e .
python -m pynytprof.tracer tests/example_script.py
nytprofhtml -f nytprof.out                    # Perl tool
xdg-open nytprof/index.html
```

Current status: MVP = emit H A F S E chunks only. Call graphs come later.

---
