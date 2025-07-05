# AGENTS

This document explains **who does what inside Pynytprof** when the codebase is driven by automated (or AI-assisted) agents.  
It lets both humans and tools figure out where a new contribution fits and which “agent” should own it.

---

## 1. Overview

| Agent | Scope | Entry-point | Owns / writes to | Typical trigger |
|-------|-------|------------|------------------|-----------------|
| **Profile agent** | Records runtime events | `pynytprof.tracer` ⇢ `_ctrace` | `nytprof.out` | `pynytprof profile …` |
| **Write agent** | Serialises data into NYTProf chunks | `_cwrite` \| `_pywrite` | `nytprof.out` | Call from tracer at process exit |
| **Convert agent** | Turns NYTProf → other formats | `pynytprof.convert` | `*.json`, `*.html` etc. | `pynytprof html` / `pynytprof speedscope` |
| **Verify agent** | Validates a NYTProf file | `pynytprof.verify` | — | `pynytprof verify …` |
| **CLI agent** | User-facing command dispatcher | `pynytprof.cli` | — | `pynytprof …` |
| **Docs agent** | Keeps docs in sync with code | `docs/architecture.md`, `AGENTS.md` | — | `pytest -q` doc tests |
| **CI agent** | Automation on PRs | `.github/workflows/ci.yml` | Wheels, artefacts | Push / PR / tag |

Agents are composable and orthogonal: **each does one thing, has one owner, and one public interface**.

---

## 2. Runtime flow (agent perspective)

1. **CLI agent** parses user intent → calls the **Profile agent**.
2. **Profile agent** selects C or Python tracer; begins sampling.
3. At program exit: **Profile** hands raw data to **Write agent**.
4. User may call **Verify agent** → sanity-check `nytprof.out`.
5. User may call **Convert agent** → render HTML / speedscope JSON.

All agents communicate only through well-defined *files* or *function calls*; no global state.

---

## 3. Extending / replacing agents

* **Swap the Write agent**  
  Implement `pynytprof._rustwrite.write()` with the same signature  
  and insert it ahead of `_cwrite` in `tracer.py`’s import probe list.
* **Add a new Convert agent**  
  Create `pynytprof.convert_xxx` and register it in `cli.py` as a
  sub-command. Keep conversion pure-Python; avoid extra deps.
* **Add CI logic**  
  Modify `.github/workflows/ci.yml`; treat GitHub Actions YAML as the
  “source code” of the CI agent.

---

## 4. Conventions every agent must follow

* **Single responsibility** – one agent, one job.
* **Stable public API** – breaking changes require a major version bump.
* **No side effects at import time** – initialise lazily.
* **Return proper exit codes** – 0 = success, ≠0 = failure.

---

## 5. Mapping modules ↔ agents (for greppers & tests)

* `src/pynytprof/tracer.py`         → **Profile agent**  
* `src/pynytprof/_ctrace.c`         → **Profile agent (C core)**  
* `src/pynytprof/_tracer.py`        → **Profile agent (Py core)**  
* `src/pynytprof/_cwrite.c`         → **Write agent (C)**  
* `src/pynytprof/_pywrite.py`       → **Write agent (Py)**  
* `src/pynytprof/convert.py`        → **Convert agent**  
* `src/pynytprof/verify.py`         → **Verify agent**  
* `src/pynytprof/cli.py`            → **CLI agent**

---

## 6. FAQ

**Q:** *Why “agents” instead of “modules”?*  
**A:** Because the repo mixes Python, C and CI YAML; “agent” stresses
the boundary and contract, not the language.

**Q:** *Do I need to update this file when I move a function?*  
**A:** Only if you add, remove, or rename an agent-level entry-point.

---

_Last updated: 2025-07-05_
