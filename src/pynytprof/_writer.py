from __future__ import annotations

import warnings

from . import _build_tag

try:
    from . import _cwrite
except Exception:  # pragma: no cover - optional
    _cwrite = None  # type: ignore

from . import _pywrite

if _cwrite is not None and getattr(_cwrite, "__build__", None) == _build_tag.__pynytprof_build__:
    write = _cwrite.write
else:
    if _cwrite is not None:
        warnings.warn("_cwrite stale; using pure Python writer", RuntimeWarning)
    write = _pywrite.write
