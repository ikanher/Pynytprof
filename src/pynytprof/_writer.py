from __future__ import annotations

import os
import warnings

import importlib.metadata

_version = importlib.metadata.version("pynytprof")

_pref = os.environ.get("PYNYTPROF_WRITER")

if _pref == "py" or not _pref:
    from . import _pywrite as _impl
    write = _impl.write
    Writer = _impl.Writer
elif _pref == "c":
    try:
        from . import _cwrite as _impl
    except Exception:
        _impl = None
    if _impl is None or getattr(_impl, "__build__", None) != _version:
        if _impl is not None:
            warnings.warn(
                "stale _cwrite extension; falling back to pure-Python writer",
                RuntimeWarning,
            )
        from . import _pywrite as _impl
    write = _impl.write
    Writer = getattr(_impl, "Writer", None)
    if Writer is None:
        from . import _pywrite as _fallback
        Writer = _fallback.Writer
else:
    raise ImportError(f"unknown writer: {_pref}")

__all__ = ["write", "Writer"]
