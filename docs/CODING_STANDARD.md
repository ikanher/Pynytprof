* Python ≥ 3.12, `ruff` + `black --line-length 99`.
* One public function per .py file unless trivial.
* Avoid globals except for the single `_RingBuffer` instance.
* C code: keep IO behind a single `flush(int fd)`; no `<stdio.h>` outside tests.
* Follow SOLID: most functions are ≤ 40 loc, single responsibility.
