## Data path

CPython frame-eval → `tracer.py` (gathers line events) → `_writer.c`
(pack structs, spill to `nytprof.out`) → Perl `nytprofhtml` → HTML.

``tracer.py`` stays pure-Python so users can prototype quickly; the C writer
handles the hot loop so overhead stays <5×.

### Major modules

| Module        | Responsibility                            |
|---------------|-------------------------------------------|
| `tracer.py`   | subscribe to frame events, queue records  |
| `_writer.c`   | ring-buffer + `write()` burst flush       |
| `reader.py`   | (dev-only) decode records for tests       |

Call depth is measured with `frame->f_depth`.  Wall-clock ticks use
`clock_gettime(CLOCK_MONOTONIC_RAW)` on POSIX and `QueryPerformanceCounter`
on Windows.
