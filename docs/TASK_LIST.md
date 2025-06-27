### Bootstrapping
- [ ] tracer.py: hook `sys.settrace` as a fallback for Py<3.12.
- [ ] _writer.c: proof-of-concept that writes hard-coded `H`..`E` for a
      3-line script, verified by `nytprofhtml`.
- [ ] tests/test_smoke.py: assert `nytprof.out` exists & >0 bytes.

### Performance
- [ ] Replace GIL-held Python queue with lock-free ring buffer.
- [ ] Support `NYTPROF_FILTER="package/*"` globs.

### Stretch
- [ ] Add Speedscope JSON converter.
