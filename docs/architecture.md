# Architecture

This document describes how **Pynytprof** works and how its modules fit together.

---

## Component map

| Module                        | Responsibility                                                |
|--------------------------------|--------------------------------------------------------------|
| `cli.py`                      | Argparse-based command-line interface                        |
| `main.py`                     | Legacy command-line helpers                                  |
| `convert.py`                  | Convert NYTProf files to other formats                       |
| `tracer.py`                   | Python tracer collecting per-line execution stats           |
| `_writer.py`                  | Abstraction for chunked NYTProf output (`py` and `c` modes)  |
| `_cwrite.*.so`                | Optimized C extension for chunk writing                      |
| `reader.py`                   | Developer helper to decode NYTProf binary files             |
| `verify.py`                   | Stream verifier for NYTProf files                            |
| `tests/`                      | Unit and integration tests validating output correctness     |

---

## Runtime flow

1. **Initialization**  
   `profile_script()` or `Tracer()` decides whether to use:
   - The C-based chunk writer (`_cwrite`) if available.
   - The fallback pure-Python writer (`_writer.py`).

2. **Profiling**  
   A Python tracing function records:
   - File and line hits.
   - Inclusive/exclusive timings.

   Events are accumulated in `_line_hits`.

3. **Shutdown**
   On process exit, the tracer emits:
   - `P` chunk (start profile marker).
   - `F` chunks (file names and metadata).
   - `S` chunk (line-level statistics).
   - `E` chunk (end marker).

   These are written sequentially via `write_chunk()`.

4. **Postprocessing**
   The resulting `nytprof.out` can be:
   - Verified with `verify.py`.
   - Rendered with `nytprofhtml`.
   - Transformed to other formats via `convert.py`.

---

## Extensibility

The tracer and writer layers are loosely coupled. You can implement your own writer by providing an object with:

- `write_chunk(token: bytes, payload: bytes)`  
- `close()`

as long as you respect the NYTProf chunk format.

---

## Notes on C vs Python Writers

- The C writer is significantly faster and produces the same output as the Python writer.
- If `_cwrite` cannot be loaded, a warning is issued and the pure-Python fallback is used.
- The environment variable `PYNYTPROF_WRITER` can force selection (`c` or `py`).
