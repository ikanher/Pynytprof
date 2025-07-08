from __future__ import annotations

import os
import warnings

import importlib.metadata

_version = importlib.metadata.version("pynytprof")

_mode = os.environ.get("PYNYTPROF_WRITER", "auto")

if _mode == "py":
    from . import _pywrite as _impl
elif _mode == "c":
    from . import _cwrite as _impl
    if getattr(_impl, "__build__", None) != _version:
        warnings.warn(
            "stale _cwrite extension; falling back to pure-Python writer",
            RuntimeWarning,
        )
        from . import _pywrite as _impl
else:  # auto
    try:
        from . import _cwrite as _cimpl
    except Exception:
        _cimpl = None
    if _cimpl is not None and getattr(_cimpl, "__build__", None) == _version:
        _impl = _cimpl
    else:
        if _cimpl is not None and getattr(_cimpl, "__build__", None) != _version:
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

__all__ = ["write", "Writer"]
