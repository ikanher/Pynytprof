from __future__ import annotations

import warnings

from ._build_tag import __pynytprof_build__

try:
    from . import _cwrite as _native
except Exception:
    _native = None

if _native is None or getattr(_native, "__build__", None) != __pynytprof_build__:
    if _native is not None:
        warnings.warn(
            "stale _cwrite extension; falling back to pure-Python writer", RuntimeWarning
        )
    from . import _pywrite as _fallback

    write = _fallback.write
else:
    write = _native.write

__all__ = ["write"]
