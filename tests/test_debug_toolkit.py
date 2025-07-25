import io
import os
from importlib import reload
import pytest

pytestmark = pytest.mark.xfail(not os.getenv("PYNYTPROF_DEBUG"), reason="debug env not set")


def test_debug_summary_table(monkeypatch, capsys, tmp_path):
    monkeypatch.setenv("PYNYTPROF_DEBUG", "1")
    import pynytprof._debug as dbg

    reload(dbg)
    import pynytprof._pywrite as pywrite

    reload(pywrite)
    out = tmp_path / "out.nyt"
    with pywrite.Writer(str(out)) as w:
        w.record_line(0, 1, 1, 0, 0)
    err = capsys.readouterr().err
    assert "DEBUG  CHUNK" in err
