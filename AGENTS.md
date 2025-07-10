# AGENTS

This document helps both **automated coding assistants** and **human contributors** understand how to navigate Pynytprof’s codebase, how pieces relate, and where to find authoritative references.

To speed up things, always run parallel tests by passing `-n auto` to `pytest`.
---

## 1. Purpose

Pynytprof is a Python profiler that produces output compatible with **Devel::NYTProf** (Perl). It does this by:

- Running a Python line tracer.
- Recording events into a binary format (`nytprof.out`).
- Emitting chunks understood by `nytprofhtml`.
- Providing helpers to convert, verify, and inspect profiles.

This document shows **where to look** and **how to contribute**.

---

## 2. Directory Overview

| Path                      | Purpose                                    |
|---------------------------|--------------------------------------------|
| `src/pynytprof/`          | Main Python modules and C extensions      |
| `src/pynytprof/_cwrite.*` | C extension for high-performance chunking |
| `tests/`                  | Unit and integration tests                |
| `docs/`                   | Specifications and architecture guides    |
| `.github/`                | CI workflows                              |

---

## 3. Main Components

### Profiling Tracer
- **Python fallback**: `src/pynytprof/_tracer.py`
- **C fast-path**: `src/pynytprof/_ctrace.c`
- **Entry point**: `tracer.py` selects which implementation to use.

### Writers
- Responsible for emitting NYTProf chunks.
- **Python fallback**: `_pywrite.py`
- **C extension**: `_cwrite.c`
- Controlled by `PYNYTPROF_WRITER` environment variable (`py` or `c`).

### CLI
- `cli.py` dispatches commands (`profile`, `verify`, `convert`).
- `main.py` has legacy helpers.

### Converters
- `convert.py` transforms `nytprof.out` to JSON, HTML, etc.

### Validators
- `verify.py` checks chunk consistency.

---

## 4. Developer Workflow

When you run:

```
pynytprof profile tests/example_script.py
```

the following happens:

1. **CLI** loads.
2. **Tracer** starts and begins recording line hits.
3. **Writer** serialises chunk data.
4. On exit: `nytprof.out` is flushed.
5. You can call `verify` or `convert` on this file.

---

## 5. Where to Find Format Specs

**Authoritative reference for output format:**
- `docs/FILE_FORMAT.md` (explains chunk types and layout)
- Upstream NYTProf: [NYTProf GitHub](https://github.com/timbunce/devel-nytprof)
- Perl module: `Devel::NYTProf::Data`

If in doubt, always compare output to a reference Perl-generated `nytprof.out`.

---

## 6. Contribution Guidelines

- Keep implementations modular: new writers or tracers must follow existing signatures.
- Avoid importing C modules unconditionally—guard with `try/except ImportError`.
- **Never** write files outside `nytprof.out` unless explicitly instructed.
- All chunks must be terminated with an `E` (end) marker.
- Use `tests/` to validate output (diff vs Perl, verify chunk counts).
- All code must run on CPython 3.8+.

---

## 7. Typical Questions

**Q: How do I switch between the C and Python writer?**  
A: Set `PYNYTPROF_WRITER=c` or `PYNYTPROF_WRITER=py` in your environment.

**Q: How do I regenerate the reference output?**  
A: Run `perl -d:NYTProf your_script.pl` and grab `nytprof.out`.

**Q: How do I add a new output format?**  
A: Add a function to `convert.py` and register it in `cli.py`.

**Q: How do I build the C extensions?**  
A: `pip install -e .` will compile `_cwrite` automatically.

**Q: How to run tests faster?**
A: `pytest -n auto` we have `pytest-xdist`, install with `pip install -e .`

---

## 8. Where Codex or other coding agents should look

- **Code examples**: `tests/`
- **Chunk format reference**: `docs/FILE_FORMAT.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **CI logic**: `.github/workflows/ci.yml`
- **Entrypoints**: `cli.py` and `tracer.py`

---

_Last updated: 2025-07-09_


