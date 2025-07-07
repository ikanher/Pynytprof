from __future__ import annotations

import warnings

import importlib.metadata

try:
    from . import _cwrite as _native
except Exception:
    _native = None

_version = importlib.metadata.version("pynytprof")

if _native is None or getattr(_native, "__build__", None) != _version:
    if _native is not None:
        warnings.warn(
            "stale _cwrite extension; falling back to pure-Python writer", RuntimeWarning
        )
    from . import _pywrite as _fallback

    write = _fallback.write
    Writer = _fallback.Writer
else:
    write = _native.write
    Writer = getattr(_native, "Writer", None)
    if Writer is None:
        from . import _pywrite as _fallback
        Writer = _fallback.Writer

__all__ = ["write", "Writer"]
