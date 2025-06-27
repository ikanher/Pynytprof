# Pynytprof

Goal: line-accurate, low-overhead Python profiler that emits **exactly the same
binary stream** as Devel::NYTProf.  We rely on Perl’s `nytprofhtml` to render
HTML until our own UI exists.

Quick start
```bash

```bash
# dev install
python -m pip install -e .

# record a profile
pynytprof tests/example_script.py

# generate HTML with Perl's tooling
nytprofhtml -f nytprof.out
xdg-open nytprof/index.html
```

Current status: MVP = emit H A F S E chunks only. Call graphs come later.

---
