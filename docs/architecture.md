# Architecture

This document explains the moving pieces of **Pynytprof** and how they work together.

## Component map

| Module | Responsibility |
|-------|---------------|
| `main.py` | Command-line entry points and high level helpers |
| `convert.py` | Convert NYTProf files to other formats |
| `tracer.py` | Pure Python tracer used when no C tracer is available |
| `reader.py` | Developer helper to decode NYTProf data |

## Runtime flow

1. `profile_script()` selects the best tracer implementation.
2. Execution events are stored in memory and flushed through a writer.
3. The resulting `nytprof.out` can be rendered with `nytprofhtml`.

## Extensibility

The tracer and writer modules are loosely coupled. Third parties can
provide alternative implementations as long as they expose the same
function signatures used by `profile_script()`.
