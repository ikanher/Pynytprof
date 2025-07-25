import pytest
pytestmark = pytest.mark.legacy_psfdce
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pynytprof._pywrite import Writer


class NonClosingBytesIO(io.BytesIO):
    def close(self):
        pass


def test_e_record_has_no_length():
    buf = NonClosingBytesIO()
    w = Writer(fp=buf)
    w.close()
    data = buf.getvalue()
    idx = data.rfind(b'E')
    assert len(data) - idx == 1, (
        'End record must be raw single byte; found extra bytes'
    )
